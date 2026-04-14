"""
Test file cho SeABank API endpoints.
Chạy: uv run python tests/test_seabank_api.py

Lưu ý: Cần thay YOUR_USERNAME, YOUR_PASSWORD bằng thông tin thực trước khi chạy.
"""

import requests
import json
import os

BASE_URL = "http://localhost:8000/api/v1/bank/seabank"
ADMIN_TOKEN = "2tech-admin-secret-token"
TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".seabank_token.json")

# ── Thông tin test ───────────────────────────────
TEST_USERNAME = "HARRYITZ"
TEST_PASSWORD = "Hieu33541!!"
TEST_ACCOUNT_NO = "000007741412"  # Số tài khoản 12 số, VD: 000007741412


def save_token(token: str, account_no: str):
    """Lưu JWT token vào file để tái sử dụng."""
    with open(TOKEN_FILE, "w") as f:
        json.dump({"token": token, "accountNo": account_no}, f)
    print(f"   💾 Token đã lưu vào {TOKEN_FILE}")


def load_token() -> str | None:
    """Đọc JWT token từ file."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
            return data.get("token")
    return None


# Biến lưu JWT token
jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2NvdW50X2lkIjoiNjlkMmU1N2IzYjgzOWRhNjI4NDRjMTEwIiwiYWNjb3VudE5vIjoiMDAwMDA3NzQxNDEyIiwiYmFua0NvZGUiOiJzZWFiYW5rIiwiZXhwIjoxNzc1NTE1Mzg3fQ.bR85u8HMxYUwBV87xnDC0Gf6H1H-1b604x0OY9KtCRY"


def test_add_account():
    """POST /api/v1/bank/seabank/add - Thêm tài khoản (Admin auth)."""
    global jwt_token

    print("=" * 60)
    print("TEST: POST /add - Thêm tài khoản SeABank")
    print("=" * 60)

    response = requests.post(
        f"{BASE_URL}/add",
        json={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "accountNo": TEST_ACCOUNT_NO,
        },
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")

    if response.status_code == 200:
        jwt_token = data.get("token")
        save_token(jwt_token, data.get("account_number", ""))
        print(f"\n✅ Thành công!")
        print(f"   Tên TK : {data['account_name']}")
        print(f"   Số TK  : {data['account_number']}")
        print(f"   Số dư  : {data['balance']:,.0f}")
    else:
        print(f"\n❌ Thất bại: {data}")

    return response.status_code == 200


def test_add_no_admin():
    """POST /add - Không có admin token (expect 403)."""
    print("\n" + "=" * 60)
    print("TEST: POST /add - Không có admin token (expect 403)")
    print("=" * 60)

    response = requests.post(
        f"{BASE_URL}/add",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        headers={"Authorization": "Bearer wrong-token"},
    )

    print(f"Status: {response.status_code}")
    if response.status_code in (401, 403):
        print("✅ Đúng - Từ chối truy cập!")
    else:
        print(f"❌ Lỗi - Expected 401/403, got {response.status_code}")


def test_get_info():
    """GET /api/v1/bank/seabank/info - Lấy thông tin tài khoản."""
    print("\n" + "=" * 60)
    print("TEST: GET /info - Thông tin tài khoản SeABank")
    print("=" * 60)

    if not jwt_token:
        print("⚠️  Bỏ qua - Không có JWT token")
        return

    response = requests.get(
        f"{BASE_URL}/info",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )

    print(f"Status: {response.status_code}")
    data = response.json()

    if response.status_code == 200:
        print(f"\n✅ Thông tin tài khoản:")
        print(f"   Tên TK    : {data['account_name']}")
        print(f"   Số TK     : {data['account_number']}")
        print(f"   Số dư     : {data['balance']:,.0f} {data['currency']}")
        print(f"   Mã KH     : {data['customer_id']}")
        print(f"   Loại TK   : {data['product_name']}")
    else:
        print(f"❌ Thất bại: {data}")


def test_get_info_no_token():
    """GET /info - Không có token (expect 401)."""
    print("\n" + "=" * 60)
    print("TEST: GET /info - Không có token (expect 401)")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/info")
    print(f"Status: {response.status_code}")
    if response.status_code == 401:
        print("✅ Đúng - Yêu cầu xác thực!")
    else:
        print(f"❌ Expected 401, got {response.status_code}")


def test_get_transactions():
    """GET /api/v1/bank/seabank/transactions - Lịch sử giao dịch."""
    print("\n" + "=" * 60)
    print("TEST: GET /transactions - Lịch sử giao dịch SeABank")
    print("=" * 60)

    if not jwt_token:
        print("⚠️  Bỏ qua - Không có JWT token")
        return

    response = requests.get(
        f"{BASE_URL}/transactions",
        params={"from_date": "2026-04-01", "to_date": "2026-04-06"},
        headers={"Authorization": f"Bearer {jwt_token}"},
    )

    print(f"Status: {response.status_code}")
    data = response.json()

    if response.status_code == 200:
        print(f"\n✅ Lịch sử giao dịch:")
        print(f"   Tài khoản  : {data['account_number']}")
        print(f"   Từ ngày    : {data['from_date']} → {data['to_date']}")
        print(f"   Tổng GD    : {data['total']}")

        if data["transactions"]:
            print(f"\n   {'Ngày':<15} | {'Có (+)':<15} | {'Nợ (-)':<15} | {'Mô tả'}")
            print("   " + "-" * 75)
            for tx in data["transactions"][:10]:
                credit = f"+{tx['credit_amount']:,.0f}" if tx["credit_amount"] else ""
                debit = f"-{tx['debit_amount']:,.0f}" if tx["debit_amount"] else ""
                desc = tx["description"][:40]
                print(f"   {tx['transaction_date']:<15} | {credit:<15} | {debit:<15} | {desc}")
            if data["total"] > 10:
                print(f"   ... và {data['total'] - 10} giao dịch nữa")
    else:
        print(f"❌ Thất bại: {data}")


def test_delete_account():
    """DELETE /api/v1/bank/seabank/delete - Xóa tài khoản."""
    print("\n" + "=" * 60)
    print("TEST: DELETE /delete - Xóa tài khoản SeABank")
    print("=" * 60)

    if not jwt_token:
        print("⚠️  Bỏ qua - Không có JWT token")
        return

    response = requests.delete(
        f"{BASE_URL}/delete",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")

    if response.status_code == 200:
        print("\n✅ Đã xóa thành công!")
        # Xóa file token
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
    else:
        print(f"❌ Thất bại: {data}")


def test_delete_again():
    """DELETE /delete - Xóa lần 2 (expect 404)."""
    print("\n" + "=" * 60)
    print("TEST: DELETE /delete - Xóa lần 2 (expect 404)")
    print("=" * 60)

    if not jwt_token:
        print("⚠️  Bỏ qua")
        return

    response = requests.delete(
        f"{BASE_URL}/delete",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 404:
        print("✅ Đúng - Tài khoản đã bị xóa!")
    else:
        print(f"❌ Expected 404, got {response.status_code}")


if __name__ == "__main__":
    print("\n🏦 BẮT ĐẦU TEST SEABANK API\n")

    if jwt_token:
        print(f"📂 Đã load token từ file: {jwt_token[:50]}...\n")

    # 1. Thêm tài khoản (Admin auth)
    test_add_account()

    # 2. Thử thêm không có admin token
    test_add_no_admin()

    # 3. Lấy thông tin tài khoản
    test_get_info()

    # 4. Không có token
    test_get_info_no_token()

    # 5. Lịch sử giao dịch
    test_get_transactions()

    # 6. Xóa tài khoản
    # test_delete_account()

    # 7. Xóa lần 2
    # test_delete_again()

    print("\n" + "=" * 60)
    print("🏁 HOÀN THÀNH TEST SEABANK!")
    print("=" * 60)
