import hashlib
import uuid
import datetime
import logging
from dataclasses import dataclass, field
import httpx

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────
LOGIN_URL = "https://ebankbackend.seanet.vn/canhan/api/authenticate-hash"
ACCOUNT_INFO_URL = "https://ebankms3.seanet.vn/p0603/api/p0603-topup/get-account-info"
TRANSACTION_URL = "https://ebankms1.seanet.vn/p03/api/p03-statement/get-trans-list-new"

COMMON_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
    "origin": "https://seanet.vn",
    "referer": "https://seanet.vn/",
    "sec-ch-ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
}


# ── Data classes ─────────────────────────────────────────
@dataclass
class SeABankAccountInfo:
    """Thông tin tài khoản SeABank."""
    account_number: str
    account_name: str
    balance: float
    currency: str = "VND"
    customer_id: str = ""
    product_name: str = ""


@dataclass
class SeABankTransaction:
    """Thông tin 1 giao dịch SeABank."""
    transaction_id: str
    transaction_date: str
    credit_amount: float
    debit_amount: float
    description: str
    sender_name: str = ""
    sender_bank: str = ""
    receiver_name: str = ""
    receiver_bank: str = ""


@dataclass
class SeABankTransactionHistory:
    """Kết quả lịch sử giao dịch SeABank."""
    account_number: str
    from_date: str
    to_date: str
    transactions: list[SeABankTransaction] = field(default_factory=list)


