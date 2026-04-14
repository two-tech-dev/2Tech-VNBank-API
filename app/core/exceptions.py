from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class GatewayException(Exception):
    """Base exception cho Gateway."""

    def __init__(self, status_code: int = 500, detail: str = "Internal Gateway Error"):
        self.status_code = status_code
        self.detail = detail


class ServiceUnavailableException(GatewayException):
    """Backend service không khả dụng."""

    def __init__(self, service_name: str = "unknown"):
        super().__init__(status_code=503, detail=f"Service '{service_name}' is currently unavailable.")


class RateLimitExceededException(GatewayException):
    """Vượt quá giới hạn request."""

    def __init__(self):
        super().__init__(status_code=429, detail="Too many requests. Please try again later.")


async def gateway_exception_handler(request: Request, exc: GatewayException) -> JSONResponse:
    """Global exception handler cho các lỗi phát sinh từ Gateway."""
    logger.error("Gateway error on %s %s: %s", request.method, request.url, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "path": str(request.url)},
    )
