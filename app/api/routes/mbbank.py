import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import verify_token, verify_admin_token, create_token
from app.core.database import mbbank_accounts_collection
from app.services.mbbank_service import MBBankService
from app.utils.crypto import encrypt_aes256, decrypt_aes256
from app.models.mbbank_account import (
    MBBankAccountCreate,
    MBBankAccountResponse,
    MBBankInfoResponse,
    MBBankTransactionsResponse,
    TransactionItem,
)

router = APIRouter()


# ─────────────────────────────────────────────────
# POST /api/v1/bank/mbbank/add
# ─────────────────────────────────────────────────
@router.post("/add", response_model=MBBankAccountResponse)
async def add_mbbank_account(
    body: MBBankAccountCreate,
    _admin: str = Depends(verify_admin_token),
):
    """
    Thêm tài khoản MB Bank (yêu cầu Admin token).
    - Login MB Bank để xác minh thông tin hợp lệ.
    - Lưu thông tin vào MongoDB.
    - Trả về JWT token cho tài khoản.
    """
    collection = mbbank_accounts_collection()

    # Kiểm tra tài khoản đã tồn tại chưa
    existing = await collection.find_one({"accountNo": body.accountNo})
    if existing:
        raise HTTPException(status_code=409, detail="Tài khoản này đã được thêm trước đó.")

    # Login MB Bank để xác minh
    try:
        service = MBBankService(username=body.username, password=body.password)
        account_info = service.login(account_number=body.accountNo)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=f"Đăng nhập MB Bank thất bại: {e}")

    # Lưu vào MongoDB
    doc = {
        "username": body.username,
        "password": encrypt_aes256(body.password),
        "accountNo": body.accountNo,
        "accountName": account_info.account_name,
        "createdAt": datetime.datetime.now(datetime.timezone.utc),
    }
    result = await collection.insert_one(doc)

    # Tạo JWT token chứa accountNo và MongoDB document id
    token = create_token({
        "account_id": str(result.inserted_id),
        "accountNo": body.accountNo,
    })

    return MBBankAccountResponse(
        message="Thêm tài khoản MB Bank thành công.",
        token=token,
        account_name=account_info.account_name,
        account_number=account_info.account_number,
        balance=account_info.balance,
    )


# ─────────────────────────────────────────────────
# GET /api/v1/bank/mbbank/info
# ─────────────────────────────────────────────────
@router.get("/info", response_model=MBBankInfoResponse)
async def get_mbbank_info(
    payload: dict = Depends(verify_token),
):
    """
    Lấy thông tin tài khoản MB Bank (yêu cầu JWT token).
    """
    account_no = payload.get("accountNo")
    if not account_no:
        raise HTTPException(status_code=400, detail="Token không chứa thông tin tài khoản.")

    # Lấy thông tin đăng nhập từ MongoDB
    collection = mbbank_accounts_collection()
    doc = await collection.find_one({"accountNo": account_no})
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản trong hệ thống.")

    # Login MB Bank và lấy thông tin
    try:
        password_plain = decrypt_aes256(doc["password"])
        service = MBBankService(username=doc["username"], password=password_plain)
        account_info = service.login(account_number=doc["accountNo"])
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=502, detail=f"Lỗi khi truy vấn MB Bank: {e}")

    return MBBankInfoResponse(
        account_name=account_info.account_name,
        account_number=account_info.account_number,
        balance=account_info.balance,
    )


# ─────────────────────────────────────────────────
# GET /api/v1/bank/mbbank/transactions
# ─────────────────────────────────────────────────
@router.get("/transactions", response_model=MBBankTransactionsResponse)
async def get_mbbank_transactions(
    from_date: str = Query(..., description="Ngày bắt đầu (YYYY-MM-DD)", examples=["2025-03-01"]),
    to_date: str = Query(..., description="Ngày kết thúc (YYYY-MM-DD)", examples=["2025-03-31"]),
    payload: dict = Depends(verify_token),
):
    """
    Lấy lịch sử giao dịch MB Bank (yêu cầu JWT token).
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

    # Lấy thông tin đăng nhập từ MongoDB
    collection = mbbank_accounts_collection()
    doc = await collection.find_one({"accountNo": account_no})
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản trong hệ thống.")

    # Lấy lịch sử giao dịch
    try:
        password_plain = decrypt_aes256(doc["password"])
        service = MBBankService(username=doc["username"], password=password_plain)
        history = service.getTransactionAccountHistory(
            account_number=doc["accountNo"],
            from_date=dt_from,
            to_date=dt_to,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=502, detail=f"Lỗi khi truy vấn MB Bank: {e}")

    transactions = [
        TransactionItem(
            transaction_date=tx.transaction_date,
            credit_amount=tx.credit_amount,
            debit_amount=tx.debit_amount,
            description=tx.description,
        )
        for tx in history.transactions
    ]

    return MBBankTransactionsResponse(
        account_number=history.account_number,
        from_date=history.from_date,
        to_date=history.to_date,
        total=len(transactions),
        transactions=transactions,
    )


# ─────────────────────────────────────────────────
# DELETE /api/v1/bank/mbbank/delete
# ─────────────────────────────────────────────────
@router.delete("/delete")
async def delete_mbbank_account(
    payload: dict = Depends(verify_token),
):
    """
    Xóa tài khoản MB Bank khỏi hệ thống (yêu cầu JWT token).
    """
    account_no = payload.get("accountNo")
    if not account_no:
        raise HTTPException(status_code=400, detail="Token không chứa thông tin tài khoản.")

    collection = mbbank_accounts_collection()
    result = await collection.delete_one({"accountNo": account_no})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản để xóa.")

    return {"message": f"Đã xóa tài khoản {account_no} khỏi hệ thống."}
