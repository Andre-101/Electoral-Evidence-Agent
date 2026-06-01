from fastapi import APIRouter

from app.core.settings import get_settings
from app.schemas.common import ApiResponse
from app.services.llm_service import ClaudeLlmService

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/status", response_model=ApiResponse)
def llm_status() -> ApiResponse:
    settings = get_settings()
    service = ClaudeLlmService()
    return ApiResponse(
        success=True,
        status="OK",
        data={
            "provider": "anthropic",
            "available": service.is_available(),
            "mode": settings.llm_enabled,
            "default_model": settings.anthropic_model,
            "api_key_configured": bool(settings.anthropic_api_key.strip()),
            "required": False,
        },
    )
