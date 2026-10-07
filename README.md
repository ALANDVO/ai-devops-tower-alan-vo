# AI DevOps Control Tower

Enterprise AI-powered DevOps platform with deployment pipeline management, SLO monitoring with error budget tracking, incident response automation, LLM-powered build failure analysis, and release notes auto-generation.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        React Frontend                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │Pipeline  │  │   SLO    │  │Incidents │  │   Releases   │ │
│  │  Visual  │  │ Dashboard│  │ Timeline │  │    Mgmt      │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │
└───────────────────────────┬──────────────────────────────────┘
                            │ REST /api/*
┌───────────────────────────▼──────────────────────────────────┐
│                      FastAPI Backend                           │
│  ┌────────┐  ┌──────────────┐  ┌───────────────────────────┐ │
│  │ Auth   │  │  Middleware  │  │           Routes           │ │
│  │ SAML   │  │ Logging      │  │  /pipelines /builds /slo   │ │
│  │ JWT    │  │ Rate Limit   │  │  /incidents /releases      │ │
│  └────────┘  └──────────────┘  └───────────────────────────┘ │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐ │
│  │   CI/CD Layer        │  │        LLM Integration          │ │
│  │  Pipeline Engine     │  │  Build Failure Analysis         │ │
│  │  Build Triggers      │  │  Root Cause Analysis            │ │
│  │  Artifact Mgmt       │  │  Postmortem Generation          │ │
│  └─────────────────────┘  │  Release Notes Generation        │ │
│  ┌─────────────────────┐  └─────────────────────────────────┘ │
│  │   Deploy Layer        │                                    │
│  │  Canary / Blue-Green  │  ┌─────────────────────────────────┐ │
│  │  Rolling Strategies   │  │        Monitoring                │ │
│  │  Rollback Engine      │  │  SLO / Error Budgets / Burn Rate │ │
│  └─────────────────────┘  │  Alerts / Observability           │ │
│                            └─────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
git clone https://github.com/ALANDVO/ai-devops-tower-alan-vo.git
cd ai-devops-tower-alan-vo
cp .env.example .env
docker compose up -d
# Open http://localhost:8000
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/auth/me` | Get current user |
| `GET` | `/api/pipelines` | List pipelines |
| `POST` | `/api/pipelines/{id}/trigger` | Trigger pipeline |
| `GET` | `/api/pipelines/{id}/status` | Pipeline status |
| `GET` | `/api/builds` | Build history |
| `POST` | `/api/builds/{id}/analyze` | LLM build failure analysis |
| `GET` | `/api/artifacts` | Artifact list |
| `POST` | `/api/deploy` | Start deployment |
| `GET` | `/api/deploy/{id}/status` | Deployment status |
| `POST` | `/api/deploy/{id}/rollback` | Trigger rollback |
| `GET` | `/api/slo` | SLO definitions |
| `GET` | `/api/slo/{id}/budget` | Error budget status |
| `GET` | `/api/slo/{id}/burn-rate` | Burn rate metrics |
| `GET` | `/api/incidents` | Incident list |
| `POST` | `/api/incidents` | Create incident |
| `POST` | `/api/incidents/{id}/analyze` | AI root cause analysis |
| `POST` | `/api/incidents/{id}/postmortem` | Generate postmortem |
| `GET` | `/api/releases` | Release list |
| `POST` | `/api/releases/{id}/notes` | Generate release notes |
| `POST` | `/api/releases/{id}/promote` | Promote release |
| `GET` | `/api/alerts` | Alert rules |
| `POST` | `/api/alerts` | Create alert rule |

## SSO Setup

### SAML
1. Set `SAML_IDP_ENTITY` to your IdP metadata URL
2. Set `SAML_IDP_CERT` to your IdP X.509 certificate (base64)
3. Set `SAML_ACS_URL` to `https://yourdomain.com/saml/acs`
4. Configure SP metadata at `/saml/metadata`

### OAuth2
1. Register your app with the OAuth provider
2. Set `OAUTH_CLIENT_ID` and `OAUTH_CLIENT_SECRET`
3. Set `OAUTH_REDIRECT_URI` to `https://yourdomain.com/auth/callback`
4. RBAC roles: `admin`, `devops`, `developer`, `viewer`

## Docker Deployment

```yaml
# docker-compose.yml
services:
  devops-tower:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
```

## Deployment Strategies

- **Canary**: Route 5% → 25% → 50% → 100% of traffic with health gates
- **Blue-Green**: Full parallel environment switch with instant rollback
- **Rolling**: Batch updates with configurable max-unavailable

## Error Budget Model

SLOs track error budgets over configurable windows (30d, 90d).
Burn rate thresholds trigger severity-graded alerts:
- 14.4x burn over 1h → SEV1 (page on-call)
- 6x burn over 6h → SEV2 (notify)
- 3x burn over 24h → SEV3 (ticket)

**Built by [Alan Vo](https://github.com/ALANDVO)** | alanvo@gmail.com | AI, ML & DevOps
