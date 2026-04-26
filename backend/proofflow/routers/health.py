from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def read_health() -> dict[str, bool | str]:
    return {"ok": True, "service": "proofflow-backend"}

