"""
Các dependency dùng chung cho API routes.

Sử dụng FastAPI Depends() để inject vào route handlers.
"""

from fastapi import Depends
from app.core.security import verify_token


async def require_auth(token: str = Depends(verify_token)) -> str:
    """Dependency yêu cầu xác thực. Inject vào route cần bảo vệ."""
    return token
