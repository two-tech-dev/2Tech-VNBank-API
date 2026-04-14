from pydantic import BaseModel


class MBBankAccountCreate(BaseModel):
    """Schema cho request body khi thêm tài khoản MB Bank."""
    username: str
    password: str
    accountNo: str


class MBBankAccountResponse(BaseModel):
    """Schema response sau khi thêm tài khoản thành công."""
    message: str
    token: str
    account_name: str
    account_number: str
    balance: float


class MBBankInfoResponse(BaseModel):
    """Schema response thông tin tài khoản."""
    account_name: str
    account_number: str
    balance: float


class TransactionItem(BaseModel):
    """Schema 1 giao dịch."""
    transaction_date: str
    credit_amount: float
    debit_amount: float
    description: str


class MBBankTransactionsResponse(BaseModel):
    """Schema response lịch sử giao dịch."""
    account_number: str
    from_date: str
    to_date: str
    total: int
    transactions: list[TransactionItem]
