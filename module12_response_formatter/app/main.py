from fastapi import FastAPI

from app.config import settings
from app.routes.formatter import router as formatter_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FastAPI service for Legal RAG Module 12 - Response Formatter",
)

app.include_router(formatter_router)