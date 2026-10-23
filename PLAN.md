# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

multi-provider-llm

## Roadmap

### restructure-baseline — Restructure to standard layout and add missing baseline files

Status: done

Acceptance:
- backend/app/main.py exports FastAPI app
- backend/app/api/, services/, models/, core/ modules exist
- backend/requirements.txt with pinned deps
- backend/Dockerfile with nonroot user
- frontend/package.json with React+TS+Vite, build/test scripts
- frontend/package-lock.json committed
- frontend/Dockerfile with nonroot user
- compose.yaml with Keycloak and persistent volumes
- portfolio.json at root with schema_version, name, owner, email, domain, workflows, auth, llm_providers
- CHANGELOG.md with actual changes
- pyproject.toml with author metadata
- .github/workflows/ci.yml running backend pytest, frontend npm ci/build/test, Docker builds
- At least 12 meaningful backend tests
- At least 3 meaningful frontend tests
- All tests pass

Implementation: `backend/app/main.py`, `backend/app/api/routes.py`, `backend/app/api/auth.py`, `backend/app/api/schemas.py`, `backend/app/api/middleware.py`, `backend/app/core/config.py`, `backend/app/services/pipelines.py`, `backend/app/services/builds.py`, `backend/app/services/artifacts.py`, `backend/app/services/deploy.py`, `backend/app/services/slo.py`, `backend/app/services/incidents.py`, `backend/app/services/releases.py`, `backend/app/services/alerts.py`, `backend/app/services/analysis.py`, `backend/app/services/observability.py`, `backend/requirements.txt`, `backend/Dockerfile`, `backend/tests/conftest.py`, `backend/tests/test_health_auth.py`, `backend/tests/test_pipelines_builds.py`, `backend/tests/test_slo.py`, `backend/tests/test_incidents_releases.py`, `backend/tests/test_deploy_alerts_artifacts.py`, `backend/tests/test_rbac_domain.py`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/auth/AuthContext.tsx`, `frontend/src/api/client.ts`, `frontend/src/components/Sidebar.tsx`, `frontend/src/components/SLOChart.tsx`, `frontend/src/components/ReleaseNotes.tsx`, `frontend/src/components/IncidentTimeline.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Pipeline.tsx`, `frontend/src/pages/SLO.tsx`, `frontend/src/pages/Incidents.tsx`, `frontend/src/pages/Releases.tsx`, `frontend/src/pages/Builds.tsx`, `frontend/src/pages/Login.tsx`, `frontend/src/styles/index.css`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/vitest.config.ts`, `frontend/src/test/setup.tsx`, `frontend/src/components/__tests__/components.test.tsx`, `compose.yaml`, `portfolio.json`, `CHANGELOG.md`, `pyproject.toml`, `.github/workflows/ci.yml`

Tests: `backend/tests/test_health_auth.py`, `backend/tests/test_pipelines_builds.py`, `backend/tests/test_slo.py`, `backend/tests/test_incidents_releases.py`, `backend/tests/test_deploy_alerts_artifacts.py`, `backend/tests/test_rbac_domain.py`, `frontend/src/components/__tests__/components.test.tsx`

### multi-provider-llm — Multi-provider LLM adapter (OpenAI-compatible, Anthropic, Gemini, Ollama)

Status: done

Acceptance:
- LLM_PROVIDER and LLM_BASE_URL added to config with defaults
- Shared LLM adapter module supports OpenAI-compatible, Anthropic, Gemini, Ollama
- analysis.py, incidents.py, releases.py use shared adapter
- Provider selection via LLM_PROVIDER env var works at runtime
- Tests cover adapter routing and error handling for each provider type
- Existing tests still pass

Implementation: `backend/app/core/config.py`, `backend/app/services/llm.py`, `backend/app/services/analysis.py`, `backend/app/services/incidents.py`, `backend/app/services/releases.py`, `backend/tests/test_llm_adapter.py`

Tests: `backend/tests/test_llm_adapter.py`, `backend/tests/test_health_auth.py`, `backend/tests/test_pipelines_builds.py`, `backend/tests/test_slo.py`, `backend/tests/test_incidents_releases.py`, `backend/tests/test_deploy_alerts_artifacts.py`, `backend/tests/test_rbac_domain.py`, `frontend/src/components/__tests__/components.test.tsx`

