from pydantic import BaseModel


class SeABankAccountCreate(BaseModel):
    """Schema cho request body khi thêm tài khoản SeABank."""
    username: str
    password: str
    accountNo: str


class SeABankAccountResponse(BaseModel):
    """Schema response sau khi thêm tài khoản thành công."""
    message: str
    token: str
    account_name: str
    account_number: str
    balance: float


class SeABankInfoResponse(BaseModel):
    """Schema response thông tin tài khoản."""
    account_name: str
    account_number: str
    balance: float
    currency: str
    customer_id: str
    product_name: str


class SeABankTransactionItem(BaseModel):
    """Schema 1 giao dịch SeABank."""
    transaction_id: str
    transaction_date: str
    credit_amount: float
    debit_amount: float
    description: str
    sender_name: str
    sender_bank: str
    receiver_name: str
    receiver_bank: str


class SeABankTransactionsResponse(BaseModel):
    """Schema response lịch sử giao dịch."""
    account_number: str
    from_date: str
    to_date: str
    total: int
    transactions: list[SeABankTransactionItem]
