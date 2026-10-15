"""Artifact storage and retrieval."""
from typing import Optional, List, Dict
from dataclasses import dataclass, field, asdict
import time
import uuid
from pathlib import Path


@dataclass
class Artifact:
    artifact_id: str
    service: str
    name: str
    version: str
    path: str
    size_bytes: int
    content_type: str
    created_at: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


class ArtifactStore:
    def __init__(self):
        self._artifacts: Dict[str, Artifact] = {}
        self._data_dir: Optional[Path] = None

    def init(self, data_dir: str):
        self._data_dir = Path(data_dir) / "artifacts"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._seed()

    def _seed(self):
        self._artifacts = {
            "art-1": Artifact(
                artifact_id="art-1",
                service="api-gateway",
                name="api-gateway",
                version="1.2.3",
                path="/artifacts/api-gateway-1.2.3.tar.gz",
                size_bytes=15728640,
                content_type="application/gzip",
            ),
            "art-2": Artifact(
                artifact_id="art-2",
                service="orders-service",
                name="orders-service",
                version="2.0.1",
                path="/artifacts/orders-service-2.0.1.tar.gz",
                size_bytes=22020096,
                content_type="application/gzip",
            ),
        }

    def list_artifacts(self, service: Optional[str] = None, limit: int = 50) -> List[dict]:
        artifacts = list(self._artifacts.values())
        if service:
            artifacts = [a for a in artifacts if a.service == service]
        artifacts.sort(key=lambda x: x.created_at, reverse=True)
        return [asdict(a) for a in artifacts[:limit]]


_store: Optional[ArtifactStore] = None


def get_artifact_store() -> ArtifactStore:
    global _store
    if _store is None:
        _store = ArtifactStore()
    return _store