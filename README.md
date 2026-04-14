# 🚀 2Tech Gateway API

API Gateway trung tâm cho hệ thống microservices **2Tech**, được xây dựng bằng **FastAPI** + **httpx**.

## Cấu trúc thư mục

```
2tech-gateway-api/
├── app/
│   ├── main.py              # Entry point - Khởi tạo FastAPI app
│   ├── api/
│   │   ├── dependencies.py  # Shared dependencies (auth, rate limit)
│   │   └── routes/
│   │       └── gateway.py   # Catch-all route forward requests
│   ├── core/
│   │   ├── config.py        # Quản lý biến môi trường (Pydantic Settings)
│   │   ├── security.py      # Xác thực JWT Bearer Token
│   │   ├── exceptions.py    # Custom exceptions + Global handler
│   │   └── proxy.py         # Logic forward request qua httpx
│   ├── models/              # Pydantic schemas (Request/Response)
│   ├── services/            # Business logic
│   └── utils/
│       └── logger.py        # Cấu hình logging
└── tests/
    └── test_main.py         # Unit tests
```

## Cài đặt & Chạy

### Yêu cầu
- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) (package manager)

### 1. Cài đặt dependencies
```bash
uv sync
```

### 2. Cấu hình môi trường
```bash
cp .env.example .env
# Chỉnh sửa .env với các giá trị thực tế
```

### 3. Chạy server (development)
```bash
uv run uvicorn app.main:app --reload --port 8000
```

### 4. Truy cập tài liệu API
- Swagger UI: [http://localhost:8000/api/v1/openapi.json](http://localhost:8000/docs)
- Redoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

## Service Routing

Gateway tự động phân phối request dựa trên URL prefix:

| Path prefix   | Backend Service      | Default URL             |
| ------------- | -------------------- | ----------------------- |
| `/users/...`  | User Service         | `http://localhost:8001`  |
| `/payments/...` | Payment Service   | `http://localhost:8002`  |
| `/products/...` | Product Service   | `http://localhost:8003`  |

## Chạy Tests
```bash
uv run pytest
```
