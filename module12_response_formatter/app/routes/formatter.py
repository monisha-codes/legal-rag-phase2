from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.cache import CacheWriter
from app.config import settings
from app.formatter import ResponseFormatterError, ResponseFormatterService
from app.models import FormatAPIResponse, FormatRequest

router = APIRouter(prefix="/formatter", tags=["Response Formatter"])

formatter_service = ResponseFormatterService()
cache_writer = CacheWriter()


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@router.post("/format", response_model=FormatAPIResponse)
def format_response(payload: FormatRequest) -> FormatAPIResponse:
    try:
        formatted_response, cache_payload = formatter_service.format(payload)

        cache_write_status = "cache_disabled"
        if settings.enable_cache_write:
            cache_write_status = cache_writer.write(cache_payload)

        return FormatAPIResponse(
            formatted_response=formatted_response,
            cache_payload=cache_payload,
            cache_write_status=cache_write_status,
        )

    except ResponseFormatterError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected formatter error",
        ) from exc