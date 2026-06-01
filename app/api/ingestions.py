import uuid

from fastapi import APIRouter, Body, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiError, ApiResponse
from app.services.core_load_service import CoreLoadService
from app.services.ingestion_service import IngestionService
from app.services.quality_validation_service import QualityValidationService
from app.services.metrics_service import MetricsService
from app.services.alert_service import AlertService
from app.services.scoring_service import ScoringService
from app.services.mapping_service import MappingService

router = APIRouter(prefix="/ingestions", tags=["ingestions"])


@router.post("", response_model=ApiResponse)
def create_ingestion(
    election_id: uuid.UUID | None = Form(default=None),
    source_name: str = Form(default="manual_upload"),
    source_url: str | None = Form(default=None),
    execution_mode: str = Form(default="EXPLORATORY"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = IngestionService(db).create_ingestion(
            file=file,
            election_id=election_id,
            source_name=source_name,
            source_url=source_url,
            execution_mode=execution_mode,
        )
        return ApiResponse(success=True, status="REGISTERED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="INGESTION_CREATE_FAILED", message=str(exc))],
        )


@router.post("/{ingestion_run_id}/profile", response_model=ApiResponse)
def profile_ingestion(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = IngestionService(db).profile_file(ingestion_run_id)
        return ApiResponse(success=True, status="PROFILED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="PROFILE_FAILED", message=str(exc))],
        )


@router.post("/{ingestion_run_id}/map", response_model=ApiResponse)
def map_ingestion(
    ingestion_run_id: uuid.UUID,
    payload: dict | None = Body(default=None),
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        manual_mappings = []
        if payload and isinstance(payload, dict):
            manual_mappings = payload.get("manual_mappings", [])
        data = MappingService(db).propose_mapping(ingestion_run_id, manual_mappings)
        return ApiResponse(success=True, status="MAPPED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="MAPPING_FAILED", message=str(exc))],
        )


@router.post("/{ingestion_run_id}/load-core", response_model=ApiResponse)
def load_core(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = CoreLoadService(db).load_to_core(ingestion_run_id)
        return ApiResponse(success=True, status="LOADED_TO_CORE", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="CORE_LOAD_FAILED", message=str(exc))],
        )


@router.post("/{ingestion_run_id}/run", response_model=ApiResponse)
def run_ingestion_pipeline(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = CoreLoadService(db).load_to_core(ingestion_run_id)
        return ApiResponse(success=True, status="LOADED_TO_CORE", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="PIPELINE_RUN_FAILED", message=str(exc))],
        )


@router.get("/{ingestion_run_id}/core-summary", response_model=ApiResponse)
def get_core_summary(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = CoreLoadService(db).get_core_summary(ingestion_run_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="CORE_SUMMARY_FAILED", message=str(exc))],
        )


@router.get("/{ingestion_run_id}/status", response_model=ApiResponse)
def get_ingestion_status(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = IngestionService(db).get_status(ingestion_run_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="INGESTION_STATUS_FAILED", message=str(exc))],
        )


@router.post("/{ingestion_run_id}/validate-quality", response_model=ApiResponse)
def validate_quality(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = QualityValidationService(db).validate_quality(ingestion_run_id)
        return ApiResponse(success=True, status="VALIDATED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="QUALITY_VALIDATION_FAILED", message=str(exc))],
        )


@router.get("/{ingestion_run_id}/quality-summary", response_model=ApiResponse)
def quality_summary(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = QualityValidationService(db).get_quality_summary(ingestion_run_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="QUALITY_SUMMARY_FAILED", message=str(exc))],
        )


@router.post("/{ingestion_run_id}/calculate-totals", response_model=ApiResponse)
def calculate_totals(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = MetricsService(db).calculate_table_totals(ingestion_run_id)
        return ApiResponse(success=True, status="METRICS_CALCULATED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="TABLE_TOTALS_FAILED", message=str(exc))],
        )


@router.get("/{ingestion_run_id}/table-totals", response_model=ApiResponse)
def table_totals(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = MetricsService(db).get_table_totals(ingestion_run_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="TABLE_TOTALS_QUERY_FAILED", message=str(exc))],
        )


