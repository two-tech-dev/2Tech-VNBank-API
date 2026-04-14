"""
TPBank API Routes
=================
- POST /add      — Thêm tài khoản (login, nếu non-trust → pending)
- POST /confirm  — Xác nhận thiết bị (check → re-login → register → save)
- GET  /info     — Lấy thông tin tài khoản (re-login mỗi lần)
- GET  /transactions — Lấy lịch sử giao dịch
- DELETE /delete — Xóa tài khoản
"""

import datetime
import logging
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import verify_token, verify_admin_token, create_token
from app.core.database import tpbank_accounts_collection, tpbank_pending_collection
from app.services.tpbank_service import TPBankService
from app.utils.crypto import encrypt_aes256, decrypt_aes256
from app.models.tpbank_account import (
    TPBankAccountCreate,
    TPBankAccountResponse,
    TPBankPendingResponse,
    TPBankConfirmRequest,
    TPBankInfoResponse,
    TPBankTransactionsResponse,
    TPBankTransactionItem,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────────
# POST /add
# ─────────────────────────────────────────────────
@router.post("/add")
async def add_tpbank_account(
    body: TPBankAccountCreate,
    _admin: str = Depends(verify_admin_token),
):
    """
    Thêm tài khoản TPBank.
    - Device đã trusted → trả JWT token ngay.
    - Device mới (70101) → trả pending_id, client gọi /confirm sau.
    """
    collection = tpbank_accounts_collection()

    existing = await collection.find_one({"accountNo": body.accountNo})
    if existing:
        raise HTTPException(409, "Tài khoản này đã được thêm trước đó.")

    with TPBankService(username=body.username, password=body.password) as svc:
        try:
            result = svc.login()
        except ValueError as e:
            raise HTTPException(400, f"Đăng nhập TPBank thất bại: {e}")
        except RuntimeError as e:
            raise HTTPException(502, f"Lỗi kết nối TPBank: {e}")

        # ── Device đã trusted ────────────────────────
        if result.success and result.access_token:
            try:
                info = svc.get_account_info(result.access_token)
            except (ValueError, RuntimeError) as e:
                raise HTTPException(502, f"Lỗi khi lấy thông tin tài khoản: {e}")

            doc = {
                "username": body.username,
                "password": encrypt_aes256(body.password),
                "accountNo": body.accountNo,
                "accountName": info.account_name,
                "deviceId": svc.device_id,
                "bankCode": "tpbank",
                "createdAt": datetime.datetime.now(datetime.timezone.utc),
            }
            ins = await collection.insert_one(doc)

            token = create_token({
                "account_id": str(ins.inserted_id),
                "accountNo": body.accountNo,
                "bankCode": "tpbank",
            })

            return TPBankAccountResponse(
                message="Thêm tài khoản TPBank thành công.",
                token=token,
                account_name=info.account_name,
                account_number=body.accountNo,
                balance=info.balance,
            )

        # ── Cần xác thực thiết bị ────────────────────
        if result.needs_verification:
            pending_col = tpbank_pending_collection()
            pending_doc = {
                "username": body.username,
                "password": encrypt_aes256(body.password),
                "accountNo": body.accountNo,
                "deviceId": svc.device_id,
                "rsaToken": result.rsa_token,
                "transactionId": result.transaction_id,
                "status": "pending",
                "createdAt": datetime.datetime.now(datetime.timezone.utc),
            }
            ins = await pending_col.insert_one(pending_doc)

            return TPBankPendingResponse(
                status="pending_verification",
                pending_id=str(ins.inserted_id),
                transaction_id=result.transaction_id or "",
                message="Vui lòng xác nhận trên ứng dụng TPBank (eToken), sau đó gọi API /confirm.",
            )

        raise HTTPException(502, "Đăng nhập TPBank thất bại: phản hồi không xác định.")


# ─────────────────────────────────────────────────
# POST /confirm
# ─────────────────────────────────────────────────
@router.post("/confirm")
async def confirm_tpbank_device(
    body: TPBankConfirmRequest,
    _admin: str = Depends(verify_admin_token),
):
    """
    Xác nhận thiết bị TPBank.
    Non-blocking: check 1 lần, nếu chưa confirm → trả pending để client retry.

    Flow khi CONFIRM:
      check → re-login(transactionId) → register_device → get_info → lưu DB
    """
    pending_col = tpbank_pending_collection()
    accounts_col = tpbank_accounts_collection()

    # Tìm pending
    try:
        pdoc = await pending_col.find_one({"_id": ObjectId(body.pending_id)})
    except Exception:
        raise HTTPException(400, "pending_id không hợp lệ.")

    if not pdoc:
        raise HTTPException(404, "Không tìm thấy yêu cầu pending.")
    if pdoc.get("status") == "confirmed":
        raise HTTPException(409, "Yêu cầu này đã được xác nhận trước đó.")

    # Đã tồn tại?
    if await accounts_col.find_one({"accountNo": pdoc["accountNo"]}):
        await pending_col.delete_one({"_id": pdoc["_id"]})
        raise HTTPException(409, "Tài khoản này đã được thêm trước đó.")

    # Dùng cùng device_id đã lưu khi /add
    password_plain = decrypt_aes256(pdoc["password"])
    with TPBankService(
        username=pdoc["username"],
        password=password_plain,
        device_id=pdoc["deviceId"],
    ) as svc:

        # ── Check verification (1 lần, non-blocking) ─
        try:
            status = svc.check_device_verification(
                rsa_token=pdoc["rsaToken"],
                transaction_id=pdoc["transactionId"],
            )
        except RuntimeError as e:
            raise HTTPException(502, f"Lỗi khi kiểm tra xác thực: {e}")

        print(f"[TPBank confirm] check_device_verification → status={status}")

        if status != "CONFIRM":
            return {
                "status": "pending",
                "message": "Chưa xác thực. Vui lòng xác nhận trên app TPBank và thử lại.",
            }

        # ── Re-login với transactionId để lấy access_token ─
        print(f"[TPBank confirm] re-login với transactionId={pdoc.get('transactionId', '')}")
        try:
            login2 = svc.login(transaction_id=pdoc.get("transactionId", ""))
        except (ValueError, RuntimeError) as e:
            print(f"[TPBank confirm] re-login FAILED: {e}")
            raise HTTPException(502, f"Đăng nhập lại thất bại sau xác thực: {e}")

        print(f"[TPBank confirm] re-login → success={login2.success}, has_token={bool(login2.access_token)}")

        if not login2.success or not login2.access_token:
            raise HTTPException(502, "Xác thực OK nhưng không nhận được access_token.")

        # ── Register device ──────────────────────────
        print("[TPBank confirm] calling register_device...")
        try:
            svc.register_device(login2.access_token)
        except RuntimeError as e:
            print(f"[TPBank confirm] register_device warning: {e}")

        # ── Lấy thông tin tài khoản ──────────────────
        print("[TPBank confirm] calling get_account_info...")
        try:
            info = svc.get_account_info(login2.access_token)
        except (ValueError, RuntimeError) as e:
            raise HTTPException(502, f"Lỗi khi lấy thông tin tài khoản: {e}")

    # ── Lưu DB ───────────────────────────────────────
    doc = {
        "username": pdoc["username"],
        "password": pdoc["password"],   # đã encrypt sẵn
        "accountNo": pdoc["accountNo"],
        "accountName": info.account_name,
        "deviceId": pdoc["deviceId"],
        "bankCode": "tpbank",
        "createdAt": datetime.datetime.now(datetime.timezone.utc),
    }
    ins = await accounts_col.insert_one(doc)

    await pending_col.update_one(
        {"_id": pdoc["_id"]},
        {"$set": {"status": "confirmed"}},
    )

    token = create_token({
        "account_id": str(ins.inserted_id),
        "accountNo": pdoc["accountNo"],
        "bankCode": "tpbank",
    })

    return TPBankAccountResponse(
        message="Xác thực thiết bị và thêm tài khoản TPBank thành công.",
        token=token,
        account_name=info.account_name,
        account_number=pdoc["accountNo"],
        balance=info.balance,
    )


# ─────────────────────────────────────────────────
# GET /info
# ─────────────────────────────────────────────────
@router.get("/info", response_model=TPBankInfoResponse)
async def get_tpbank_info(
    payload: dict = Depends(verify_token),
):
    """Lấy thông tin tài khoản (re-login mỗi lần, dùng deviceId đã lưu)."""
    account_no = payload.get("accountNo")
    if not account_no:
        raise HTTPException(400, "Token không chứa thông tin tài khoản.")

    collection = tpbank_accounts_collection()
    doc = await collection.find_one({"accountNo": account_no})
    if not doc:
        raise HTTPException(404, "Không tìm thấy tài khoản trong hệ thống.")

    with TPBankService(
        username=doc["username"],
        password=decrypt_aes256(doc["password"]),
        device_id=doc["deviceId"],
    ) as svc:
        try:
            result = svc.login()
            if not result.success or not result.access_token:
                raise RuntimeError("Login thất bại (device có thể đã bị revoke).")
            info = svc.get_account_info(result.access_token)
        except (ValueError, RuntimeError) as e:
            raise HTTPException(502, f"Lỗi khi truy vấn TPBank: {e}")

    return TPBankInfoResponse(
        account_name=info.account_name,
        account_number=info.account_number,
        balance=info.balance,
        currency=info.currency,
    )


# ─────────────────────────────────────────────────
# GET /transactions
# ─────────────────────────────────────────────────
@router.get("/transactions", response_model=TPBankTransactionsResponse)
async def get_tpbank_transactions(
    from_date: str = Query(..., description="YYYY-MM-DD", examples=["2026-04-01"]),
    to_date: str = Query(..., description="YYYY-MM-DD", examples=["2026-04-09"]),
    payload: dict = Depends(verify_token),
):
    """Lấy lịch sử giao dịch (re-login mỗi lần, dùng deviceId đã lưu)."""
    account_no = payload.get("accountNo")
    if not account_no:
        raise HTTPException(400, "Token không chứa thông tin tài khoản.")

    try:
        dt_from = datetime.datetime.strptime(from_date, "%Y-%m-%d")
        dt_to = datetime.datetime.strptime(to_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Định dạng ngày không hợp lệ. Sử dụng YYYY-MM-DD.")

    collection = tpbank_accounts_collection()
    doc = await collection.find_one({"accountNo": account_no})
    if not doc:
        raise HTTPException(404, "Không tìm thấy tài khoản trong hệ thống.")

    with TPBankService(
        username=doc["username"],
        password=decrypt_aes256(doc["password"]),
        device_id=doc["deviceId"],
    ) as svc:
        try:
            result = svc.login()
            if not result.success or not result.access_token:
                raise RuntimeError("Login thất bại.")
            history = svc.get_transaction_history(
                account_no=doc["accountNo"],
                from_date=dt_from,
                to_date=dt_to,
                access_token=result.access_token,
            )
        except (ValueError, RuntimeError) as e:
            raise HTTPException(502, f"Lỗi khi truy vấn TPBank: {e}")

    return TPBankTransactionsResponse(
        account_number=history.account_number,
        from_date=history.from_date,
        to_date=history.to_date,
        total=history.total,
        transactions=[
            TPBankTransactionItem(
                id=tx.id,
                reference=tx.reference,
                description=tx.description,
                amount=tx.amount,
                credit_debit_indicator=tx.credit_debit_indicator,
                booking_date=tx.booking_date,
                running_balance=tx.running_balance,
                perform_date=tx.perform_date,
                transaction_date=tx.transaction_date,
            )
            for tx in history.transactions
        ],
    )


# ─────────────────────────────────────────────────
# DELETE /delete
# ─────────────────────────────────────────────────
@router.delete("/delete")
async def delete_tpbank_account(
    payload: dict = Depends(verify_token),
):
    """Xóa tài khoản TPBank khỏi hệ thống."""
    account_no = payload.get("accountNo")
    if not account_no:
        raise HTTPException(400, "Token không chứa thông tin tài khoản.")

    collection = tpbank_accounts_collection()
    result = await collection.delete_one({"accountNo": account_no})

    if result.deleted_count == 0:
        raise HTTPException(404, "Không tìm thấy tài khoản để xóa.")

    return {"message": f"Đã xóa tài khoản TPBank {account_no} khỏi hệ thống."}
