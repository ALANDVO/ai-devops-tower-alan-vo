"""Incident lifecycle, severity, on-call routing, LLM root cause analysis and postmortems."""

import time
import json
import uuid
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class IncidentEvent:
    timestamp: float
    actor: str
    action: str
    details: str = ""


@dataclass
class Incident:
    incident_id: str
    title: str
    severity: str  # P1, P2, P3, P4
    description: str
    service: str
    status: str = "open"  # open, investigating, identified, monitoring, resolved
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    events: List[IncidentEvent] = field(default_factory=list)
    root_cause: Optional[str] = None
    postmortem: Optional[str] = None
    on_call: str = ""
    components: List[str] = field(default_factory=list)
    detected_by: str = ""


class IncidentEngine:
    def __init__(self):
        self._incidents: Dict[str, Incident] = {}

    def init(self, data_dir: str):
        self._data_dir = Path(data_dir) / "incidents"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._seed()

    def _seed(self):
        """Seed with sample incidents for demo."""
        self.create_from_dict(
            {"title": "API gateway 5xx spike", "severity": "P1", "service": "api-gateway",
             "description": "Sudden increase in 5xx errors across all regions. Error budget burn rate at 14.4x."},
            "sre-team",
        )
        self.create_from_dict(
            {"title": "Database connection pool exhaustion", "severity": "P2", "service": "orders-db",
             "description": "Connection pool at 100% capacity. Requests queuing >5s."},
            "devops-bot",
        )
        self.create_from_dict(
            {"title": "Elevated p99 latency on /checkout", "severity": "P3", "service": "checkout-api",
             "description": "p99 latency trending above 500ms threshold. SLO at warning level."},
            "slo-monitor",
        )

    def create_from_dict(self, data: dict, created_by: str) -> Incident:
        inc_id = f"inc-{uuid.uuid4().hex[:12]}"
        severity = data.get("severity", "P2")
        on_call = self._route_on_call(severity, data.get("service", ""))
        incident = Incident(
            incident_id=inc_id,
            title=data.get("title", "Untitled"),
            severity=severity,
            description=data.get("description", ""),
            service=data.get("service", ""),
            components=data.get("components", []),
            detected_by=data.get("detected_by", created_by),
            on_call=on_call,
            events=[IncidentEvent(time.time(), "system", "created", f"Severity {severity}, on-call: {on_call}")],
        )
        self._incidents[inc_id] = incident
        return incident

    def create(self, req: Any, user: str) -> dict:
        data = {
            "title": req.title if hasattr(req, "title") else "Untitled",
            "severity": req.severity if hasattr(req, "severity") else "P2",
            "description": req.description if hasattr(req, "description") else "",
            "service": req.service if hasattr(req, "service") else "",
            "components": req.components if hasattr(req, "components") else [],
            "detected_by": user,
        }
        incident = self.create_from_dict(data, user)
        return asdict(incident)

    def _route_on_call(self, severity: str, service: str) -> str:
        """Route to on-call based on severity and service."""
        rotation = {
            "P1": "senior-sre-oncall",
            "P2": "platform-oncall",
            "P3": "service-team-lead",
            "P4": "developer-oncall",
        }
        return rotation.get(severity, "general-oncall")

    def list_incidents(self, severity: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[dict]:
        incidents = list(self._incidents.values())
        if severity:
            incidents = [i for i in incidents if i.severity == severity]
        if status:
            incidents = [i for i in incidents if i.status == status]
        incidents.sort(key=lambda i: i.created_at, reverse=True)
        return [asdict(i) for i in incidents[:limit]]

    def get_incident(self, incident_id: str) -> Optional[dict]:
        inc = self._incidents.get(incident_id)
        if not inc:
            return None
        d = asdict(inc)
        d["duration_minutes"] = ((inc.resolved_at or time.time()) - inc.created_at) / 60
        return d

    def update_status(self, incident_id: str, new_status: str, actor: str, details: str = "") -> Optional[dict]:
        inc = self._incidents.get(incident_id)
        if not inc:
            return None
        inc.status = new_status
        if new_status == "resolved":
            inc.resolved_at = time.time()
        inc.events.append(IncidentEvent(time.time(), actor, "status_change", details or f"Status → {new_status}"))
        return asdict(inc)

    async def analyze(self, incident_id: str) -> Optional[dict]:
        """LLM-powered root cause analysis."""
        inc = self._incidents.get(incident_id)
        if not inc:
            return None

        prompt = f"""You are a senior SRE performing root cause analysis.

Incident: {inc.title}
Severity: {inc.severity}
Service: {inc.service}
Description: {inc.description}
Components: {', '.join(inc.components) if inc.components else 'N/A'}
Status: {inc.status}

Timeline:
{chr(10).join(f"  [{e.timestamp}] {e.actor}: {e.action} — {e.details}" for e in inc.events)}

Provide:
1. Most likely root cause with confidence level
2. Contributing factors
3. Evidence chain from the timeline
4. Immediate mitigation steps
5. Long-term fixes

Be specific. Reference the service architecture and common failure modes."""

        try:
            import httpx
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.LLM_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": settings.LLM_MODEL,
                        "max_tokens": settings.LLM_MAX_TOKENS,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                analysis = data["content"][0]["text"]
                inc.root_cause = analysis
                inc.events.append(IncidentEvent(time.time(), "ai", "root_cause_analyzed", "LLM analysis completed"))
                return {"root_cause": analysis, "analyzed_at": time.time()}
        except Exception as e:
            return {"root_cause": f"Analysis unavailable: {str(e)}", "error": True}

    async def postmortem(self, incident_id: str) -> Optional[dict]:
        """Generate LLM-powered postmortem document."""
        inc = self._incidents.get(incident_id)
        if not inc:
            return None

        duration = ((inc.resolved_at or time.time()) - inc.created_at) / 60
        prompt = f"""Generate a blameless postmortem for this incident.

Title: {inc.title}
Severity: {inc.severity}
Service: {inc.service}
Duration: {duration:.0f} minutes
Status: {inc.status}

Description: {inc.description}

Timeline:
{chr(10).join(f"  [{time.strftime('%H:%M:%S', time.localtime(e.timestamp))}] {e.actor}: {e.action} — {e.details}" for e in inc.events)}

Root cause (if known): {inc.root_cause or 'Not yet determined'}

Structure:
## Summary
## Timeline (UTC)
## Impact
## Root Cause
## Detection
## Resolution
## Action Items (with owners and deadlines)
## What Went Well
## What Could Be Improved

Be thorough, blameless, and actionable."""

        try:
            import httpx
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.LLM_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": settings.LLM_MODEL,
                        "max_tokens": settings.LLM_MAX_TOKENS,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                pm = data["content"][0]["text"]
                inc.postmortem = pm
                inc.events.append(IncidentEvent(time.time(), "ai", "postmortem_generated", "Postmortem document created"))
                return {"postmortem": pm, "generated_at": time.time()}
        except Exception as e:
            return {"postmortem": f"Generation unavailable: {str(e)}", "error": True}


from pathlib import Path
from config import settings

_engine: Optional[IncidentEngine] = None

def get_incident_engine() -> IncidentEngine:
    global _engine
    if _engine is None:
        _engine = IncidentEngine()
    return _engine