# ── Service class ────────────────────────────────────────
class SeABankService:
    """
    Service class để tương tác với ngân hàng SeABank.
    Gọi trực tiếp API SeANet (eBanking).
    """

    def __init__(self, username: str, password: str):
        """
        Khởi tạo SeABankService.

        Args:
            username: Tên đăng nhập SeABank.
            password: Mật khẩu (plain text, sẽ được hash SHA256 khi gửi).
        """
        self._username = username
        self._password = password
        self._token: str | None = None
        self._main_account: str | None = None
        self._customer_id: str | None = None

    @staticmethod
    def _hash_password(password: str) -> str:
        """SHA256 hash mật khẩu."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @staticmethod
    def _generate_context() -> str:
        """Tạo context string cho login request."""
        uid = str(uuid.uuid4())
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
        return f"{uid}_{ua}"

    def login(self) -> dict:
        """
        Đăng nhập SeABank, lấy id_token.

        Returns:
            dict chứa username, customerId, mainAccount, id_token.

        Raises:
            ValueError: Sai tài khoản hoặc mật khẩu.
            RuntimeError: Lỗi kết nối.
        """
        context = self._generate_context()
        password_hash = self._hash_password(self._password)

        payload = {
            "username": self._username,
            "password": password_hash,
            "rememberMe": False,
            "context": context,
            "channel": "SEAMOBILE3.0",
            "subChannel": "SEANET",
            "passwordType": "HASH",
            "captcha": None,
            "location": None,
            "longitude": None,
            "latitude": None,
            "ipAddress": None,
            "machineName": None,
            "machineType": None,
            "application": None,
            "version": None,
            "contextFull": context,
        }

        headers = {**COMMON_HEADERS, "Content-Type": "application/json", "accept-encoding": "gzip", "authority": "ebankbackend.seanet.vn"}

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(LOGIN_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.RequestError as e:
            logger.error("Lỗi kết nối SeABank login: %s", e)
            raise RuntimeError(f"Lỗi kết nối SeABank: {e}") from e

        if data.get("code") != "00":
            msg = data.get("message", "Unknown error")
            raise ValueError(f"Đăng nhập SeABank thất bại: {msg}")

        login_data = data["data"]
        self._token = login_data.get("id_token")
        self._main_account = login_data.get("mainAccount")
        self._customer_id = login_data.get("customerId")

        return {
            "username": login_data.get("username"),
            "customerId": self._customer_id,
            "mainAccount": self._main_account,
            "id_token": self._token,
        }

    def _ensure_logged_in(self):
        """Đảm bảo đã login trước khi gọi API khác."""
        if self._token is None:
            self.login()

    def _auth_headers(self) -> dict:
        """Tạo headers có Bearer token."""
        return {
            **COMMON_HEADERS,
            "Authorization": f"Bearer {self._token}",
            "cache-control": "no-cache",
            "pragma": "no-cache",
        }

    def get_account_info(self) -> SeABankAccountInfo:
        """
        Lấy thông tin tài khoản (số dư, tên chủ TK).

        Returns:
            SeABankAccountInfo

        Raises:
            ValueError: Không tìm thấy tài khoản.
            RuntimeError: Lỗi kết nối.
        """
        self._ensure_logged_in()

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(ACCOUNT_INFO_URL, headers=self._auth_headers())
                resp.raise_for_status()
                data = resp.json()
        except httpx.RequestError as e:
            logger.error("Lỗi kết nối SeABank account info: %s", e)
            raise RuntimeError(f"Lỗi kết nối SeABank: {e}") from e

        if data.get("code") != "00":
            raise RuntimeError(f"Lỗi lấy thông tin tài khoản: {data.get('message')}")

        account_list = data.get("data", {}).get("accountList", [])
        if not account_list:
            raise ValueError("Không tìm thấy tài khoản nào.")

        # Tìm tài khoản chính (mainAccount) hoặc lấy tài khoản đầu tiên
        acct = None
        for a in account_list:
            if a.get("accountID") == self._main_account:
                acct = a
                break
        if acct is None:
            acct = account_list[0]

        return SeABankAccountInfo(
            account_number=acct.get("accountID", ""),
            account_name=acct.get("shortName", ""),
            balance=float(acct.get("availBal", 0) or 0),
            currency=acct.get("currency", "VND"),
            customer_id=acct.get("customerID", ""),
            product_name=acct.get("productName", ""),
        )

    def get_transaction_history(
        self,
        account_id: str | None = None,
        from_date: datetime.datetime | None = None,
        to_date: datetime.datetime | None = None,
    ) -> SeABankTransactionHistory:
        """
        Lấy lịch sử giao dịch.

        Args:
            account_id: Số tài khoản 12 số (mặc định: mainAccount).
            from_date: Ngày bắt đầu (mặc định: 30 ngày trước).
            to_date: Ngày kết thúc (mặc định: hôm nay).

        Returns:
            SeABankTransactionHistory

        Raises:
            RuntimeError: Lỗi kết nối hoặc API trả lỗi.
        """
        self._ensure_logged_in()

        if to_date is None:
            to_date = datetime.datetime.now()
        if from_date is None:
            from_date = to_date - datetime.timedelta(days=30)
        if account_id is None:
            account_id = self._main_account

        # SeABank API dùng format YYYYMMDD
        payload = {
            "accountID": account_id,
            "fromDate": from_date.strftime("%Y%m%d"),
            "toDate": to_date.strftime("%Y%m%d"),
            "coCode": "",
            "language": "GB",
            "shortTitle": "",
            "currency": "",
            "productName": "",
        }

        headers = {
            **self._auth_headers(),
            "Content-Type": "application/json",
            "accept-encoding": "gzip",
            "authority": "ebankms1.seanet.vn",
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(TRANSACTION_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.RequestError as e:
            logger.error("Lỗi kết nối SeABank transactions: %s", e)
            raise RuntimeError(f"Lỗi kết nối SeABank: {e}") from e

        if data.get("code") != "00":
            raise RuntimeError(f"Lỗi lấy lịch sử giao dịch: {data.get('message')}")

        raw_list = data.get("data", []) or []
        transactions: list[SeABankTransaction] = []

        for tx in raw_list:
            total_amount = float(tx.get("totalAmount", 0) or 0)
            credit = total_amount if total_amount > 0 else 0.0
            debit = abs(total_amount) if total_amount < 0 else 0.0

            transactions.append(
                SeABankTransaction(
                    transaction_id=tx.get("transID", ""),
                    transaction_date=tx.get("transactionDate", ""),
                    credit_amount=credit,
                    debit_amount=debit,
                    description=tx.get("description", ""),
                    sender_name=tx.get("customerName", ""),
                    sender_bank=tx.get("sendingBank", "") or "",
                    receiver_name=tx.get("recipient", ""),
                    receiver_bank=tx.get("receivingBank", "") or "",
                )
            )

        return SeABankTransactionHistory(
            account_number=account_id or "",
            from_date=from_date.strftime("%Y-%m-%d"),
            to_date=to_date.strftime("%Y-%m-%d"),
            transactions=transactions,
        )
