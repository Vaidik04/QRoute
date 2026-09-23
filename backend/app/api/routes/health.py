from fastapi import APIRouter
from app.schemas.health import HealthResponse
from app.core.config import settings

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse, summary="Health Check")
async def health_check():
    return HealthResponse(
        status="ok",
        service="q-transit-nexus-backend",
        version=settings.APP_VERSION
    )
