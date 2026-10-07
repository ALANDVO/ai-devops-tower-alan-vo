"""API routes for AI DevOps Control Tower."""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional

from api.auth import get_current_user
from api.schemas import (
    PipelineTriggerRequest, DeployRequest, IncidentCreate,
    AlertRuleCreate, ReleasePromoteRequest,
)
from services.pipelines import get_pipeline_engine
from services.builds import get_build_engine
from services.analysis import get_analysis_engine
from services.artifacts import get_artifact_store
from services.deploy import get_deploy_engine
from services.slo import get_slo_engine
from services.incidents import get_incident_engine
from services.releases import get_release_engine
from services.alerts import get_alert_engine


router = APIRouter()


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
async def trigger_pipeline(pipeline_id: str, req: PipelineTriggerRequest, user=Depends(get_current_user)):
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
    limit: int = Query(50, le=200),
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


# ─── Artifacts ───

@router.get("/artifacts")
async def list_artifacts(service: Optional[str] = None, limit: int = Query(50, le=200)):
    store = get_artifact_store()
    artifacts = store.list_artifacts(service=service, limit=limit)
    return {"artifacts": artifacts, "count": len(artifacts)}


# ─── Deployment ───

@router.post("/deploy", status_code=202)
async def start_deployment(req: DeployRequest, user=Depends(get_current_user)):
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
    return {"deployment_id": deployment_id, "status": result["status"]}


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
async def create_incident(req: IncidentCreate, user=Depends(get_current_user)):
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


@router.post("/incidents/{incident_id}/postmortem")
async def incident_postmortem(incident_id: str, user=Depends(get_current_user)):
    """Generate LLM-powered postmortem."""
    engine = get_incident_engine()
    result = await engine.postmortem(incident_id)
    if not result:
        raise HTTPException(404, "Incident not found")
    return {"incident_id": incident_id, "postmortem": result}


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
async def create_alert(req: AlertRuleCreate, user=Depends(get_current_user)):
    engine = get_alert_engine()
    alert = engine.create_alert(req, user["email"])
    return alert
