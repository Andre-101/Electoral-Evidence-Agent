import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiError, ApiResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/case/{review_case_id}", response_model=ApiResponse)
def generate_case_report(
    review_case_id: uuid.UUID,
    export_format: str = "HTML",
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = ReportService(db).generate_case_report(review_case_id, export_format)
        return ApiResponse(success=True, status="REPORT_GENERATED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="CASE_REPORT_GENERATION_FAILED", message=str(exc))],
        )


@router.post("/executive/{ingestion_run_id}", response_model=ApiResponse)
def generate_executive_report(
    ingestion_run_id: uuid.UUID,
    export_format: str = "HTML",
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = ReportService(db).generate_executive_report(ingestion_run_id, export_format)
        return ApiResponse(success=True, status="REPORT_GENERATED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="EXECUTIVE_REPORT_GENERATION_FAILED", message=str(exc))],
        )


@router.get("/{report_id}", response_model=ApiResponse)
def get_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = ReportService(db).get_report(report_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="REPORT_QUERY_FAILED", message=str(exc))],
        )


@router.get("/{report_id}/html")
def get_report_html(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    try:
        html = ReportService(db).read_report_html(report_id)
        return Response(content=html, media_type="text/html")
    except Exception as exc:
        return Response(content=f"Report not found: {exc}", status_code=404)
