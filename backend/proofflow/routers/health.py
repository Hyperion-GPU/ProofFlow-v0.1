from fastapi import APIRouter

from proofflow.version import __version__, release_name, release_stage

router = APIRouter(tags=["health"])


@router.get("/health")
def read_health() -> dict[str, bool | str]:
    return {
        "ok": True,
        "service": "proofflow-backend",
        "version": __version__,
        "release_stage": release_stage,
        "release_name": release_name,
    }
