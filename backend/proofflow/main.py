import time
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from proofflow.config import get_api_key, get_rate_limit
from proofflow.migrations import init_db
from proofflow.routers import (
    actions,
    agentguard,
    artifacts,
    backups,
    cases,
    decisions,
    health,
    localproof,
    reports,
    restore,
    search,
)
from proofflow.version import __version__, release_name


class OptionalAPIKeyMiddleware(BaseHTTPMiddleware):
    """Require X-ProofFlow-Token header when PROOFFLOW_API_KEY is set."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        api_key = get_api_key()
        if api_key is None:
            return await call_next(request)
        # Health endpoint is always public
        if request.url.path == "/health":
            return await call_next(request)
        token = request.headers.get("X-ProofFlow-Token")
        if token != api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )
        return await call_next(request)


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter. Only active when PROOFFLOW_RATE_LIMIT is set."""

    def __init__(self, app: FastAPI, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests: deque[float] = deque()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        now = time.time()
        while self.requests and self.requests[0] < now - self.window:
            self.requests.popleft()
        if len(self.requests) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
            )
        self.requests.append(now)
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=release_name,
        version=__version__,
        description="Local-first AI workflow dashboard MVP.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(OptionalAPIKeyMiddleware)
    rate_limit = get_rate_limit()
    if rate_limit:
        app.add_middleware(SimpleRateLimitMiddleware, max_requests=rate_limit)
    app.include_router(cases.router)
    app.include_router(artifacts.router)
    app.include_router(agentguard.router)
    app.include_router(decisions.router)
    app.include_router(localproof.router)
    app.include_router(reports.router)
    app.include_router(search.router)
    app.include_router(actions.router)
    app.include_router(backups.router)
    app.include_router(restore.router)
    app.include_router(health.router)
    return app


app = create_app()
