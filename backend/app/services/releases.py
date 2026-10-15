"""Release management, promotion, versioning, LLM release notes generation."""

import time
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class Release:
    release_id: str
    service: str
    version: str
    status: str = "draft"  # draft, staging, production, archived
    description: str = ""
    changelog: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    promoted_at: Optional[float] = None
    notes: Optional[str] = None
    created_by: str = ""
    environment: str = "development"


class ReleaseEngine:
    def __init__(self):
        self._releases: Dict[str, Release] = {}

    def init(self, data_dir: str):
        self._data_dir = Path(data_dir) / "releases"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._seed()

    def _seed(self):
        """Seed with sample releases."""
        r1 = Release(
            release_id="rel-2024-01-15",
            service="api-gateway",
            version="2.4.0",
            status="production",
            description="Major release with rate limiting improvements",
            changelog=["Added configurable rate limiting per API key", "Reduced p99 latency by 40%", "Fixed connection leak in WebSocket handler"],
            created_by="release-bot",
            environment="production",
            promoted_at=time.time() - 86400 * 3,
        )
        r2 = Release(
            release_id="rel-2024-01-18",
            service="orders-service",
            version="1.12.0",
            status="staging",
            description="New payment provider integration",
            changelog=["Added Stripe webhook processing", "Refund flow improvements", "Currency conversion support"],
            created_by="dev-team",
            environment="staging",
        )
        self._releases[r1.release_id] = r1
        self._releases[r2.release_id] = r2

    def create_release(self, service: str, version: str, description: str, changelog: List[str], user: str) -> Release:
        rel_id = f"rel-{uuid.uuid4().hex[:10]}"
        release = Release(
            release_id=rel_id, service=service, version=version,
            description=description, changelog=changelog, created_by=user,
        )
        self._releases[rel_id] = release
        return release

    def list_releases(self, service: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[dict]:
        releases = list(self._releases.values())
        if service:
            releases = [r for r in releases if r.service == service]
        if status:
            releases = [r for r in releases if r.status == status]
        releases.sort(key=lambda r: r.created_at, reverse=True)
        return [asdict(r) for r in releases[:limit]]

    def get_release(self, release_id: str) -> Optional[dict]:
        r = self._releases.get(release_id)
        return asdict(r) if r else None

    def promote(self, release_id: str, environment: str, user: str) -> dict:
        r = self._releases.get(release_id)
        if not r:
            raise ValueError(f"Release {release_id} not found")
        r.status = environment
        r.environment = environment
        r.promoted_at = time.time()
        return {"status": r.status, "environment": environment, "promoted_at": r.promoted_at}

    async def generate_notes(self, release_id: str) -> Optional[dict]:
        """LLM-powered release notes generation."""
        r = self._releases.get(release_id)
        if not r:
            return None

        changelog_text = "\n".join(f"- {item}" for item in r.changelog)
        prompt = f"""Generate professional release notes for the following release.

Service: {r.service}
Version: {r.version}
Description: {r.description}

Changelog items:
{changelog_text}

Requirements:
- Customer-facing tone (not developer-facing)
- Group changes by category: New Features, Improvements, Bug Fixes, Breaking Changes
- Each item should explain the user impact, not just the technical change
- Include a brief summary paragraph at the top
- End with upgrade instructions if applicable
- Keep it concise but complete
- Format in Markdown"""

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
                notes = data["content"][0]["text"]
                r.notes = notes
                return {"notes": notes, "version": r.version, "service": r.service}
        except Exception as e:
            return {"notes": f"Generation unavailable: {str(e)}", "error": True}


from app.core.config import settings

_engine: Optional[ReleaseEngine] = None

def get_release_engine() -> ReleaseEngine:
    global _engine
    if _engine is None:
        _engine = ReleaseEngine()
    return _engine
