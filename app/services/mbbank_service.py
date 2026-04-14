import datetime
import logging
from dataclasses import dataclass, field
import mbbank

logger = logging.getLogger(__name__)


@dataclass
class AccountInfo:
    """Thông tin tài khoản sau khi login thành công."""
    account_number: str
    account_name: str
    balance: float
    currency: str = "VND"


@dataclass
class Transaction:
    """Thông tin 1 giao dịch."""
    transaction_date: str
    credit_amount: float
    debit_amount: float
    description: str


@dataclass
class TransactionHistory:
    """Kết quả trả về khi lấy lịch sử giao dịch."""
    account_number: str
    from_date: str
    to_date: str
    transactions: list[Transaction] = field(default_factory=list)


class MBBankService:
    """
    Service class để tương tác với ngân hàng MB Bank.
    Sử dụng thư viện mbbank-lib.
    """

    def __init__(self, username: str, password: str):
        """
        Khởi tạo MBBankService.

        Args:
            username: Số điện thoại / tên đăng nhập MB Bank.
            password: Mật khẩu đăng nhập.
        """
        self._username = username
        self._password = password
        self._client: mbbank.MBBank | None = None

    def _get_client(self) -> mbbank.MBBank:
        """Lazy init MB Bank client."""
        if self._client is None:
            self._client = mbbank.MBBank(
                username=self._username,
                password=self._password,
            )
        return self._client

    def login(self, account_number: str) -> AccountInfo:
        """
        Đăng nhập và lấy thông tin tài khoản theo số tài khoản.

        Args:
            account_number: Số tài khoản cần tra cứu.

        Returns:
            AccountInfo chứa tên chủ tài khoản và số dư.

        Raises:
            ValueError: Không tìm thấy tài khoản.
            RuntimeError: Lỗi kết nối hoặc xác thực.
        """
        try:
            client = self._get_client()
            balance_info = client.getBalance()

            if not balance_info.acct_list:
                raise ValueError("Đăng nhập thành công nhưng không tìm thấy tài khoản nào.")

            # Tìm tài khoản khớp với account_number
            for acct in balance_info.acct_list:
                if acct.acctNo == account_number:
                    return AccountInfo(
                        account_number=acct.acctNo,
                        account_name=getattr(acct, "acctNm", ""),
                        balance=float(getattr(acct, "currentBalance", 0)),
                        currency=getattr(acct, "currency", "VND"),
                    )

            # Nếu không khớp, trả về tài khoản đầu tiên kèm cảnh báo
            logger.warning(
                "Không tìm thấy tài khoản %s, trả về tài khoản đầu tiên.", account_number
            )
            acct = balance_info.acct_list[0]
            return AccountInfo(
                account_number=acct.acctNo,
                account_name=getattr(acct, "acctNm", ""),
                balance=float(getattr(acct, "currentBalance", 0)),
                currency=getattr(acct, "currency", "VND"),
            )

        except ValueError:
            raise
        except Exception as e:
            logger.error("Lỗi khi login MB Bank: %s", e)
            raise RuntimeError(f"Lỗi khi đăng nhập MB Bank: {e}") from e

    def getTransactionAccountHistory(
        self,
        account_number: str,
        from_date: datetime.datetime | None = None,
        to_date: datetime.datetime | None = None,
    ) -> TransactionHistory:
        """
        Lấy lịch sử giao dịch của tài khoản.

        Args:
            account_number: Số tài khoản cần tra cứu.
            from_date: Ngày bắt đầu (mặc định: 30 ngày trước).
            to_date: Ngày kết thúc (mặc định: hôm nay).

        Returns:
            TransactionHistory chứa danh sách giao dịch.

        Raises:
            RuntimeError: Lỗi kết nối hoặc xác thực.
        """
        if to_date is None:
            to_date = datetime.datetime.now()
        if from_date is None:
            from_date = to_date - datetime.timedelta(days=30)

        try:
            client = self._get_client()
            history = client.getTransactionAccountHistory(
                accountNo=account_number,
                from_date=from_date,
                to_date=to_date,
            )

            transactions: list[Transaction] = []
            if history.transactionHistoryList:
                for tx in history.transactionHistoryList:
                    transactions.append(
                        Transaction(
                            transaction_date=str(getattr(tx, "transactionDate", "")),
                            credit_amount=float(getattr(tx, "creditAmount", 0) or 0),
                            debit_amount=float(getattr(tx, "debitAmount", 0) or 0),
                            description=getattr(tx, "description", ""),
                        )
                    )

            return TransactionHistory(
                account_number=account_number,
                from_date=from_date.strftime("%Y-%m-%d"),
                to_date=to_date.strftime("%Y-%m-%d"),
                transactions=transactions,
            )

        except Exception as e:
            logger.error("Lỗi khi lấy lịch sử giao dịch: %s", e)
            raise RuntimeError(f"Lỗi khi lấy lịch sử giao dịch: {e}") from e
