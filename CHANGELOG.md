# Changelog

## 1.4.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.3.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-15

### Added
- Initial project structure with FastAPI backend and React TypeScript frontend
- CI/CD pipeline management: pipeline registration, build triggering, stage tracking
- Build failure analysis with LLM-powered root cause identification
- SLO definitions with error budget tracking and burn rate calculation (1h/6h/24h windows)
- Incident lifecycle management: creation, severity routing, timeline, AI root cause analysis, postmortem generation
- Release management: versioning, multi-environment promotion, LLM-generated release notes
- Deployment engine with canary, blue-green, and rolling strategies with health checks and rollback
- Alert rules with escalation policies and notification channels
- Observability layer: metrics, logs, distributed traces
- JWT-based authentication with RBAC (admin, devops, developer, viewer)
- SAML/OAuth2 integration points for SSO
- Keycloak integration in Docker Compose for local development
- Responsive dashboard with real-time stats, pipeline cards, SLO budget bars, incident timeline, release notes viewer
- REST API with OpenAPI documentation

### Fixed
- Restructured codebase to standard backend/app layout
- Added comprehensive test suite (backend pytest, frontend vitest)
- Added CI/CD workflow with Docker builds
- Added portfolio.json, pyproject.toml, CHANGELOG.md

## [1.1.0] - 2026-10-23

### Added
- Multi-provider LLM adapter supporting OpenAI-compatible, Anthropic, Gemini, and Ollama
- LLM_PROVIDER and LLM_BASE_URL configuration options for runtime provider selection
- Shared LLM adapter module (backend/app/services/llm.py) with unified interface
- Refactored build analysis, incident root cause analysis, and release notes generation to use shared adapter
- Comprehensive test suite for LLM adapters (14 tests covering all providers and error handling)

### Changed
- Updated config.py with LLM_PROVIDER (default: anthropic) and LLM_BASE_URL settings
- Refactored analysis.py, incidents.py, releases.py to use shared LLM adapter
- Restored original incident on-call routing logic for test compatibility

### Tests
- All 87 backend tests pass (73 original + 14 new LLM adapter tests)
- All 12 frontend tests pass
### Changed
- Updated Gemini adapter to use `systemInstruction` field (modern API) instead of manual role alternation for system prompts

### Planned
- Full OIDC/Keycloak authentication flow with PKCE
- SAML identity provider broker configuration
- Persistent SQLite storage with SQLAlchemy
- Integration tests with testcontainers
- Webhook support for CI/CD systems (GitHub Actions, GitLab CI, Jenkins)

## [1.2.0] - 2026-11-06

### Added
- LLM streaming responses for all providers (OpenAI-compatible, Anthropic, Gemini, Ollama)
- LLMStreamChunk dataclass for normalized streaming chunks
- Abstract stream() method on LLMAdapter base class
- Streaming implementation in all four provider adapters
- stream_llm() convenience function for one-off streaming calls
- 6 new streaming tests covering success and error handling per provider

### Changed
- Extended LLM adapter interface with streaming capability

### Tests
- All 93 backend tests pass (87 original + 6 new streaming tests)
- All 12 frontend tests pass

---

Alan Vo · [alanvo.net](https://alanvo.net) · [X: @alanvoasi](https://x.com/alanvoasi)
