from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator


class Settings(BaseSettings):
    PROJECT_NAME: str = "2Tech Gateway API"
    API_V1_STR: str = "api/v1"
    ENVIRONMENT: str = "development"

    # Danh sách các domain được phép truy cập (CORS)
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = []

    # JWT Authentication
    SECRET_KEY: str = "3f1c21b53488fbdf7d4134f0b992c9fd82b8e30ac392e58c2a6c63a1d9f7651e"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # Admin token - dùng để xác thực các thao tác admin
    ADMIN_TOKEN: str = "2tech-admin-secret-token"

    # MongoDB
    MONGODB_URI: str = "mongodb://JasperMC:harrypasswordX@103.77.173.158:27017/h-tech-payments?authSource=admin"
    MONGODB_DB_NAME: str = "h-tech-payments"

    # Cấu hình URL các backend services
    USER_SERVICE_URL: str = "http://localhost:8001"
    PAYMENT_SERVICE_URL: str = "http://localhost:8002"
    PRODUCT_SERVICE_URL: str = "http://localhost:8003"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = {"case_sensitive": True, "env_file": ".env"}


settings = Settings()
