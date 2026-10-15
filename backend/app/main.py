"""AI DevOps Control Tower — FastAPI application entry point."""

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import router
from app.api.auth import auth_router
from app.api.middleware import setup_middleware
from app.services.observability import get_observability


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown hooks."""
    # Startup
    observability = get_observability()
    observability.init(settings.DATA_DIR, settings.LOG_DIR)
    from app.services.pipelines import get_pipeline_engine
    from app.services.slo import get_slo_engine
    from app.services.incidents import get_incident_engine
    from app.services.releases import get_release_engine
    get_pipeline_engine().init(settings.DATA_DIR)
    get_slo_engine().init(settings.DATA_DIR)
    get_incident_engine().init(settings.DATA_DIR)
    get_release_engine().init(settings.DATA_DIR)
    yield
    # Shutdown
    observability.close()


app = FastAPI(
    title="AI DevOps Control Tower",
    description="Enterprise AI DevOps platform with SLO monitoring, incident automation, and LLM-powered build analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api")
app.include_router(auth_router, prefix="/api/auth")
setup_middleware(app)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
    )
