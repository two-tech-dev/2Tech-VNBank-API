import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import verify_token, verify_admin_token, create_token
from app.core.database import seabank_accounts_collection
from app.services.seabank_service import SeABankService
from app.utils.crypto import encrypt_aes256, decrypt_aes256
from app.models.seabank_account import (
    SeABankAccountCreate,
    SeABankAccountResponse,
    SeABankInfoResponse,
    SeABankTransactionsResponse,
    SeABankTransactionItem,
)

router = APIRouter()


# ─────────────────────────────────────────────────
# POST /api/v1/bank/seabank/add
# ─────────────────────────────────────────────────
@router.post("/add", response_model=SeABankAccountResponse)
async def add_seabank_account(
    body: SeABankAccountCreate,
    _admin: str = Depends(verify_admin_token),
):
    """
    Thêm tài khoản SeABank (yêu cầu Admin token).
    - Login SeABank để xác minh thông tin hợp lệ.
    - Lưu thông tin vào MongoDB.
    - Trả về JWT token cho tài khoản.
    """
    collection = seabank_accounts_collection()

    # Kiểm tra tài khoản đã tồn tại chưa
    existing = await collection.find_one({"accountNo": body.accountNo})
    if existing:
        raise HTTPException(status_code=409, detail="Tài khoản này đã được thêm trước đó.")

    # Login SeABank để xác minh
    try:
        service = SeABankService(username=body.username, password=body.password)
        login_data = service.login()
        account_info = service.get_account_info()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Đăng nhập SeABank thất bại: {e}")
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Lỗi kết nối SeABank: {e}")

    # Lưu vào MongoDB (dùng accountNo do user nhập)
    doc = {
        "username": body.username,
        "password": encrypt_aes256(body.password),
        "accountNo": body.accountNo,
        "accountName": account_info.account_name,
        "customerId": login_data.get("customerId", ""),
        "mainAccount": login_data.get("mainAccount", ""),
        "bankCode": "seabank",
        "createdAt": datetime.datetime.now(datetime.timezone.utc),
    }
    result = await collection.insert_one(doc)

    # Tạo JWT token
    token = create_token({
        "account_id": str(result.inserted_id),
        "accountNo": body.accountNo,
        "bankCode": "seabank",
    })

    return SeABankAccountResponse(
        message="Thêm tài khoản SeABank thành công.",
        token=token,
        account_name=account_info.account_name,
        account_number=body.accountNo,
        balance=account_info.balance,
    )


# ─────────────────────────────────────────────────
# GET /api/v1/bank/seabank/info
# ─────────────────────────────────────────────────
@router.get("/info", response_model=SeABankInfoResponse)
async def get_seabank_info(
    payload: dict = Depends(verify_token),
):
    """
    Lấy thông tin tài khoản SeABank (yêu cầu JWT token).
    """
    account_no = payload.get("accountNo")
    if not account_no:
        raise HTTPException(status_code=400, detail="Token không chứa thông tin tài khoản.")

    collection = seabank_accounts_collection()
    doc = await collection.find_one({"accountNo": account_no})
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản trong hệ thống.")

    try:
        password_plain = decrypt_aes256(doc["password"])
        service = SeABankService(username=doc["username"], password=password_plain)
        service.login()
        account_info = service.get_account_info()
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=502, detail=f"Lỗi khi truy vấn SeABank: {e}")

    return SeABankInfoResponse(
        account_name=account_info.account_name,
        account_number=account_info.account_number,
        balance=account_info.balance,
        currency=account_info.currency,
        customer_id=account_info.customer_id,
        product_name=account_info.product_name,
    )


# ─────────────────────────────────────────────────
# GET /api/v1/bank/seabank/transactions
# ─────────────────────────────────────────────────
@router.get("/transactions", response_model=SeABankTransactionsResponse)
async def get_seabank_transactions(
    from_date: str = Query(..., description="Ngày bắt đầu (YYYY-MM-DD)", examples=["2026-04-01"]),
    to_date: str = Query(..., description="Ngày kết thúc (YYYY-MM-DD)", examples=["2026-04-06"]),
    payload: dict = Depends(verify_token),
):
    """
    Lấy lịch sử giao dịch SeABank (yêu cầu JWT token).
    """
    account_no = payload.get("accountNo")
    if not account_no:
        raise HTTPException(status_code=400, detail="Token không chứa thông tin tài khoản.")

    # Parse date
    try:
        dt_from = datetime.datetime.strptime(from_date, "%Y-%m-%d")
        dt_to = datetime.datetime.strptime(to_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Định dạng ngày không hợp lệ. Sử dụng YYYY-MM-DD.")

    collection = seabank_accounts_collection()
    doc = await collection.find_one({"accountNo": account_no})
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản trong hệ thống.")

    try:
        password_plain = decrypt_aes256(doc["password"])
        service = SeABankService(username=doc["username"], password=password_plain)
        service.login()
        history = service.get_transaction_history(
            account_id=doc["accountNo"],
            from_date=dt_from,
            to_date=dt_to,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=502, detail=f"Lỗi khi truy vấn SeABank: {e}")

    transactions = [
        SeABankTransactionItem(
            transaction_id=tx.transaction_id,
            transaction_date=tx.transaction_date,
            credit_amount=tx.credit_amount,
            debit_amount=tx.debit_amount,
            description=tx.description,
            sender_name=tx.sender_name,
            sender_bank=tx.sender_bank,
            receiver_name=tx.receiver_name,
            receiver_bank=tx.receiver_bank,
        )
        for tx in history.transactions
    ]

    return SeABankTransactionsResponse(
        account_number=history.account_number,
        from_date=history.from_date,
        to_date=history.to_date,
        total=len(transactions),
        transactions=transactions,
    )


# ─────────────────────────────────────────────────
# DELETE /api/v1/bank/seabank/delete
# ─────────────────────────────────────────────────
@router.delete("/delete")
async def delete_seabank_account(
    payload: dict = Depends(verify_token),
):
    """
    Xóa tài khoản SeABank khỏi hệ thống (yêu cầu JWT token).
    """
    account_no = payload.get("accountNo")
    if not account_no:
        raise HTTPException(status_code=400, detail="Token không chứa thông tin tài khoản.")

    collection = seabank_accounts_collection()
    result = await collection.delete_one({"accountNo": account_no})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản để xóa.")

    return {"message": f"Đã xóa tài khoản SeABank {account_no} khỏi hệ thống."}
