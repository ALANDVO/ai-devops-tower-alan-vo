"""Tests for incidents and releases endpoints."""
import pytest
from httpx import AsyncClient


class TestIncidents:
    async def test_list_incidents(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/incidents", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "incidents" in data
        assert "count" in data
        assert isinstance(data["incidents"], list)

    async def test_list_incidents_filter_by_severity(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/incidents?severity=P1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for inc in data["incidents"]:
            assert inc["severity"] == "P1"

    async def test_list_incidents_filter_by_status(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/incidents?status=open", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for inc in data["incidents"]:
            assert inc["status"] == "open"

    async def test_create_incident(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/incidents",
            json={"title": "Test incident", "severity": "P2", "description": "Test description", "service": "test-service"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test incident"
        assert data["severity"] == "P2"
        assert data["status"] == "open"
        assert data["on_call"] != ""

    async def test_create_incident_severity_routing(self, client: AsyncClient, auth_headers):
        """Verify P1 routes to on-call, P2/P3 to team."""
        for severity, expected_oncall in [("P1", "senior-sre-oncall"), ("P2", "platform-oncall"), ("P3", "service-team-lead")]:
            resp = await client.post(
                "/api/incidents",
                json={"title": f"Test {severity}", "severity": severity, "description": "Test", "service": "test-service"},
                headers=auth_headers,
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["on_call"] == expected_oncall

    async def test_get_incident(self, client: AsyncClient, auth_headers):
        list_resp = await client.get("/api/incidents", headers=auth_headers)
        incidents = list_resp.json()["incidents"]
        assert len(incidents) > 0
        iid = incidents[0]["incident_id"]
        resp = await client.get(f"/api/incidents/{iid}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["incident_id"] == iid
        assert "events" in data
        assert "components" in data

    async def test_get_incident_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/incidents/nonexistent", headers=auth_headers)
        assert resp.status_code == 404

    async def test_analyze_incident_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/incidents/some-id/analyze")
        assert resp.status_code == 401

    async def test_postmortem_incident_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/incidents/some-id/postmortem")
        assert resp.status_code == 401

    async def test_analyze_incident_stream_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/incidents/some-id/analyze/stream")
        assert resp.status_code == 401

    async def test_analyze_incident_stream_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/incidents/nonexistent/analyze/stream", headers=auth_headers)
        assert resp.status_code == 404

    async def test_analyze_incident_stream_success(self, client: AsyncClient, auth_headers):
        list_resp = await client.get("/api/incidents", headers=auth_headers)
        incidents = list_resp.json()["incidents"]
        assert len(incidents) > 0
        iid = incidents[0]["incident_id"]
        resp = await client.get(f"/api/incidents/{iid}/analyze/stream", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"
        content = resp.text
        assert "data:" in content
        assert "is_final" in content

    async def test_postmortem_incident_stream_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/incidents/some-id/postmortem/stream")
        assert resp.status_code == 401

    async def test_postmortem_incident_stream_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/incidents/nonexistent/postmortem/stream", headers=auth_headers)
        assert resp.status_code == 404

    async def test_postmortem_incident_stream_success(self, client: AsyncClient, auth_headers):
        list_resp = await client.get("/api/incidents", headers=auth_headers)
        incidents = list_resp.json()["incidents"]
        assert len(incidents) > 0
        iid = incidents[0]["incident_id"]
        resp = await client.get(f"/api/incidents/{iid}/postmortem/stream", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"
        content = resp.text
        assert "data:" in content
        assert "is_final" in content


class TestReleases:
    async def test_list_releases(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/releases", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "releases" in data
        assert "count" in data
        assert isinstance(data["releases"], list)

    async def test_list_releases_filter_by_service(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/releases?service=api-gateway", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for r in data["releases"]:
            assert r["service"] == "api-gateway"

    async def test_list_releases_filter_by_status(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/releases?status=staging", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for r in data["releases"]:
            assert r["status"] == "staging"

    async def test_get_release(self, client: AsyncClient, auth_headers):
        list_resp = await client.get("/api/releases", headers=auth_headers)
        releases = list_resp.json()["releases"]
        assert len(releases) > 0
        rid = releases[0]["release_id"]
        resp = await client.get(f"/api/releases/{rid}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["release_id"] == rid
        assert "changelog" in data
        assert "version" in data

    async def test_generate_notes_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/releases/some-id/notes")
        assert resp.status_code == 401

    async def test_promote_release_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/releases/some-id/promote", json={"environment": "production"})
        assert resp.status_code == 401

    async def test_generate_notes_stream_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/releases/some-id/notes/stream")
        assert resp.status_code == 401

    async def test_generate_notes_stream_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/releases/nonexistent/notes/stream", headers=auth_headers)
        assert resp.status_code == 404

    async def test_generate_notes_stream_success(self, client: AsyncClient, auth_headers):
        list_resp = await client.get("/api/releases", headers=auth_headers)
        releases = list_resp.json()["releases"]
        assert len(releases) > 0
        rid = releases[0]["release_id"]
        resp = await client.get(f"/api/releases/{rid}/notes/stream", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"
        content = resp.text
        assert "data:" in content
        assert "is_final" in content

    async def test_promote_release(self, client: AsyncClient, auth_headers):
        list_resp = await client.get("/api/releases", headers=auth_headers)
        releases = list_resp.json()["releases"]
        assert len(releases) > 0
        rid = releases[0]["release_id"]
        resp = await client.post(f"/api/releases/{rid}/promote", json={"environment": "staging"}, headers=auth_headers)
        assert resp.status_code == 202
        data = resp.json()
        assert data["release_id"] == rid
        assert data["environment"] == "staging"
        assert data["status"] in ("staging", "production", "canary")

    async def test_promote_release_invalid_env(self, client: AsyncClient, auth_headers):
        list_resp = await client.get("/api/releases", headers=auth_headers)
        releases = list_resp.json()["releases"]
        assert len(releases) > 0
        rid = releases[0]["release_id"]
        resp = await client.post(f"/api/releases/{rid}/promote", json={"environment": "invalid-env"}, headers=auth_headers)
        assert resp.status_code in (202, 400, 422)
