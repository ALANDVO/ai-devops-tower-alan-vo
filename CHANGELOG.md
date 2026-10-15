# Changelog

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

## [Unreleased]

### Planned
- Full OIDC/Keycloak authentication flow with PKCE
- SAML identity provider broker configuration
- Multi-provider LLM abstraction (OpenAI, Anthropic, Gemini, Ollama)
- Persistent SQLite storage with SQLAlchemy
- Integration tests with testcontainers
- Webhook support for CI/CD systems (GitHub Actions, GitLab CI, Jenkins)