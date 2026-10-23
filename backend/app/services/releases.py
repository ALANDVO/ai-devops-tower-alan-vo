"""Release management, promotion, versioning, LLM release notes generation."""

import time
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

from app.core.config import settings
from app.services.llm import get_llm_adapter, LLMResponse


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
            release_id="rel-seed-001",
            service="user-api",
            version="2.4.0",
            status="production",
            description="Add user profile management and avatar uploads",
            changelog=[
                "feat: User profile page with editable fields",
                "feat: Avatar upload with automatic resizing and CDN",
                "fix: Race condition in session refresh",
                "improvement: Reduced API latency by 15% via query optimization",
            ],
            created_by="deploy-bot",
            environment="production",
            created_at=time.time() - 86400 * 7,
            promoted_at=time.time() - 86400 * 6,
            notes=None,
        )
        r2 = Release(
            release_id="rel-seed-002",
            service="payment-gateway",
            version="1.3.0",
            status="staging",
            description="Support for Apple Pay and Google Pay",
            changelog=[
                "feat: Apple Pay integration via PaymentRequest API",
                "feat: Google Pay support with tokenized cards",
                "fix: Webhook retry logic for failed payments",
                "improvement: Added idempotency keys for all mutating endpoints",
            ],
            created_by="deploy-bot",
            environment="staging",
            created_at=time.time() - 86400 * 2,
            notes=None,
        )
        self._releases[r1.release_id] = r1
        self._releases[r2.release_id] = r2

    def create_release(self, service: str, version: str, description: str, changelog: List[str], user: str) -> Release:
        rel_id = f"rel-{uuid.uuid4().hex[:10]}"
        release = Release(
            release_id=rel_id,
            service=service,
            version=version,
            description=description,
            changelog=changelog,
            created_by=user,
            status="draft",
        )
        self._releases[rel_id] = release
        return release

    def list_releases(self, service: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[dict]:
        releases = list(self._releases.values())
        if service:
            releases = [r for r in releases if r.service == service]
        if status:
            releases = [r for r in releases if r.status == status]
        releases.sort(key=lambda x: x.created_at, reverse=True)
        return [asdict(r) for r in releases[:limit]]

    def get_release(self, release_id: str) -> Optional[dict]:
        r = self._releases.get(release_id)
        return asdict(r) if r else None

    def promote(self, release_id: str, environment: str, user: str) -> dict:
        r = self._releases.get(release_id)
        if not r:
            return {"status": "not_found", "error": True}
        valid_envs = ["development", "staging", "production"]
        if environment not in valid_envs:
            return {"status": "invalid_environment", "error": True}
        r.status = environment
        r.promoted_at = time.time()
        r.environment = environment
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

        response: LLMResponse = await get_llm_adapter().complete(prompt)

        if response.error:
            return {"notes": f"Generation unavailable: {response.error}", "error": True, "provider": response.provider, "model": response.model}

        notes = response.content
        r.notes = notes
        return {"notes": notes, "version": r.version, "service": r.service, "provider": response.provider, "model": response.model, "usage": response.usage}


_engine: Optional[ReleaseEngine] = None


def get_release_engine() -> ReleaseEngine:
    global _engine
    if _engine is None:
        _engine = ReleaseEngine()
    return _engine