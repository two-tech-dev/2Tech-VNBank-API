from pydantic import BaseModel


class TPBankAccountCreate(BaseModel):
    """Schema cho request body khi thêm tài khoản TPBank."""
    username: str
    password: str
    accountNo: str


class TPBankAccountResponse(BaseModel):
    """Schema response sau khi thêm tài khoản thành công."""
    message: str
    token: str
    account_name: str
    account_number: str
    balance: float


class TPBankPendingResponse(BaseModel):
    """Schema response khi cần xác thực thiết bị (2-step flow)."""
    status: str  # "pending_verification"
    pending_id: str
    transaction_id: str
    message: str


class TPBankConfirmRequest(BaseModel):
    """Schema cho request body khi confirm device verification."""
    pending_id: str


class TPBankInfoResponse(BaseModel):
    """Schema response thông tin tài khoản."""
    account_name: str
    account_number: str
    balance: float
    currency: str


class TPBankTransactionItem(BaseModel):
    """Schema 1 giao dịch TPBank."""
    id: str
    reference: str
    description: str
    amount: float
    credit_debit_indicator: str
    booking_date: str
    running_balance: float
    perform_date: str
    transaction_date: str


class TPBankTransactionsResponse(BaseModel):
    """Schema response lịch sử giao dịch."""
    account_number: str
    from_date: str
    to_date: str
    total: int
    transactions: list[TPBankTransactionItem]
