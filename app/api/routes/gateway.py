from fastapi import APIRouter, Request
from app.core.proxy import forward_request
from app.core.config import settings

router = APIRouter()

# Mapping prefix path -> backend service URL
SERVICE_ROUTES: dict[str, str] = {
    "users": settings.USER_SERVICE_URL,
    "payments": settings.PAYMENT_SERVICE_URL,
    "products": settings.PRODUCT_SERVICE_URL,
}


def _resolve_target(path: str) -> str:
    """Phân giải path prefix để tìm backend service URL tương ứng."""
    prefix = path.split("/")[0] if "/" in path else path
    base_url = SERVICE_ROUTES.get(prefix)
    if base_url:
        return f"{base_url}/{path}"
    # Fallback: forward tới service mặc định
    return f"{settings.USER_SERVICE_URL}/{path}"


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    tags=["Gateway"],
)
async def gateway_route(request: Request, path: str):
    """
    Catch-all route: Chuyển tiếp tất cả request đến backend service phù hợp
    dựa trên prefix của path.

    Ví dụ:
    - /api/v1/users/123  -> USER_SERVICE_URL/users/123
    - /api/v1/products   -> PRODUCT_SERVICE_URL/products
    """
    target_url = _resolve_target(path)
    return await forward_request(request, target_url)
