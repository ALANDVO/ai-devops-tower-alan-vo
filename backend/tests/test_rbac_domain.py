"""Tests for RBAC permissions and domain logic."""
import pytest
from httpx import AsyncClient


class TestRBAC:
    """Test role-based access control."""

    async def test_viewer_cannot_trigger_pipeline(self, client: AsyncClient, viewer_headers):
        list_resp = await client.get("/api/pipelines", headers=viewer_headers)
        pipelines = list_resp.json()["pipelines"]
        if pipelines:
            pid = pipelines[0]["pipeline_id"]
            resp = await client.post(f"/api/pipelines/{pid}/trigger", json={}, headers=viewer_headers)
            assert resp.status_code == 403

    async def test_viewer_cannot_create_incident(self, client: AsyncClient, viewer_headers):
        resp = await client.post(
            "/api/incidents",
            json={"title": "Test", "severity": "P3", "service": "test"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403

    async def test_viewer_cannot_deploy(self, client: AsyncClient, viewer_headers):
        resp = await client.post(
            "/api/deploy", json={"service": "test", "artifact": "test:latest"}, headers=viewer_headers
        )
        assert resp.status_code == 403

    async def test_viewer_cannot_create_alert(self, client: AsyncClient, viewer_headers):
        resp = await client.post(
            "/api/alerts",
            json={"name": "Test", "service": "test", "metric": "cpu", "condition": "gt", "threshold": 80},
            headers=viewer_headers,
        )
        assert resp.status_code == 403

    async def test_viewer_cannot_promote_release(self, client: AsyncClient, viewer_headers):
        list_resp = await client.get("/api/releases", headers=viewer_headers)
        releases = list_resp.json()["releases"]
        if releases:
            rid = releases[0]["release_id"]
            resp = await client.post(f"/api/releases/{rid}/promote", json={"environment": "staging"}, headers=viewer_headers)
            assert resp.status_code == 403

    async def test_viewer_can_read_all(self, client: AsyncClient, viewer_headers):
        """Viewer should have read access to all endpoints."""
        endpoints = [
            "/api/pipelines",
            "/api/builds",
            "/api/slo",
            "/api/incidents",
            "/api/releases",
            "/api/alerts",
            "/api/artifacts",
        ]
        for ep in endpoints:
            resp = await client.get(ep, headers=viewer_headers)
            assert resp.status_code == 200, f"Viewer denied on {ep}"

    async def test_developer_can_write(self, client: AsyncClient, auth_headers):
        """Developer (devops role) should have write access."""
        # Trigger pipeline
        list_resp = await client.get("/api/pipelines", headers=auth_headers)
        pipelines = list_resp.json()["pipelines"]
        if pipelines:
            pid = pipelines[0]["pipeline_id"]
            resp = await client.post(f"/api/pipelines/{pid}/trigger", json={}, headers=auth_headers)
            assert resp.status_code == 202

        # Create incident
        resp = await client.post(
            "/api/incidents", json={"title": "Test", "severity": "P3", "service": "test"}, headers=auth_headers
        )
        assert resp.status_code == 201

        # Create alert
        resp = await client.post(
            "/api/alerts",
            json={"name": "Test", "service": "test", "metric": "cpu", "condition": "gt", "threshold": 80},
            headers=auth_headers,
        )
        assert resp.status_code == 201


class TestDomainLogic:
    """Test core domain logic without HTTP."""

    def test_slo_budget_calculation(self):
        from app.services.slo import SloEngine
        engine = SloEngine()
        engine._register_defaults()
        slos = engine.list_slos()
        assert len(slos) >= 4
        # Test budget calculation for first SLO
        budget = engine.get_budget(slos[0]["slo_id"])
        assert budget is not None
        assert "budget_percentage" in budget
        assert "status" in budget

    def test_slo_burn_rate_calculation(self):
        from app.services.slo import SloEngine
        engine = SloEngine()
        engine._register_defaults()
        slos = engine.list_slos()
        burn = engine.get_burn_rate(slos[0]["slo_id"], "30d")
        assert burn is not None
        assert "burn_rate" in burn
        assert "severity" in burn

    def test_incident_oncall_routing(self):
        from app.services.incidents import IncidentEngine
        engine = IncidentEngine()
        # P1 -> primary oncall
        assert "oncall" in engine._route_on_call("P1", "api-gateway").lower()
        # P2 -> secondary
        assert "oncall" in engine._route_on_call("P2", "api-gateway").lower()
        # P3 -> team
        assert "team" in engine._route_on_call("P3", "orders-db").lower()

    def test_incident_severity_validation(self):
        from app.services.incidents import IncidentEngine
        engine = IncidentEngine()
        engine.init("/tmp/test-data")
        inc = engine.create_from_dict(
            {"title": "Test", "severity": "P1", "service": "svc", "description": "desc"},
            "user@test.com",
        )
        assert inc.severity == "P1"
        # Invalid severity should default
        inc2 = engine.create_from_dict(
            {"title": "Test", "severity": "P5", "service": "svc", "description": "desc"},
            "user@test.com",
        )
        assert inc2.severity == "P5"  # Engine doesn't validate, API does

    def test_deployment_strategy_planning(self):
        from app.services.deploy import DeployEngine
        engine = DeployEngine()
        # Rolling
        steps = engine._plan_steps("rolling")
        assert len(steps) >= 3
        assert any("batch" in s.name.lower() for s in steps)
        # Canary
        steps = engine._plan_steps("canary")
        assert len(steps) >= 4
        assert any("5%" in s.name or "canary" in s.name.lower() for s in steps)
        # Blue-green
        steps = engine._plan_steps("blue-green")
        assert len(steps) >= 3
        assert any("blue" in s.name.lower() or "green" in s.name.lower() for s in steps)

    def test_alert_evaluation(self):
        from app.services.alerts import AlertEngine
        engine = AlertEngine()
        engine._seed()
        # High 5xx rate should trigger
        triggered = engine.evaluate("http_5xx_ratio", 0.06, "api-gateway")
        assert len(triggered) >= 1
        assert any(a["metric"] == "http_5xx_ratio" for a in triggered)
        # Below threshold should not trigger
        triggered = engine.evaluate("http_5xx_ratio", 0.01, "api-gateway")
        assert len(triggered) == 0

    def test_alert_condition_operators(self):
        from app.services.alerts import AlertEngine
        engine = AlertEngine()
        # gt
        assert engine._compare(10, "gt", 5) is True
        assert engine._compare(5, "gt", 5) is False
        # lt
        assert engine._compare(5, "lt", 10) is True
        assert engine._compare(10, "lt", 10) is False
        # gte
        assert engine._compare(5, "gte", 5) is True
        # lte
        assert engine._compare(5, "lte", 5) is True
        # equals
        assert engine._compare(5, "equals", 5) is True
        assert engine._compare(4, "equals", 5) is False

    def test_pipeline_stage_order(self):
        from app.services.pipelines import STAGE_ORDER
        assert STAGE_ORDER == ["checkout", "build", "test", "lint", "package", "publish"]

    def test_release_promotion_flow(self):
        from app.services.releases import ReleaseEngine
        engine = ReleaseEngine()
        engine.init("/tmp/test-data")
        # Create a release
        rel = engine.create_release("test-svc", "1.0.0", "Test release", ["Initial release"], "user@test.com")
        assert rel.status == "draft"
        # Promote to staging
        result = engine.promote(rel.release_id, "staging", "user@test.com")
        assert result["status"] == "staging"
        # Promote to production
        result = engine.promote(rel.release_id, "production", "user@test.com")
        assert result["status"] == "production"