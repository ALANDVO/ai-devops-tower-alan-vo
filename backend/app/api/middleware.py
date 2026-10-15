"""Middleware: CORS, request logging, rate limiting, error handling."""

import time
import uuid
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from typing import Dict


class RequestContext(BaseHTTPMiddleware):
    """Attach request ID and timing to every request."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        request.state.start_time = time.monotonic()
        response = await call_next(request)
        elapsed = (time.monotonic() - request.state.start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed:.1f}ms"
        return response


class RateLimiter(BaseHTTPMiddleware):
    """Simple in-memory rate limiter per IP."""

    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: Dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        hits = self._hits.get(key, [])
        hits = [t for t in hits if now - t < self.window]
        if len(hits) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Retry in " + str(int(self.window - (now - hits[0]))) + "s."},
                headers={"Retry-After": str(self.window)},
            )
        hits.append(now)
        self._hits[key] = hits
        return await call_next(request)


class GlobalErrorHandler(Exception):
    """Custom application error."""
    def __init__(self, status: int, message: str, code: str = "error"):
        self.status = status
        self.message = message
        self.code = code


def setup_middleware(app: FastAPI):
    """Register all middleware on the FastAPI app."""
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time"],
    )
    app.add_middleware(RateLimiter, max_requests=120, window_seconds=60)
    app.add_middleware(RequestContext)

    @app.exception_handler(Exception)
    async def handle_exception(request: Request, exc: Exception):
        if isinstance(exc, GlobalErrorHandler):
            return JSONResponse(status_code=exc.status, content={"error": exc.code, "detail": exc.message})
        return JSONResponse(status_code=500, content={"error": "internal_error", "detail": str(exc)})
