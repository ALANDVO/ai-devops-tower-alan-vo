"""Tests for deployment, alerts, and artifacts endpoints."""
import pytest
from httpx import AsyncClient


class TestDeployment:
    async def test_start_deployment_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/deploy", json={"service": "test", "artifact": "test:latest"})
        assert resp.status_code == 401

    async def test_start_deployment(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/deploy",
            json={
                "service": "api-gateway",
                "artifact": "api-gateway:v1.2.3",
                "environment": "staging",
                "strategy": "canary",
                "max_unavailable": 25,
                "health_check_path": "/health",
                "timeout_seconds": 300,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "deployment_id" in data
        assert data["status"] == "started"
        assert data["strategy"] == "canary"

    async def test_deployment_strategies(self, client: AsyncClient, auth_headers):
        for strategy in ["rolling", "canary", "blue-green"]:
            resp = await client.post(
                "/api/deploy",
                json={"service": "test", "artifact": "test:latest", "strategy": strategy},
                headers=auth_headers,
            )
            assert resp.status_code == 202
            data = resp.json()
            assert data["strategy"] == strategy

    async def test_deployment_status(self, client: AsyncClient, auth_headers):
        # Start a deployment first
        start_resp = await client.post(
            "/api/deploy",
            json={"service": "test", "artifact": "test:latest", "environment": "staging"},
            headers=auth_headers,
        )
        dep_id = start_resp.json()["deployment_id"]
        resp = await client.get(f"/api/deploy/{dep_id}/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["deployment_id"] == dep_id
        assert "status" in data
        assert "steps" in data
        assert "health_score" in data

    async def test_deployment_status_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/deploy/nonexistent/status", headers=auth_headers)
        assert resp.status_code == 404

    async def test_rollback_deployment_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/deploy/some-id/rollback")
        assert resp.status_code == 401

    async def test_rollback_deployment(self, client: AsyncClient, auth_headers):
        start_resp = await client.post(
            "/api/deploy",
            json={"service": "test", "artifact": "test:latest"},
            headers=auth_headers,
        )
        dep_id = start_resp.json()["deployment_id"]
        resp = await client.post(f"/api/deploy/{dep_id}/rollback", headers=auth_headers)
        assert resp.status_code == 202
        data = resp.json()
        assert data["deployment_id"] == dep_id
        assert data["status"] == "rolled_back"
        assert "reason" in data


class TestAlerts:
    async def test_list_alerts(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/alerts", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        assert "count" in data
        assert isinstance(data["alerts"], list)
        assert data["count"] >= 2  # Default seeded alerts

    async def test_list_alerts_filter_by_service(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/alerts?service=api-gateway", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for a in data["alerts"]:
            assert a["service"] == "api-gateway"

    async def test_alert_structure(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/alerts", headers=auth_headers)
        data = resp.json()
        for alert in data["alerts"]:
            assert "rule_id" in alert
            assert "name" in alert
            assert "service" in alert
            assert "metric" in alert
            assert "condition" in alert
            assert "threshold" in alert
            assert "duration_seconds" in alert
            assert "severity" in alert
            assert "notification_channels" in alert
            assert "enabled" in alert
            assert alert["condition"] in ("gt", "lt", "gte", "lte", "equals")

    async def test_create_alert_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/alerts", json={"name": "Test", "service": "test", "metric": "cpu", "condition": "gt", "threshold": 80})
        assert resp.status_code == 401

    async def test_create_alert(self, client: AsyncClient, auth_headers):
        resp = await client.post(
            "/api/alerts",
            json={
                "name": "High Memory Usage",
                "service": "test-service",
                "metric": "memory_usage",
                "condition": "gt",
                "threshold": 85.0,
                "duration_seconds": 300,
                "severity": "P2",
                "notification_channels": ["slack:#ops"],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "rule_id" in data
        assert data["name"] == "High Memory Usage"
        assert data["severity"] == "P2"
        assert data["enabled"] is True


class TestArtifacts:
    async def test_list_artifacts(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/artifacts", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "artifacts" in data
        assert "count" in data

    async def test_list_artifacts_filter_by_service(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/artifacts?service=api-gateway", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for a in data["artifacts"]:
            assert a.get("service") == "api-gateway"