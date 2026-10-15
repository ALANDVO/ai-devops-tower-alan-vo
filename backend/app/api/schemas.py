"""Pydantic request/response schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class PipelineTriggerRequest(BaseModel):
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class DeployRequest(BaseModel):
    service: str
    artifact: str
    environment: str = "production"
    strategy: str = "rolling"  # rolling | canary | blue-green
    max_unavailable: int = 25
    batch_size: Optional[int] = None
    health_check_path: str = "/health"
    timeout_seconds: int = 300


class IncidentCreate(BaseModel):
    title: str
    severity: str = "P2"  # P1, P2, P3, P4
    description: str = ""
    service: str = ""
    components: List[str] = Field(default_factory=list)
    detected_by: Optional[str] = None


class AlertRuleCreate(BaseModel):
    name: str
    service: str
    metric: str
    condition: str  # gt, lt, gte, lte, equals
    threshold: float
    duration_seconds: int = 300
    severity: str = "P2"
    notification_channels: List[str] = Field(default_factory=list)


class ReleasePromoteRequest(BaseModel):
    environment: str  # staging, production, canary
