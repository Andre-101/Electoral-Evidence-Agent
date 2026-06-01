from fastapi import FastAPI

from app.api.routes import api_router
from app.core.settings import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.pipeline_version,
    debug=settings.app_debug,
)

app.include_router(api_router)
