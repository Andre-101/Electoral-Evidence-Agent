import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiError, ApiResponse
from app.services.scoring_service import ScoringService
from app.services.evidence_service import EvidenceService
from app.services.agent_service import AgentService

router = APIRouter(prefix="/review-cases", tags=["review-cases"])


@router.get("/{review_case_id}", response_model=ApiResponse)
def get_review_case(
    review_case_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = ScoringService(db).get_review_case_detail(review_case_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="REVIEW_CASE_NOT_FOUND", message=str(exc))],
        )


@router.post("/{review_case_id}/evidence-items/generate", response_model=ApiResponse)
def generate_evidence_items(
    review_case_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = EvidenceService(db).generate_evidence_items(review_case_id)
        return ApiResponse(success=True, status="EVIDENCE_CREATED", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="EVIDENCE_GENERATION_FAILED", message=str(exc))],
        )


@router.get("/{review_case_id}/evidence-items", response_model=ApiResponse)
def get_evidence_items(
    review_case_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = EvidenceService(db).get_evidence_items(review_case_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="EVIDENCE_ITEMS_QUERY_FAILED", message=str(exc))],
        )


@router.get("/{review_case_id}/agent-context", response_model=ApiResponse)
def get_agent_context(
    review_case_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = EvidenceService(db).build_agent_context(review_case_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="AGENT_CONTEXT_FAILED", message=str(exc))],
        )


@router.post("/{review_case_id}/dossier", response_model=ApiResponse)
def generate_dossier(
    review_case_id: uuid.UUID,
    force_regenerate: bool = False,
    include_technical_summary: bool = True,
    include_traceability: bool = True,
    use_llm: bool | None = None,
    model: str | None = None,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = AgentService(db).generate_dossier(
            review_case_id=review_case_id,
            force_regenerate=force_regenerate,
            include_technical_summary=include_technical_summary,
            include_traceability=include_traceability,
            use_llm=use_llm,
            model=model,
        )
        return ApiResponse(success=True, status=data["dossier_status"], data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="DOSSIER_GENERATION_FAILED", message=str(exc))],
        )


@router.get("/{review_case_id}/dossier", response_model=ApiResponse)
def get_dossier(
    review_case_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ApiResponse:
    try:
        data = AgentService(db).get_dossier(review_case_id)
        return ApiResponse(success=True, status="OK", data=data)
    except Exception as exc:
        return ApiResponse(
            success=False,
            status="FAILED",
            errors=[ApiError(code="DOSSIER_QUERY_FAILED", message=str(exc))],
        )
