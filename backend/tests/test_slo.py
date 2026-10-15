"""Tests for SLO endpoints."""
import pytest
from httpx import AsyncClient


class TestSLO:
    async def test_list_slos(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/slo", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "slos" in data
        assert "count" in data
        assert isinstance(data["slos"], list)
        assert data["count"] >= 4  # Default seeded SLOs

    async def test_slo_structure(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/slo", headers=auth_headers)
        data = resp.json()
        for slo in data["slos"]:
            assert "slo_id" in slo
            assert "service" in slo
            assert "name" in slo
            assert "objective" in slo
            assert "window_days" in slo
            assert "metric" in slo
            assert "threshold" in slo
            assert 0 < slo["objective"] <= 1
            assert slo["window_days"] in (30, 90)

    async def test_slo_budget(self, client: AsyncClient, auth_headers):
        list_resp = await client.get("/api/slo", headers=auth_headers)
        slos = list_resp.json()["slos"]
        if slos:
            sid = slos[0]["slo_id"]
            resp = await client.get(f"/api/slo/{sid}/budget", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert "slo_id" in data
            assert "objective" in data
            assert "actual_reliability" in data
            assert "budget_percentage" in data
            assert "status" in data
            assert data["status"] in ("healthy", "warning", "critical", "exhausted")
            assert 0 <= data["budget_percentage"] <= 100

    async def test_slo_budget_not_found(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/slo/nonexistent/budget", headers=auth_headers)
        assert resp.status_code == 404

    async def test_slo_burn_rate(self, client: AsyncClient, auth_headers):
        list_resp = await client.get("/api/slo", headers=auth_headers)
        slos = list_resp.json()["slos"]
        if slos:
            sid = slos[0]["slo_id"]
            resp = await client.get(f"/api/slo/{sid}/burn-rate?window=30d", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert "slo_id" in data
            assert "window" in data
            assert "burn_rate" in data
            assert "severity" in data
            assert data["severity"] in ("none", "SEV3", "SEV2", "SEV1")

    async def test_slo_burn_rate_windows(self, client: AsyncClient, auth_headers):
        list_resp = await client.get("/api/slo", headers=auth_headers)
        slos = list_resp.json()["slos"]
        if slos:
            sid = slos[0]["slo_id"]
            for window in ["1h", "6h", "24h", "30d"]:
                resp = await client.get(f"/api/slo/{sid}/burn-rate?window={window}", headers=auth_headers)
                assert resp.status_code == 200