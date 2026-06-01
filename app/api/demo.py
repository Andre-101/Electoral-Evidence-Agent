from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiError, ApiResponse
from app.services.demo_service import DemoService

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/run", response_model=ApiResponse)
def run_demo(
    sample_name: str = "sample_territorial_outlier.csv",
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = DemoService(db).run_demo_pipeline(sample_name)
        return ApiResponse(success=True, status="DEMO_COMPLETED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="DEMO_PIPELINE_FAILED", message=str(exc))],
        )
