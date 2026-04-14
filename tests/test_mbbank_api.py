"""
Test file cho MB Bank API endpoints.
Chạy: uv run python tests/test_mbbank_api.py

Lưu ý: Cần thay YOUR_USERNAME, YOUR_PASSWORD, YOUR_ACCOUNT_NO
        bằng thông tin thực trước khi chạy.
"""

import requests
import json
import os

BASE_URL = "http://localhost:8000/api/v1/bank/mbbank"
ADMIN_TOKEN = "2tech-admin-secret-token"
TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".mbbank_token.json")

# ── Thông tin test ───────────────────────────────
TEST_USERNAME = "0347970961"
TEST_PASSWORD = "Hieu33541!!"
TEST_ACCOUNT_NO = "0347970961"


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


# Biến lưu JWT token - tự động load từ file nếu có
jwt_token = load_token()


def test_add_account():
    """POST /api/v1/bank/mbbank/add - Thêm tài khoản (Admin auth)."""
    global jwt_token

    print("=" * 60)
    print("TEST: POST /add - Thêm tài khoản MB Bank")
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
    print(f"Response: {data}")

    if response.status_code == 200:
        jwt_token = data.get("token")
        save_token(jwt_token, TEST_ACCOUNT_NO)
        print(f"\n✅ Thành công! JWT Token: {jwt_token[:50]}...")
    else:
        print(f"\n❌ Thất bại: {data}")

    return response.status_code == 200


def test_add_account_no_admin():
    """POST /add - Thử thêm tài khoản KHÔNG có admin token."""
    print("\n" + "=" * 60)
    print("TEST: POST /add - Không có admin token (expect 401/403)")
    print("=" * 60)

    response = requests.post(
        f"{BASE_URL}/add",
        json={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "accountNo": TEST_ACCOUNT_NO,
        },
        headers={"Authorization": "Bearer wrong-token"},
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code in (401, 403):
        print("\n✅ Đúng - Từ chối truy cập!")
    else:
        print("\n❌ Lỗi - Phải trả về 401 hoặc 403")


def test_get_info():
    """GET /api/v1/bank/mbbank/info - Lấy thông tin tài khoản (JWT auth)."""
    print("\n" + "=" * 60)
    print("TEST: GET /info - Lấy thông tin tài khoản")
    print("=" * 60)

    if not jwt_token:
        print("⚠️  Bỏ qua - Không có JWT token (test add thất bại)")
        return

    response = requests.get(
        f"{BASE_URL}/info",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")

    if response.status_code == 200:
        print(f"\n✅ Tên TK: {data['account_name']}")
        print(f"   Số TK : {data['account_number']}")
        print(f"   Số dư : {data['balance']:,.0f}")
    else:
        print(f"\n❌ Thất bại: {data}")


def test_get_info_no_token():
    """GET /info - Không có token (expect 401)."""
    print("\n" + "=" * 60)
    print("TEST: GET /info - Không có token (expect 401)")
    print("=" * 60)

    response = requests.get(f"{BASE_URL}/info")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 401:
        print("\n✅ Đúng - Yêu cầu xác thực!")
    else:
        print("\n❌ Lỗi - Phải trả về 401")


def test_get_transactions():
    """GET /api/v1/bank/mbbank/transactions - Lịch sử giao dịch (JWT auth)."""
    print("\n" + "=" * 60)
    print("TEST: GET /transactions - Lịch sử giao dịch")
    print("=" * 60)

    if not jwt_token:
        print("⚠️  Bỏ qua - Không có JWT token (test add thất bại)")
        return

    response = requests.get(
        f"{BASE_URL}/transactions",
        params={"from_date": "2025-03-01", "to_date": "2025-03-31"},
        headers={"Authorization": f"Bearer {jwt_token}"},
    )

    print(f"Status: {response.status_code}")
    data = response.json()

    if response.status_code == 200:
        print(f"\n✅ Tài khoản: {data['account_number']}")
        print(f"   Khoảng thời gian: {data['from_date']} → {data['to_date']}")
        print(f"   Tổng giao dịch: {data['total']}")
        if data["transactions"]:
            print(f"\n   {'Ngày':<20} | {'Có (+)':<15} | {'Nợ (-)':<15} | {'Mô tả'}")
            print("   " + "-" * 70)
            for tx in data["transactions"][:5]:
                credit = f"+{tx['credit_amount']:,.0f}" if tx["credit_amount"] else ""
                debit = f"-{tx['debit_amount']:,.0f}" if tx["debit_amount"] else ""
                desc = tx["description"][:40]
                print(f"   {tx['transaction_date']:<20} | {credit:<15} | {debit:<15} | {desc}")
            if data["total"] > 5:
                print(f"   ... và {data['total'] - 5} giao dịch nữa")
    else:
        print(f"\n❌ Thất bại: {data}")


def test_delete_account():
    """DELETE /api/v1/bank/mbbank/delete - Xóa tài khoản (JWT auth)."""
    print("\n" + "=" * 60)
    print("TEST: DELETE /delete - Xóa tài khoản")
    print("=" * 60)

    if not jwt_token:
        print("⚠️  Bỏ qua - Không có JWT token (test add thất bại)")
        return

    response = requests.delete(
        f"{BASE_URL}/delete",
        headers={"Authorization": f"Bearer {jwt_token}"},
    )

    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {data}")

    if response.status_code == 200:
        print(f"\n✅ Đã xóa thành công!")
    else:
        print(f"\n❌ Thất bại: {data}")


def test_delete_account_again():
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
    print(f"Response: {response.json()}")

    if response.status_code == 404:
        print("\n✅ Đúng - Tài khoản đã bị xóa!")
    else:
        print("\n❌ Lỗi - Phải trả về 404")


if __name__ == "__main__":
    print("\n🚀 BẮT ĐẦU TEST MB BANK API\n")

    # 1. Thêm tài khoản (Admin auth)
    success = test_add_account()

    # 2. Thử thêm tài khoản không có admin token
    test_add_account_no_admin()

    # 3. Lấy thông tin tài khoản (JWT auth)
    test_get_info()

    # 4. Lấy thông tin không có token
    test_get_info_no_token()

    # 5. Lấy lịch sử giao dịch (JWT auth)
    test_get_transactions()

    # 6. Xóa tài khoản (JWT auth)
    test_delete_account()

    # 7. Xóa lần 2 (expect 404)
    test_delete_account_again()

    print("\n" + "=" * 60)
    print("🏁 HOÀN THÀNH TEST!")
    print("=" * 60)