@router.post("/{ingestion_run_id}/calculate-table-metrics", response_model=ApiResponse)
def calculate_table_metrics(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = MetricsService(db).calculate_table_metrics(ingestion_run_id)
        return ApiResponse(success=True, status="TABLE_METRICS_CALCULATED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="TABLE_METRICS_FAILED", message=str(exc))],
        )


@router.post("/{ingestion_run_id}/calculate-option-table-metrics", response_model=ApiResponse)
def calculate_option_table_metrics(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = MetricsService(db).calculate_option_table_metrics(ingestion_run_id)
        return ApiResponse(success=True, status="OPTION_TABLE_METRICS_CALCULATED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="OPTION_TABLE_METRICS_FAILED", message=str(exc))],
        )


@router.post("/{ingestion_run_id}/calculate-basic-metrics", response_model=ApiResponse)
def calculate_basic_metrics(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = MetricsService(db).calculate_all_basic_metrics(ingestion_run_id)
        return ApiResponse(success=True, status="BASIC_METRICS_CALCULATED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="BASIC_METRICS_FAILED", message=str(exc))],
        )


@router.get("/{ingestion_run_id}/table-metrics", response_model=ApiResponse)
def table_metrics(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = MetricsService(db).get_table_metrics(ingestion_run_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="TABLE_METRICS_QUERY_FAILED", message=str(exc))],
        )


@router.get("/{ingestion_run_id}/option-table-metrics", response_model=ApiResponse)
def option_table_metrics(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = MetricsService(db).get_option_table_metrics(ingestion_run_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="OPTION_TABLE_METRICS_QUERY_FAILED", message=str(exc))],
        )


@router.post("/{ingestion_run_id}/generate-eda-alerts", response_model=ApiResponse)
def generate_eda_alerts(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = AlertService(db).generate_eda_alerts(ingestion_run_id)
        return ApiResponse(success=True, status="ALERTS_GENERATED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="EDA_ALERT_GENERATION_FAILED", message=str(exc))],
        )


@router.get("/{ingestion_run_id}/eda-alerts", response_model=ApiResponse)
def eda_alerts(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = AlertService(db).get_eda_alerts(ingestion_run_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="EDA_ALERTS_QUERY_FAILED", message=str(exc))],
        )


@router.get("/{ingestion_run_id}/eda-summary", response_model=ApiResponse)
def eda_summary(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = AlertService(db).get_eda_summary(ingestion_run_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="EDA_SUMMARY_QUERY_FAILED", message=str(exc))],
        )


@router.post("/{ingestion_run_id}/calculate-territorial-metrics", response_model=ApiResponse)
def calculate_territorial_metrics(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = MetricsService(db).calculate_territorial_metrics(ingestion_run_id)
        return ApiResponse(success=True, status="TERRITORIAL_METRICS_CALCULATED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="TERRITORIAL_METRICS_FAILED", message=str(exc))],
        )


@router.get("/{ingestion_run_id}/station-metrics", response_model=ApiResponse)
def station_metrics(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = MetricsService(db).get_station_metrics(ingestion_run_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="STATION_METRICS_QUERY_FAILED", message=str(exc))],
        )


@router.get("/{ingestion_run_id}/municipality-metrics", response_model=ApiResponse)
def municipality_metrics(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = MetricsService(db).get_municipality_metrics(ingestion_run_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="MUNICIPALITY_METRICS_QUERY_FAILED", message=str(exc))],
        )


@router.post("/{ingestion_run_id}/calculate-scores", response_model=ApiResponse)
def calculate_scores(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = ScoringService(db).calculate_scores(ingestion_run_id)
        return ApiResponse(success=True, status="SCORED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="SCORING_FAILED", message=str(exc))],
        )


@router.get("/{ingestion_run_id}/review-cases", response_model=ApiResponse)
def review_cases_for_ingestion(
    ingestion_run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = ScoringService(db).get_review_cases(ingestion_run_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="REVIEW_CASES_QUERY_FAILED", message=str(exc))],
        )
