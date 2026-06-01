from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.ingestions import router as ingestions_router
from app.api.review_cases import router as review_cases_router
from app.api.reports import router as reports_router
from app.api.demo import router as demo_router
from app.api.llm import router as llm_router
api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(ingestions_router)
api_router.include_router(review_cases_router)
api_router.include_router(reports_router)
api_router.include_router(demo_router)
api_router.include_router(llm_router)
