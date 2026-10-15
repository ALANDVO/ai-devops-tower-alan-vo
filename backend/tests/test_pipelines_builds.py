"""Tests for pipelines and builds endpoints."""
import pytest
from httpx import AsyncClient


class TestPipelines:
    async def test_list_pipelines(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/pipelines", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "pipelines" in data
        assert "count" in data
        assert isinstance(data["pipelines"], list)

    async def test_list_pipelines_filter_by_service(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/pipelines?service=api-gateway", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for p in data["pipelines"]:
            assert p["service"] == "api-gateway"

    async def test_list_pipelines_filter_by_status(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/pipelines?status=active", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for p in data["pipelines"]:
            assert p.get("status") == "active"

    async def test_get_pipeline(self, client: AsyncClient, auth_headers):
        # First list to get a pipeline ID
        list_resp = await client.get("/api/pipelines", headers=auth_headers)
        pipelines = list_resp.json()["pipelines"]
        if pipelines:
            pid = pipelines[0]["pipeline_id"]
            resp = await client.get(f"/api/pipelines/{pid}", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["pipeline_id"] == pid
        else:
            # No pipelines seeded, test 404
            resp = await client.get("/api/pipelines/nonexistent", headers=auth_headers)
            assert resp.status_code == 404

    async def test_trigger_pipeline_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/pipelines/some-id/trigger", json={"branch": "main"})
        assert resp.status_code == 401

    async def test_trigger_pipeline(self, client: AsyncClient, auth_headers):
        list_resp = await client.get("/api/pipelines", headers=auth_headers)
        pipelines = list_resp.json()["pipelines"]
        if pipelines:
            pid = pipelines[0]["pipeline_id"]
            resp = await client.post(
                f"/api/pipelines/{pid}/trigger",
                json={"branch": "feature/test", "commit_sha": "abc123", "parameters": {"env": "test"}},
                headers=auth_headers,
            )
            assert resp.status_code == 202
            data = resp.json()
            assert "build_id" in data
            assert data["status"] == "queued"


class TestBuilds:
    async def test_list_builds(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/builds", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "builds" in data
        assert "count" in data

    async def test_list_builds_filter_by_pipeline(self, client: AsyncClient, auth_headers):
        list_resp = await client.get("/api/pipelines", headers=auth_headers)
        pipelines = list_resp.json()["pipelines"]
        if pipelines:
            pid = pipelines[0]["pipeline_id"]
            resp = await client.get(f"/api/builds?pipeline_id={pid}", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            for b in data["builds"]:
                assert b["pipeline_id"] == pid

    async def test_list_builds_filter_by_status(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/builds?status=success", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for b in data["builds"]:
            assert b["status"] == "success"

    async def test_get_build(self, client: AsyncClient, auth_headers):
        list_resp = await client.get("/api/builds", headers=auth_headers)
        builds = list_resp.json()["builds"]
        if builds:
            bid = builds[0]["build_id"]
            resp = await client.get(f"/api/builds/{bid}", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["build_id"] == bid
            assert "stages" in data

    async def test_analyze_build_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/builds/some-id/analyze")
        assert resp.status_code == 401

    async def test_analyze_build_success(self, client: AsyncClient, auth_headers):
        list_resp = await client.get("/api/builds", headers=auth_headers)
        builds = list_resp.json()["builds"]
        if builds:
            bid = builds[0]["build_id"]
            resp = await client.post(f"/api/builds/{bid}/analyze", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["build_id"] == bid
            assert "analysis" in data

    async def test_analyze_build_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/builds/nonexistent-build/analyze", headers=auth_headers)
        assert resp.status_code == 404