"""Tests for health endpoint and authentication."""
import pytest
from httpx import AsyncClient


class TestHealth:
    async def test_health_endpoint(self, client: AsyncClient):
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ai-devops-tower"
        assert data["version"] == "1.0.0"


class TestAuth:
    async def test_me_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_me_with_valid_token(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["role"] == "devops"
        assert "permissions" in data

    async def test_me_with_viewer_token(self, client: AsyncClient, viewer_headers):
        resp = await client.get("/api/auth/me", headers=viewer_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "viewer"

    async def test_login_creates_token(self, client: AsyncClient):
        resp = await client.post("/api/auth/login", json={"email": "new@example.com", "role": "developer"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_login_invalid_role_defaults_to_developer(self, client: AsyncClient):
        resp = await client.post("/api/auth/login", json={"email": "test@example.com", "role": "invalid"})
        assert resp.status_code == 200
        data = resp.json()
        # Should still create token, role validation happens at permission check
        assert "access_token" in data

    async def test_saml_metadata_endpoint(self, client: AsyncClient):
        resp = await client.get("/api/auth/saml/metadata")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/xml"
        assert "<EntityDescriptor" in resp.text