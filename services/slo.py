"""SLO definitions, error budget tracking, burn rate calculation."""

import time
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, field, asdict


@dataclass
class SLODefinition:
    slo_id: str
    service: str
    name: str
    objective: float  # e.g., 0.999 = 99.9%
    window_days: int  # 30 or 90
    metric: str  # e.g., "availability", "latency_p99"
    threshold: float  # e.g., 300ms for latency
    created_at: float = field(default_factory=time.time)


class SloEngine:
    def __init__(self):
        self._slos: Dict[str, SLODefinition] = {}
        self._metrics: Dict[str, List[dict]] = {}

    def init(self, data_dir: str):
        self._data_dir = Path(data_dir) / "slo"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._register_defaults()

    def _register_defaults(self):
        defaults = [
            ("api-availability", "api-gateway", "API Availability", 0.999, 30, "availability", 100.0),
            ("api-latency", "api-gateway", "API Latency P99", 0.995, 30, "latency_p99", 300.0),
            ("build-success", "ci-pipeline", "Build Success Rate", 0.95, 30, "build_success", 100.0),
            ("deploy-success", "deploy-engine", "Deployment Success", 0.99, 30, "deploy_success", 100.0),
        ]
        for sid, svc, name, obj, window, metric, threshold in defaults:
            self.define(sid, svc, name, obj, window, metric, threshold)

    def define(self, slo_id: str, service: str, name: str, objective: float,
               window_days: int, metric: str, threshold: float) -> SLODefinition:
        slo = SLODefinition(
            slo_id=slo_id, service=service, name=name, objective=objective,
            window_days=window_days, metric=metric, threshold=threshold,
        )
        self._slos[slo_id] = slo
        if slo_id not in self._metrics:
            self._metrics[slo_id] = self._generate_sample_metrics(slo)
        return slo

    def _generate_sample_metrics(self, slo: SLODefinition) -> List[dict]:
        """Generate realistic sample metrics for the SLO window."""
        import random
        random.seed(hash(slo.slo_id) % 10000)
        now = time.time()
        points = []
        # 30 days of hourly data points (simplified to 720 points)
        for i in range(720):
            ts = now - (720 - i) * 3600
            # Base success rate near objective with noise
            base = slo.objective
            noise = random.gauss(0, 0.001)
            # Occasional incidents
            incident = random.random() < 0.005
            value = base + noise - (0.02 if incident else 0)
            value = max(0.5, min(1.0, value))
            points.append({"timestamp": ts, "value": value, "incident": incident})
        return points

    def list_slos(self) -> List[dict]:
        return [asdict(s) for s in self._slos.values()]

    def get_slo(self, slo_id: str) -> Optional[SLODefinition]:
        return self._slos.get(slo_id)

    def get_budget(self, slo_id: str) -> Optional[dict]:
        slo = self._slos.get(slo_id)
        if not slo:
            return None
        metrics = self._metrics.get(slo_id, [])
        if not metrics:
            return {"slo_id": slo_id, "error_budget_remaining": slo.objective, "status": "unknown"}

        # Calculate actual reliability
        total = len(metrics)
        successful = sum(1 for m in metrics if m["value"] >= slo.objective)
        actual_reliability = successful / total if total > 0 else 0.0
        error_budget_total = 1.0 - slo.objective
        error_budget_used = max(0.0, 1.0 - actual_reliability)
        error_budget_remaining = error_budget_total - error_budget_used

        # Budget percentage remaining
        budget_pct = (error_budget_remaining / error_budget_total * 100) if error_budget_total > 0 else 0

        # Status
        if budget_pct > 50:
            status = "healthy"
        elif budget_pct > 20:
            status = "warning"
        else:
            status = "critical"

        return {
            "slo_id": slo_id,
            "service": slo.service,
            "name": slo.name,
            "objective": slo.objective,
            "actual_reliability": actual_reliability,
            "error_budget_total": error_budget_total,
            "error_budget_used": error_budget_used,
            "error_budget_remaining": error_budget_remaining,
            "budget_percentage": budget_pct,
            "status": status,
            "window_days": slo.window_days,
        }

    def get_burn_rate(self, slo_id: str, window: str = "30d") -> Optional[dict]:
        slo = self._slos.get(slo_id)
        if not slo:
            return None
        metrics = self._metrics.get(slo_id, [])
        if not metrics:
            return {"slo_id": slo_id, "burn_rate": 0.0, "thresholds": []}

        # Calculate burn rate: how fast we're consuming error budget
        error_budget_total = 1.0 - slo.objective
        window_hours = int(window.rstrip("d")) * 24
        recent = metrics[-window_hours:] if len(metrics) >= window_hours else metrics

        failures = sum(1 for m in recent if m["value"] < slo.objective)
        burn_rate = (failures / len(recent)) / error_budget_total if error_budget_total > 0 else 0

        # Threshold levels
        thresholds = [
            {"multiplier": 14.4, "window": "1h", "severity": "P1", "action": "page_oncall"},
            {"multiplier": 6.0, "window": "6h", "severity": "P2", "action": "notify_team"},
            {"multiplier": 3.0, "window": "24h", "severity": "P3", "action": "create_ticket"},
        ]

        active_alerts = [t for t in thresholds if burn_rate >= t["multiplier"]]

        return {
            "slo_id": slo_id,
            "service": slo.service,
            "burn_rate": burn_rate,
            "window": window,
            "failures_in_window": failures,
            "total_in_window": len(recent),
            "thresholds": thresholds,
            "active_alerts": active_alerts,
            "severity": active_alerts[0]["severity"] if active_alerts else "none",
        }


_engine: Optional[SloEngine] = None

def get_slo_engine() -> SloEngine:
    global _engine
    if _engine is None:
        _engine = SloEngine()
    return _engine
