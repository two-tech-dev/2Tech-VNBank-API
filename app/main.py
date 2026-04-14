from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import gateway, bank, mbbank, seabank, tpbank
from app.core.config import settings


app_kwargs = {
    "title": settings.PROJECT_NAME,
    "version": "1.0.0",
    "description": "2Tech Gateway API - Điểm vào trung tâm cho hệ thống microservices",
}

if settings.ENVIRONMENT == "production":
    app_kwargs["openapi_url"] = None
    app_kwargs["docs_url"] = None
    app_kwargs["redoc_url"] = None
else:
    app_kwargs["openapi_url"] = f"/{settings.API_V1_STR}/openapi.json"

app = FastAPI(**app_kwargs)

# CORS configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# MB Bank routes (đăng ký TRƯỚC gateway catch-all)
app.include_router(mbbank.router, prefix=f"/{settings.API_V1_STR}/bank/mbbank", tags=["MB Bank"])

# SeABank routes
app.include_router(seabank.router, prefix=f"/{settings.API_V1_STR}/bank/seabank", tags=["SeABank"])

# TPBank routes
app.include_router(tpbank.router, prefix=f"/{settings.API_V1_STR}/bank/tpbank", tags=["TPBank"])

# Bank routes
app.include_router(bank.router, prefix=f"/{settings.API_V1_STR}/bank", tags=["Bank"])

# Gateway catch-all routes (PHẢI ở cuối cùng vì /{path:path} bắt tất cả)
app.include_router(gateway.router, prefix=f"/{settings.API_V1_STR}")


@app.get("/health", tags=["Health"])
async def health_check():
    """Endpoint kiểm tra Gateway có hoạt động hay không."""
    return {"status": "ok", "service": settings.PROJECT_NAME}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
