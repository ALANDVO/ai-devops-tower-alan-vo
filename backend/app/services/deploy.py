"""Deployment strategies: canary, blue-green, rolling. Rollback with health checks."""

import time
import uuid
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class DeploymentStep:
    name: str
    status: str = "pending"  # pending, running, success, failed
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    details: str = ""


@dataclass
class Deployment:
    deployment_id: str
    service: str
    artifact: str
    environment: str
    strategy: str
    triggered_by: str
    status: str = "pending"  # pending, in_progress, completed, rolled_back, failed
    steps: List[DeploymentStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    health_score: float = 1.0
    rollback_reason: str = ""


class DeployEngine:
    def __init__(self):
        self._deployments: Dict[str, Deployment] = {}

    def start(self, req: Any, user: str) -> dict:
        dep_id = f"deploy-{uuid.uuid4().hex[:12]}"
        strategy = req.strategy if hasattr(req, "strategy") else "rolling"
        steps = self._plan_steps(strategy)
        deployment = Deployment(
            deployment_id=dep_id,
            service=req.service if hasattr(req, "service") else "unknown",
            artifact=req.artifact if hasattr(req, "artifact") else "",
            environment=req.environment if hasattr(req, "environment") else "production",
            strategy=strategy,
            triggered_by=user,
            steps=steps,
        )
        self._deployments[dep_id] = deployment
        self._execute(deployment)
        return {"deployment_id": dep_id, "status": deployment.status}

    def _plan_steps(self, strategy: str) -> List[DeploymentStep]:
        if strategy == "canary":
            return [
                DeploymentStep("canary_5pct"),
                DeploymentStep("health_check_1"),
                DeploymentStep("canary_25pct"),
                DeploymentStep("health_check_2"),
                DeploymentStep("canary_50pct"),
                DeploymentStep("health_check_3"),
                DeploymentStep("full_rollout"),
                DeploymentStep("final_health_check"),
            ]
        elif strategy == "blue-green":
            return [
                DeploymentStep("provision_blue"),
                DeploymentStep("smoke_test_blue"),
                DeploymentStep("switch_traffic"),
                DeploymentStep("health_check"),
                DeploymentStep("teardown_green"),
            ]
        else:  # rolling
            return [
                DeploymentStep("batch_1"),
                DeploymentStep("health_check_1"),
                DeploymentStep("batch_2"),
                DeploymentStep("health_check_2"),
                DeploymentStep("batch_3"),
                DeploymentStep("health_check_3"),
                DeploymentStep("final_verification"),
            ]

    def _execute(self, d: Deployment):
        d.status = "in_progress"
        for step in d.steps:
            step.status = "running"
            step.started_at = time.time()
            time.sleep(0.01)
            # Simulated health check
            health = self._check_health(d)
            d.health_score = health
            if health < 0.9:
                step.status = "failed"
                d.status = "failed"
                d.rollback_reason = f"Health check failed at {step.name} (score: {health:.2f})"
                break
            step.status = "success"
            step.finished_at = time.time()
            step.details = f"Health: {health:.2f}"
        else:
            d.status = "completed"
            d.finished_at = time.time()

    def _check_health(self, d: Deployment) -> float:
        """Simulated health check — in production, queries service metrics."""
        import random
        random.seed(hash(d.deployment_id) % 10000)
        return random.uniform(0.85, 1.0)

    def get_status(self, dep_id: str) -> Optional[dict]:
        d = self._deployments.get(dep_id)
        if not d:
            return None
        result = asdict(d)
        result["progress"] = f"{sum(1 for s in d.steps if s.status == 'success')}/{len(d.steps)}"
        return result

    def rollback(self, dep_id: str, user: str) -> dict:
        d = self._deployments.get(dep_id)
        if not d:
            raise ValueError(f"Deployment {dep_id} not found")
        d.status = "rolled_back"
        d.rollback_reason = f"Manual rollback by {user}"
        d.finished_at = time.time()
        # Add rollback steps
        d.steps.append(DeploymentStep("rollback", "success", d.finished_at, d.finished_at, "Reverted to previous version"))
        return {"status": "rolled_back", "reason": d.rollback_reason}


_engine: Optional[DeployEngine] = None

def get_deploy_engine() -> DeployEngine:
    global _engine
    if _engine is None:
        _engine = DeployEngine()
    return _engine
