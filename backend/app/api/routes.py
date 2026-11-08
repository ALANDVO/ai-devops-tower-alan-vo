"""API routes for AI DevOps Control Tower."""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional, AsyncGenerator
import json

from app.api.auth import get_current_user, require_permission
from app.api.schemas import (
    PipelineTriggerRequest, DeployRequest, IncidentCreate,
    AlertRuleCreate, ReleasePromoteRequest,
)
from app.services.pipelines import get_pipeline_engine
from app.services.builds import get_build_engine
from app.services.analysis import get_analysis_engine
from app.services.artifacts import get_artifact_store
from app.services.deploy import get_deploy_engine
from app.services.slo import get_slo_engine
from app.services.incidents import get_incident_engine
from app.services.releases import get_release_engine
from app.services.alerts import get_alert_engine
from app.services.llm import stream_llm, LLMStreamChunk


router = APIRouter()


def sse_format(chunk: LLMStreamChunk) -> str:
    """Format a stream chunk as SSE event."""
    data = {
        "content": chunk.content,
        "is_final": chunk.is_final,
        "provider": chunk.provider,
        "model": chunk.model,
    }
    if chunk.usage:
        data["usage"] = chunk.usage
    if chunk.error:
        data["error"] = chunk.error
    return f"data: {json.dumps(data)}\n\n"


async def stream_analysis(prompt: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
    """Stream LLM analysis as SSE events."""
    async for chunk in stream_llm(prompt, system_prompt):
        yield sse_format(chunk)


async def stream_incident_analysis(incident_id: str) -> AsyncGenerator[str, None]:
    """Stream incident root cause analysis as SSE events."""
    engine = get_incident_engine()
    inc = engine._incidents.get(incident_id)
    if not inc:
        yield sse_format(LLMStreamChunk(content="", is_final=True, error="Incident not found"))
        return

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

    async for chunk in stream_llm(prompt):
        yield sse_format(chunk)


async def stream_incident_postmortem(incident_id: str) -> AsyncGenerator[str, None]:
    """Stream incident postmortem as SSE events."""
    engine = get_incident_engine()
    inc = engine._incidents.get(incident_id)
    if not inc:
        yield sse_format(LLMStreamChunk(content="", is_final=True, error="Incident not found"))
        return

    import time
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

    async for chunk in stream_llm(prompt):
        yield sse_format(chunk)


async def stream_release_notes(release_id: str) -> AsyncGenerator[str, None]:
    """Stream release notes generation as SSE events."""
    engine = get_release_engine()
    r = engine._releases.get(release_id)
    if not r:
        yield sse_format(LLMStreamChunk(content="", is_final=True, error="Release not found"))
        return

    prompt = f"""Generate release notes for version {r.version} of {r.service}.

Description: {r.description or 'No description provided'}
Changelog:
{chr(10).join(f"- {item}" for item in r.changelog) if r.changelog else 'No changelog entries'}

Write user-facing release notes that are clear, organized, and highlight:
- New features
- Improvements
- Bug fixes
- Breaking changes (if any)
- Upgrade notes

Use a friendly, professional tone. Group by category."""

    async for chunk in stream_llm(prompt):
        yield sse_format(chunk)


async def stream_build_analysis(build_id: str) -> AsyncGenerator[str, None]:
    """Stream build failure analysis as SSE events."""
    build_engine = get_build_engine()
    build = build_engine.get_build(build_id)
    if not build:
        yield sse_format(LLMStreamChunk(content="", is_final=True, error="Build not found"))
        return

    if build["status"] == "success":
        yield sse_format(LLMStreamChunk(
            content="Build completed successful. No failures detected.",
            is_final=True,
            provider="local",
            model="none"
        ))
        return

    failed_stages = [s for s in build["stages"] if s["status"] == "failed"]
    if not failed_stages:
        yield sse_format(LLMStreamChunk(
            content="Build did not complete all stages.",
            is_final=True,
            provider="local",
            model="none"
        ))
        return

    import json
    stage_info = []
    for s in failed_stages:
        stage_info.append(f"Stage: {s['name']}\nExit code: {s.get('exit_code', 'N/A')}\nLogs: {s.get('logs', 'No logs available')[:2000]}")

    prompt = f"""You are a senior DevOps engineer analyzing a CI/CD build failure.

Build details:
- Service: {build['service']}
- Branch: {build['branch']}
- Commit: {build['commit_sha']}
- Triggered by: {build['triggered_by']}
- Parameters: {json.dumps(build.get('parameters', {}))}

Failed stages:
{chr(10).join(stage_info)}

Provide:
1. Root cause analysis (most likely cause)
2. Evidence from logs
3. Recommended fixes (ordered by likelihood)
4. Preventive measures for the future

Be specific and actionable. Reference exact log lines where possible."""

    async for chunk in stream_llm(prompt):
        yield sse_format(chunk)


# ─── Health ───

@router.get("/health")
async def health():
    return {"status": "healthy", "service": "ai-devops-tower", "version": "1.0.0"}


# ─── Pipelines ───

@router.get("/pipelines")
async def list_pipelines(service: Optional[str] = None, status: Optional[str] = None):
    engine = get_pipeline_engine()
    pipelines = engine.list_pipelines(service=service, status=status)
    return {"pipelines": pipelines, "count": len(pipelines)}


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    engine = get_pipeline_engine()
    pipeline = engine.get_pipeline(pipeline_id)
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")
    return pipeline


@router.post("/pipelines/{pipeline_id}/trigger", status_code=202)
async def trigger_pipeline(pipeline_id: str, req: PipelineTriggerRequest, user=Depends(require_permission("pipelines:write"))):
    engine = get_pipeline_engine()
    result = engine.trigger(pipeline_id, req.branch or "main", req.commit_sha or "latest", user["email"], req.parameters or {})
    return {"build_id": result["build_id"], "status": "queued"}


@router.get("/pipelines/{pipeline_id}/status")
async def pipeline_status(pipeline_id: str):
    engine = get_pipeline_engine()
    status = engine.get_status(pipeline_id)
    if not status:
        raise HTTPException(404, "Pipeline not found")
    return status


# ─── Builds ───

@router.get("/builds")
async def list_builds(
    pipeline_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=200)
):
    engine = get_build_engine()
    builds = engine.list_builds(pipeline_id=pipeline_id, status=status, limit=limit)
    return {"builds": builds, "count": len(builds)}


