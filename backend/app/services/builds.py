"""Build records and history - wraps pipeline engine builds."""
from typing import Optional, List
from app.services.pipelines import get_pipeline_engine, Build


class BuildEngine:
    """Thin wrapper around PipelineEngine for build-specific queries."""

    def list_builds(
        self, pipeline_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50
    ) -> List[dict]:
        engine = get_pipeline_engine()
        builds = engine.list_builds(pipeline_id=pipeline_id, status=status, limit=limit)
        return builds

    def get_build(self, build_id: str) -> Optional[dict]:
        engine = get_pipeline_engine()
        build = engine.get_build(build_id)
        if build:
            from dataclasses import asdict
            return asdict(build)
        return None


_engine: Optional[BuildEngine] = None


def get_build_engine() -> BuildEngine:
    global _engine
    if _engine is None:
        _engine = BuildEngine()
    return _engine