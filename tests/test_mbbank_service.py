"""
Test file cho MBBankService.
Chạy: uv run python tests/test_mbbank_service.py
"""

from app.services.mbbank_service import MBBankService


def test_login():
    """Test login và lấy thông tin tài khoản."""
    username = "0347970961"
    password = "Hieu33541!!"
    account_number = "0347970961"

    service = MBBankService(username=username, password=password)

    try:
        account = service.login(account_number=account_number)
        print("=" * 60)
        print("LOGIN THÀNH CÔNG")
        print("=" * 60)
        print(f"  Tên tài khoản : {account.account_name}")
        print(f"  Số tài khoản  : {account.account_number}")
        print(f"  Số dư         : {account.balance:,.0f} {account.currency}")
        print("=" * 60)
    except ValueError as e:
        print(f"Lỗi dữ liệu: {e}")
    except RuntimeError as e:
        print(f"Lỗi kết nối: {e}")


def test_transaction_history():
    """Test lấy lịch sử giao dịch 30 ngày gần nhất."""
    username = "0347970961"
    password = "Hieu33541!!"
    account_number = "0347970961"

    service = MBBankService(username=username, password=password)

    try:
        history = service.getTransactionAccountHistory(account_number=account_number)
        print("=" * 80)
        print(f"LỊCH SỬ GIAO DỊCH: {history.from_date} → {history.to_date}")
        print(f"Tài khoản: {history.account_number}")
        print(f"Tổng số giao dịch: {len(history.transactions)}")
        print("=" * 80)

        if not history.transactions:
            print("Không có giao dịch nào trong khoảng thời gian này.")
            return

        print(f"{'Ngày':<20} | {'Có (+)':<15} | {'Nợ (-)':<15} | {'Mô tả'}")
        print("-" * 80)
        for tx in history.transactions:
            credit = f"+{tx.credit_amount:,.0f}" if tx.credit_amount else ""
            debit = f"-{tx.debit_amount:,.0f}" if tx.debit_amount else ""
            print(f"{tx.transaction_date:<20} | {credit:<15} | {debit:<15} | {tx.description}")

        print("-" * 80)
    except RuntimeError as e:
        print(f"Lỗi: {e}")


if __name__ == "__main__":
    print("\n>>> TEST 1: Login\n")
    test_login()

    print("\n>>> TEST 2: Transaction History\n")
    test_transaction_history()