@router.get("/builds/{build_id}")
async def get_build(build_id: str):
    engine = get_build_engine()
    build = engine.get_build(build_id)
    if not build:
        raise HTTPException(404, "Build not found")
    return build


@router.post("/builds/{build_id}/analyze")
async def analyze_build(build_id: str, user=Depends(get_current_user)):
    """LLM-powered build failure analysis."""
    engine = get_analysis_engine()
    build_engine = get_build_engine()
    build = build_engine.get_build(build_id)
    if not build:
        raise HTTPException(404, "Build not found")
    analysis = await engine.analyze(build)
    return {"build_id": build_id, "analysis": analysis}


@router.get("/builds/{build_id}/analyze/stream")
async def analyze_build_stream(build_id: str, user=Depends(get_current_user)):
    """Stream LLM-powered build failure analysis as SSE."""
    build_engine = get_build_engine()
    build = build_engine.get_build(build_id)
    if not build:
        raise HTTPException(404, "Build not found")
    return StreamingResponse(
        stream_build_analysis(build_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


# ─── Artifacts ───

@router.get("/artifacts")
async def list_artifacts(service: Optional[str] = None, limit: int = Query(50, le=200)):
    store = get_artifact_store()
    artifacts = store.list_artifacts(service=service, limit=limit)
    return {"artifacts": artifacts, "count": len(artifacts)}


# ─── Deployment ───

@router.post("/deploy", status_code=202)
async def start_deployment(req: DeployRequest, user=Depends(require_permission("deploy:write"))):
    engine = get_deploy_engine()
    result = engine.start(req, user["email"])
    return {"deployment_id": result["deployment_id"], "status": "started", "strategy": req.strategy}


@router.get("/deploy/{deployment_id}/status")
async def deployment_status(deployment_id: str):
    engine = get_deploy_engine()
    status = engine.get_status(deployment_id)
    if not status:
        raise HTTPException(404, "Deployment not found")
    return status


@router.post("/deploy/{deployment_id}/rollback", status_code=202)
async def rollback_deployment(deployment_id: str, user=Depends(get_current_user)):
    engine = get_deploy_engine()
    result = engine.rollback(deployment_id, user["email"])
    return {"deployment_id": deployment_id, "status": result["status"], "reason": result.get("reason", "")}


# ─── SLO ───

@router.get("/slo")
async def list_slos():
    engine = get_slo_engine()
    slos = engine.list_slos()
    return {"slos": slos, "count": len(slos)}


@router.get("/slo/{slo_id}/budget")
async def slo_budget(slo_id: str):
    engine = get_slo_engine()
    budget = engine.get_budget(slo_id)
    if not budget:
        raise HTTPException(404, "SLO not found")
    return budget


@router.get("/slo/{slo_id}/burn-rate")
async def slo_burn_rate(slo_id: str, window: str = "30d"):
    engine = get_slo_engine()
    burn = engine.get_burn_rate(slo_id, window)
    if not burn:
        raise HTTPException(404, "SLO not found")
    return burn


# ─── Incidents ───

@router.get("/incidents")
async def list_incidents(severity: Optional[str] = None, status: Optional[str] = None, limit: int = Query(50, le=200)):
    engine = get_incident_engine()
    incidents = engine.list_incidents(severity=severity, status=status, limit=limit)
    return {"incidents": incidents, "count": len(incidents)}


@router.post("/incidents", status_code=201)
async def create_incident(req: IncidentCreate, user=Depends(require_permission("incidents:write"))):
    engine = get_incident_engine()
    incident = engine.create(req, user["email"])
    return incident


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    engine = get_incident_engine()
    incident = engine.get_incident(incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return incident


@router.post("/incidents/{incident_id}/analyze")
async def incident_root_cause(incident_id: str, user=Depends(get_current_user)):
    """AI root cause analysis."""
    engine = get_incident_engine()
    result = await engine.analyze(incident_id)
    if not result:
        raise HTTPException(404, "Incident not found")
    return {"incident_id": incident_id, "root_cause": result}


@router.get("/incidents/{incident_id}/analyze/stream")
async def incident_root_cause_stream(incident_id: str, user=Depends(get_current_user)):
    """Stream AI root cause analysis as SSE."""
    engine = get_incident_engine()
    inc = engine._incidents.get(incident_id)
    if not inc:
        raise HTTPException(404, "Incident not found")
    return StreamingResponse(
        stream_incident_analysis(incident_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.post("/incidents/{incident_id}/postmortem")
async def incident_postmortem(incident_id: str, user=Depends(get_current_user)):
    """Generate LLM-powered postmortem."""
    engine = get_incident_engine()
    result = await engine.postmortem(incident_id)
    if not result:
        raise HTTPException(404, "Incident not found")
    return {"incident_id": incident_id, "postmortem": result}


@router.get("/incidents/{incident_id}/postmortem/stream")
async def incident_postmortem_stream(incident_id: str, user=Depends(get_current_user)):
    """Stream LLM-powered postmortem as SSE."""
    engine = get_incident_engine()
    inc = engine._incidents.get(incident_id)
    if not inc:
        raise HTTPException(404, "Incident not found")
    return StreamingResponse(
        stream_incident_postmortem(incident_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


# ─── Releases ───

@router.get("/releases")
async def list_releases(service: Optional[str] = None, status: Optional[str] = None, limit: int = Query(50, le=200)):
    engine = get_release_engine()
    releases = engine.list_releases(service=service, status=status, limit=limit)
    return {"releases": releases, "count": len(releases)}


@router.get("/releases/{release_id}")
async def get_release(release_id: str):
    engine = get_release_engine()
    release = engine.get_release(release_id)
    if not release:
        raise HTTPException(404, "Release not found")
    return release


@router.post("/releases/{release_id}/notes")
async def generate_release_notes(release_id: str, user=Depends(get_current_user)):
    """LLM-powered release notes generation."""
    engine = get_release_engine()
    result = await engine.generate_notes(release_id)
    if not result:
        raise HTTPException(404, "Release not found")
    return {"release_id": release_id, "notes": result}


@router.get("/releases/{release_id}/notes/stream")
async def generate_release_notes_stream(release_id: str, user=Depends(get_current_user)):
    """Stream LLM-powered release notes generation as SSE."""
    engine = get_release_engine()
    r = engine._releases.get(release_id)
    if not r:
        raise HTTPException(404, "Release not found")
    return StreamingResponse(
        stream_release_notes(release_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


@router.post("/releases/{release_id}/promote", status_code=202)
async def promote_release(release_id: str, req: ReleasePromoteRequest, user=Depends(get_current_user)):
    engine = get_release_engine()
    result = engine.promote(release_id, req.environment, user["email"])
    return {"release_id": release_id, "status": result["status"], "environment": req.environment}


# ─── Alerts ───

@router.get("/alerts")
async def list_alerts(service: Optional[str] = None):
    engine = get_alert_engine()
    alerts = engine.list_alerts(service=service)
    return {"alerts": alerts, "count": len(alerts)}


@router.post("/alerts", status_code=201)
async def create_alert(req: AlertRuleCreate, user=Depends(require_permission("alerts:write"))):
    engine = get_alert_engine()
    alert = engine.create_alert(req, user["email"])
    return alert
