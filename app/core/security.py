import jwt
import datetime
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings

security_scheme = HTTPBearer(auto_error=False)


def create_token(data: dict) -> str:
    """
    Tạo JWT token từ payload data.
    Token không có thời hạn (không bao giờ hết hạn).

    Args:
        data: Dữ liệu cần encode vào token.

    Returns:
        JWT token string.
    """
    payload = data.copy()
    # Không thêm "exp" claim → token không bao giờ hết hạn
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Security(security_scheme),
) -> dict:
    """
    Dependency xác thực JWT Bearer token.
    Decode token bằng SECRET_KEY, trả về payload nếu hợp lệ.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authentication token.")

    token = credentials.credentials

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")


async def verify_admin_token(
    credentials: HTTPAuthorizationCredentials | None = Security(security_scheme),
) -> str:
    """
    Dependency xác thực Admin token (so sánh trực tiếp với ADMIN_TOKEN trong env).
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authentication token.")

    token = credentials.credentials
    if token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token.")

    return token
