# Hướng dẫn Cài đặt & API Documentation

## 1. Danh sách các API Endpoint

Dưới đây là các API paths được định nghĩa trong dự án (Prefix mặc định: `/api/v1`):

### Health Check
- `GET /health` : Kiểm tra trạng thái hoạt động của Gateway.

### MB Bank
- `POST /api/v1/bank/mbbank/add` : Thêm tài khoản MB Bank
- `GET /api/v1/bank/mbbank/info` : Lấy thông tin tài khoản MB Bank
- `GET /api/v1/bank/mbbank/transactions` : Lấy danh sách giao dịch MB Bank
- `DELETE /api/v1/bank/mbbank/delete` : Xóa tài khoản MB Bank

### SeABank
- `POST /api/v1/bank/seabank/add` : Thêm tài khoản SeABank
- `GET /api/v1/bank/seabank/info` : Lấy thông tin tài khoản SeABank
- `GET /api/v1/bank/seabank/transactions` : Lấy danh sách giao dịch SeABank
- `DELETE /api/v1/bank/seabank/delete` : Xóa tài khoản SeABank

### TPBank
- `POST /api/v1/bank/tpbank/add` : Thêm tài khoản TPBank
- `POST /api/v1/bank/tpbank/confirm` : Xác nhận giao dịch TPBank
- `GET /api/v1/bank/tpbank/info` : Lấy thông tin tài khoản TPBank
- `GET /api/v1/bank/tpbank/transactions` : Lấy danh sách giao dịch TPBank
- `DELETE /api/v1/bank/tpbank/delete` : Xóa tài khoản TPBank

### Bank (General Routes)
- `GET /api/v1/bank/` : Lấy danh sách thông tin chung của các ngân hàng.
- `GET /api/v1/bank/{bank_code}` : Lấy thông tin ngân hàng cụ thể theo mã (bank_code).
- `POST /api/v1/bank/transfer` : Thực hiện tạo giao dịch chuyển khoản.
- `GET /api/v1/bank/account/{account_number}` : Lấy thông tin theo số tài khoản ngân hàng cụ thể.

### Gateway Proxy (Catch-all)
- `ANY /api/v1/{path:path}` : Tất cả các route khác (ví dụ: `/api/v1/users/...`, `/api/v1/payments/...`, `/api/v1/products/...`) đều sẽ tự động được gateway proxy chuyển tiếp tới các service tương ứng đã khai báo url trong `.env`.

---

## 2. Hướng dẫn Deploy lên Ubuntu VPS

Dưới đây là các bước quy chuẩn để triển khai ứng dụng Gateway lên Ubuntu VPS với quy trình tối ưu cho production.

### Bước 1: Cập nhật hệ thống và cài đặt phụ thuộc
Cập nhật gói Ubuntu và cài đặt các package cơ bản bao gồm nginx và git.
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git nginx curl -y
```

### Bước 2: Cài đặt công cụ `uv` (Khuyên dùng)
Dự án sử dụng file `uv.lock` cho việc quản lý các môi trường package được tối ưu nhanh hơn `pip` thông thường:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### Bước 3: Clone source code và dựng môi trường ảo (venv)
```bash
# Clone dự án từ github/gitlab
git clone <URL_REPO_CỦA_DỰ_ÁN> 2tech-gateway-api
cd 2tech-gateway-api

# Khởi tạo môi trường ảo và cài đặt thư viện bằng uv
uv venv
source .venv/bin/activate
uv sync

# Sao chép và cấu hình lại environment 
cp .env.example .env
```

Thiết lập nội dung `.env` bằng `nano` hoặc `vim` các biến môi trường thực tế (MongoDB URI, URL của các Microservices).
```bash
nano .env
```

### Bước 4: Cấu hình systemd service chạy nền nền tự động
Thay vì chạy tay, bạn cần sử dụng systemd để ứng dụng tự động chạy cũng như tự khởi động lại:
```bash
sudo nano /etc/systemd/system/2tech-gateway.service
```

Thêm nội dung sau (lưu ý đổi biến `User` cũng như `/path/to/2tech-gateway-api` cho đúng với path trên hệ thống VPS):
```ini
[Unit]
Description=2Tech Gateway API Daemon Service
After=network.target

[Service]
User=root # (Hãy thay bằng user thực tế đang chạy project)
Group=www-data
WorkingDirectory=/path/to/2tech-gateway-api
Environment="PATH=/path/to/2tech-gateway-api/.venv/bin"
# Lệnh chạy 4 Workers của uvicorn để cân bằng tải tốt hơn
ExecStart=/path/to/2tech-gateway-api/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4

[Install]
WantedBy=multi-user.target
```

Khởi động service vừa tạo:
```bash
sudo systemctl daemon-reload
sudo systemctl start 2tech-gateway
sudo systemctl enable 2tech-gateway
sudo systemctl status 2tech-gateway # Kiểm tra xem service đang active (running) chưa
```

### Bước 5: Cấu hình Nginx làm Reverse Proxy
Dùng Nginx để định tuyến traffic từ bên ngoài port 80/443 vào local port 8000.
```bash
sudo nano /etc/nginx/sites-available/2tech-gateway
```

Nội dung của file cấu hình Nginx (nhớ đổi `your_domain.com` sang IP hoặc Tên miền của VPS):
```nginx
server {
    listen 80;
    server_name your_domain.com; # Thay bằng Domain hoặc IP tĩnh của VPS

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Kiểm tra lỗi cú pháp và Enable file config Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/2tech-gateway /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Bước 6: (Khuyên dùng) Mở rộng cài đặt SSL (HTTPS) cho Tên miền
Để api kết nối bảo mật an toàn, hãy dùng Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your_domain.com
```

🎉 Xin chúc mừng, 2Tech Gateway API đã được deploy thành công và đang hoạt động!
