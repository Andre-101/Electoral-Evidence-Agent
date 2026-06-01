from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constants import APP_VERSION
from app.core.settings import get_settings
from app.db.repositories.health_repo import HealthRepository
from app.db.session import get_db
from app.schemas.common import ApiResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse)
def health(db: Session = Depends(get_db)) -> ApiResponse:
    db_status = "ok" if HealthRepository(db).ping() else "error"
    return ApiResponse(
        success=True,
        status="OK",
        data={"service": "ok", "db_status": db_status},
    )


@router.get("/version", response_model=ApiResponse)
def version() -> ApiResponse:
    settings = get_settings()
    return ApiResponse(
        success=True,
        status="OK",
        data={
            "app_version": APP_VERSION,
            "pipeline_version": settings.pipeline_version,
            "rules_version": settings.rules_version,
            "scoring_version": settings.scoring_version,
        },
    )
