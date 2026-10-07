"""CI pipeline management: build triggers, status tracking, stage orchestration."""

import json
import time
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict


STAGE_ORDER = ["checkout", "build", "test", "lint", "package", "publish"]


@dataclass
class Stage:
    name: str
    status: str = "pending"  # pending, running, success, failed, skipped
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    logs: str = ""
    exit_code: Optional[int] = None


@dataclass
class Build:
    build_id: str
    pipeline_id: str
    service: str
    branch: str
    commit_sha: str
    triggered_by: str
    status: str = "queued"  # queued, running, success, failed, cancelled
    stages: List[Stage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


class PipelineEngine:
    def __init__(self):
        self._pipelines: Dict[str, dict] = {}
        self._builds: Dict[str, Build] = {}
        self._data_dir: Optional[Path] = None

    def init(self, data_dir: str):
        self._data_dir = Path(data_dir) / "pipelines"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        p = self._data_dir / "pipelines.json"
        if p.exists():
            self._pipelines = json.loads(p.read_text())

    def _save(self):
        if self._data_dir:
            (self._data_dir / "pipelines.json").write_text(json.dumps(self._pipelines, indent=2))

    def register(self, pipeline_id: str, service: str, stages: Optional[List[str]] = None) -> dict:
        pipeline = {
            "pipeline_id": pipeline_id,
            "service": service,
            "stages": stages or STAGE_ORDER,
            "created_at": time.time(),
            "last_run": None,
            "build_count": 0,
        }
        self._pipelines[pipeline_id] = pipeline
        self._save()
        return pipeline

    def list_pipelines(self, service: Optional[str] = None, status: Optional[str] = None) -> List[dict]:
        pipelines = list(self._pipelines.values())
        if service:
            pipelines = [p for p in pipelines if p["service"] == service]
        return pipelines

    def get_pipeline(self, pipeline_id: str) -> Optional[dict]:
        return self._pipelines.get(pipeline_id)

    def trigger(self, pipeline_id: str, branch: str, commit_sha: str, user: str, params: Dict[str, Any]) -> dict:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")
        build_id = f"build-{uuid.uuid4().hex[:12]}"
        stages = [Stage(name=s) for s in pipeline["stages"]]
        build = Build(
            build_id=build_id, pipeline_id=pipeline_id, service=pipeline["service"],
            branch=branch, commit_sha=commit_sha, triggered_by=user,
            stages=stages, parameters=params,
        )
        self._builds[build_id] = build
        pipeline["last_run"] = time.time()
        pipeline["build_count"] += 1
        self._save()
        # Simulate stage execution
        self._run_build(build)
        return {"build_id": build_id, "status": build.status}

    def _run_build(self, build: Build):
        build.status = "running"
        for stage in build.stages:
            stage.status = "running"
            stage.started_at = time.time()
            # Simulate work
            time.sleep(0.01)
            stage.status = "success"
            stage.finished_at = time.time()
            stage.exit_code = 0
        build.status = "success"
        build.finished_at = time.time()

    def get_status(self, pipeline_id: str) -> Optional[dict]:
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return None
        builds = [b for b in self._builds.values() if b.pipeline_id == pipeline_id]
        latest = builds[-1] if builds else None
        return {
            "pipeline_id": pipeline_id,
            "service": pipeline["service"],
            "last_build": asdict(latest) if latest else None,
            "build_count": pipeline["build_count"],
        }

    def get_build(self, build_id: str) -> Optional[Build]:
        return self._builds.get(build_id)

    def list_builds(self, pipeline_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[dict]:
        builds = list(self._builds.values())
        if pipeline_id:
            builds = [b for b in builds if b.pipeline_id == pipeline_id]
        if status:
            builds = [b for b in builds if b.status == status]
        builds.sort(key=lambda b: b.created_at, reverse=True)
        return [asdict(b) for b in builds[:limit]]


_engine: Optional[PipelineEngine] = None

def get_pipeline_engine() -> PipelineEngine:
    global _engine
    if _engine is None:
        _engine = PipelineEngine()
    return _engine
