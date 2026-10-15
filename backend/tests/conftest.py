"""Pytest configuration and fixtures."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.config import settings


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_settings():
    """Override settings for testing."""
    with patch.object(settings, "LLM_API_KEY", "test-key-12345678901234567890"):
        with patch.object(settings, "JWT_SECRET", "test-secret-key-for-testing-only"):
            with patch.object(settings, "DEBUG", True):
                yield settings


@pytest_asyncio.fixture
async def client(mock_settings):
    """Async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Valid auth headers for testing."""
    from app.api.auth import create_token
    token = create_token("test@example.com", "devops")["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers():
    """Viewer role headers (limited permissions)."""
    from app.api.auth import create_token
    token = create_token("viewer@example.com", "viewer")["access_token"]
    return {"Authorization": f"Bearer {token}"}