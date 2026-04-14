from fastapi import APIRouter, Depends
from app.core.security import verify_token

router = APIRouter()


@router.get("/")
async def list_banks(payload: dict = Depends(verify_token)):
    """Lấy danh sách ngân hàng."""
    return {
        "message": "Danh sách ngân hàng",
        "user": payload,
        "data": [],
    }


@router.get("/{bank_code}")
async def get_bank(bank_code: str, payload: dict = Depends(verify_token)):
    """Lấy thông tin chi tiết ngân hàng theo mã."""
    return {
        "message": f"Thông tin ngân hàng {bank_code}",
        "user": payload,
        "data": {"bank_code": bank_code},
    }


@router.post("/transfer")
async def create_transfer(payload: dict = Depends(verify_token)):
    """Tạo lệnh chuyển khoản."""
    return {
        "message": "Tạo lệnh chuyển khoản thành công",
        "user": payload,
        "data": {},
    }


@router.get("/account/{account_number}")
async def get_account(account_number: str, payload: dict = Depends(verify_token)):
    """Tra cứu thông tin tài khoản ngân hàng."""
    return {
        "message": f"Thông tin tài khoản {account_number}",
        "user": payload,
        "data": {"account_number": account_number},
    }
