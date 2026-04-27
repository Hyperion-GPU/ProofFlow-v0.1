from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from proofflow.migrations import init_db
from proofflow.routers import (
    actions,
    agentguard,
    artifacts,
    cases,
    decisions,
    health,
    localproof,
    reports,
    search,
)
from proofflow.version import __version__, release_name


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
    app.include_router(cases.router)
    app.include_router(artifacts.router)
    app.include_router(agentguard.router)
    app.include_router(decisions.router)
    app.include_router(localproof.router)
    app.include_router(reports.router)
    app.include_router(search.router)
    app.include_router(actions.router)
    app.include_router(health.router)
    return app


app = create_app()
