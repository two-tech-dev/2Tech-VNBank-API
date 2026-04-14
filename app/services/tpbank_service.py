"""
TPBank eBank Service
====================
Tương tác với API TPBank (ebank.tpb.vn).

Flow xác thực thiết bị mới (non-trust):
  1. POST /auth/login/v4/non-trust  → error 70101 + rsa_token, transaction_id
  2. User xác nhận trên app TPBank Mobile (eToken)
  3. POST /auth/transaction/check   → status = "CONFIRM"
  4. POST /auth/login/v4/non-trust  → (với transactionId) → access_token
  5. POST /device/.../device/login  → register device
  6. Các API khác dùng access_token

Flow login device đã trust:
  1. POST /auth/login/v4/non-trust  → access_token trực tiếp
"""

import uuid
import datetime
import logging
from dataclasses import dataclass, field
import httpx

logger = logging.getLogger(__name__)

# ── URLs ─────────────────────────────────────────────────
BASE_URL = "https://ebank.tpb.vn/gateway"
LOGIN_URL = f"{BASE_URL}/api/auth/login/v4/non-trust"
CHECK_URL = f"{BASE_URL}/api/auth/transaction/check"
REGISTER_DEVICE_URL = f"{BASE_URL}/api/device-presentation-service/v1/device/register"
LOGIN_DEVICE_URL = f"{BASE_URL}/api/device-presentation-service/v1/device/login"
ACCOUNT_INFO_URL = f"{BASE_URL}/api/common-presentation-service/v1/bank-accounts"
TRANSACTION_URL = f"{BASE_URL}/api/smart-search-presentation-service-v2/v2/account-transactions/find"

# ── Browser fingerprint constants ────────────────────────
APP_VERSION = "2026.03.27"
PLATFORM_NAME = "WEB"
PLATFORM_VERSION = "146"
SOURCE_APP = "HYDRO"
DEVICE_NAME = "Chrome"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36"
)


# ── Helpers ──────────────────────────────────────────────

def generate_device_id() -> str:
    """Tạo device ID ngẫu nhiên (45 ký tự alphanumeric, mixed case)."""
    import string
    import random
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=45))


def _build_headers(device_id: str, access_token: str | None = None) -> dict:
    """Headers chung cho tất cả request tới TPBank."""
    return {
        "APP_VERSION": APP_VERSION,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Authorization": f"Bearer {access_token}" if access_token else "Bearer",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "DEVICE_ID": device_id,
        "DEVICE_NAME": DEVICE_NAME,
        "Origin": "https://ebank.tpb.vn",
        "PLATFORM_NAME": PLATFORM_NAME,
        "PLATFORM_VERSION": PLATFORM_VERSION,
        "Pragma": "no-cache",
        "Referer": "https://ebank.tpb.vn/retail/vX/",
        "SOURCE_APP": SOURCE_APP,
        "USER_NAME": "HYD",
        "User-Agent": USER_AGENT,
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }


# ── Data classes ─────────────────────────────────────────

@dataclass
class LoginResult:
    """Kết quả từ login API."""
    success: bool = False
    access_token: str | None = None
    expires_in: int = 0
    # Verification fields (error 70101)
    needs_verification: bool = False
    rsa_token: str | None = None
    transaction_id: str | None = None


@dataclass
class AccountInfo:
    """Thông tin tài khoản."""
    account_number: str
    account_name: str
    balance: float
    currency: str = "VND"


@dataclass
class Transaction:
    """1 giao dịch."""
    id: str
    reference: str
    description: str
    amount: float
    credit_debit_indicator: str
    booking_date: str
    running_balance: float
    perform_date: str = ""
    transaction_date: str = ""


@dataclass
class TransactionHistory:
    """Kết quả lịch sử giao dịch."""
    account_number: str
    from_date: str
    to_date: str
    total: int = 0
    transactions: list[Transaction] = field(default_factory=list)


# ── Service ──────────────────────────────────────────────

class TPBankService:
    """
    Client TPBank dùng 1 httpx.Client session xuyên suốt
    để giữ cookies (NSC load balancer, XSRF-TOKEN, ...).
    """

    def __init__(
        self,
        username: str,
        password: str,
        device_id: str | None = None,
    ):
        self.username = username
        self.password = password
        self.device_id = device_id or generate_device_id()
        self.access_token: str | None = None
        # Session giữ cookies xuyên suốt
        self._http = httpx.Client(
            timeout=30.0,
            verify=True,
            follow_redirects=True,
        )

    # ── lifecycle ────────────────────────────────────────

    def close(self):
        """Đóng HTTP session."""
        try:
            self._http.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __del__(self):
        self.close()

    # ── private helpers ──────────────────────────────────

    def _headers(self, token: str | None = None) -> dict:
        return _build_headers(self.device_id, token or self.access_token)

    def _post(self, url: str, payload: dict, token: str | None = None) -> dict:
        """POST request dùng session, trả JSON (hoặc {} nếu body rỗng)."""
        try:
            resp = self._http.post(url, json=payload, headers=self._headers(token))
            text = resp.text.strip()
            if not text:
                logger.debug("POST %s → %s (empty body)", url, resp.status_code)
                return {}
            data = resp.json()
            logger.debug("POST %s → %s: %s", url, resp.status_code, data)
            return data
        except httpx.RequestError as e:
            logger.error("Request error %s: %s", url, e)
            raise RuntimeError(f"Lỗi kết nối TPBank ({url}): {e}") from e

    def _get(self, url: str, token: str | None = None) -> dict | list:
        """GET request dùng session, trả JSON."""
        try:
            resp = self._http.get(url, headers=self._headers(token))
            data = resp.json()
            logger.debug("GET %s → %s", url, resp.status_code)
            return data
        except httpx.RequestError as e:
            logger.error("Request error %s: %s", url, e)
            raise RuntimeError(f"Lỗi kết nối TPBank ({url}): {e}") from e

    # ── 1. LOGIN ─────────────────────────────────────────

    def login(self, transaction_id: str = "") -> LoginResult:
        """
        Đăng nhập TPBank.
        - transaction_id rỗng: lần login đầu tiên
        - transaction_id có giá trị: re-login sau khi device đã confirm

        Raises:
            ValueError: Sai tài khoản/mật khẩu.
            RuntimeError: Lỗi kết nối hoặc lỗi TPBank không xác định.
        """
        data = self._post(LOGIN_URL, {
            "username": self.username,
            "password": self.password,
            "deviceId": self.device_id,
            "transactionId": transaction_id,
        })

        # Thành công — có access_token
        if data.get("access_token"):
            self.access_token = data["access_token"]
            logger.info("TPBank login OK (device trusted)")
            return LoginResult(
                success=True,
                access_token=data["access_token"],
                expires_in=data.get("expires_in", 900),
            )

        # Xử lý error
        error = data.get("error", {})
        code = error.get("error_code", "")

        # 70101 — cần xác thực thiết bị
        if code == "70101":
            logger.info("TPBank login → cần xác thực thiết bị (70101)")
            return LoginResult(
                needs_verification=True,
                rsa_token=error.get("rsa_token"),
                transaction_id=error.get("transaction_id"),
            )

        # 50525 — sai credentials
        if code == "50525":
            remain = error.get("remain_try_number", "?")
            limit = error.get("limit_try_number", "?")
            raise ValueError(f"Sai tên đăng nhập hoặc mật khẩu. Còn {remain}/{limit} lần thử.")

        # Lỗi khác
        msg = error.get("error_message", str(data))
        raise RuntimeError(f"Đăng nhập TPBank thất bại: {msg}")

    # ── 2. CHECK DEVICE VERIFICATION ─────────────────────

    def check_device_verification(self, rsa_token: str, transaction_id: str) -> str:
        """
        Check 1 lần xem user đã confirm trên app chưa.
        Trả status string: "PENDING", "CONFIRM", ...
        KHÔNG trả access_token — cần gọi login() lại.
        """
        data = self._post(CHECK_URL, {
            "rsaToken": rsa_token,
            "transactionId": transaction_id,
        })
        status = data.get("status", "PENDING")
        logger.info("TPBank check verification → %s", status)
        return status

    # ── 3. REGISTER DEVICE ───────────────────────────────

    def register_device(self, access_token: str | None = None) -> dict:
        """
        Đăng ký device + login device.
        Bước 1: POST /device/register → deviceManagementId
        Bước 2: POST /device/login   → với deviceManagementId đó
        """
        token = access_token or self.access_token
        if not token:
            raise RuntimeError("Chưa có access_token.")

        # Bước 1: Register
        register_payload = {
            "app": SOURCE_APP,
            "platformName": PLATFORM_NAME,
            "platformVersion": PLATFORM_VERSION,
            "deviceId": self.device_id,
            "deviceName": DEVICE_NAME,
            "appVersion": APP_VERSION,
        }

        try:
            resp = self._http.post(
                REGISTER_DEVICE_URL, json=register_payload, headers=self._headers(token)
            )
            body = resp.text.strip()
            print(f"[TPBank] register_device → status={resp.status_code}, body={body or '(empty)'}")
            register_data = resp.json() if body else {}
        except httpx.RequestError as e:
            print(f"[TPBank] register_device ERROR: {e}")
            raise RuntimeError(f"Lỗi kết nối TPBank register device: {e}") from e

        # Bước 2: Login device với deviceManagementId từ register
        device_mgmt_id = register_data.get("deviceManagementId", "")
        if not device_mgmt_id:
            print("[TPBank] register_device: không có deviceManagementId, bỏ qua login device")
            return register_data

        login_payload = {
            "deviceManagementId": device_mgmt_id,
            "appVersion": APP_VERSION,
        }

        try:
            resp2 = self._http.post(
                LOGIN_DEVICE_URL, json=login_payload, headers=self._headers(token)
            )
            body2 = resp2.text.strip()
            print(f"[TPBank] login_device → status={resp2.status_code}, body={body2 or '(empty)'}")
            return resp2.json() if body2 else {}
        except httpx.RequestError as e:
            print(f"[TPBank] login_device ERROR: {e}")
            raise RuntimeError(f"Lỗi kết nối TPBank login device: {e}") from e

    # ── 4. ACCOUNT INFO ──────────────────────────────────

    def get_account_info(self, access_token: str | None = None) -> AccountInfo:
        """Lấy thông tin tài khoản (số dư, tên, ...)."""
        token = access_token or self.access_token
        if not token:
            raise RuntimeError("Chưa có access_token.")

        url = f"{ACCOUNT_INFO_URL}?function=home"
        data = self._get(url, token=token)

        if not isinstance(data, list) or len(data) == 0:
            raise ValueError("Không tìm thấy tài khoản TPBank nào.")

        acct = data[0]
        return AccountInfo(
            account_number=acct.get("BBAN", ""),
            account_name=acct.get("name", ""),
            balance=float(acct.get("availableBalance", 0) or 0),
            currency=acct.get("currency", "VND"),
        )

    # ── 5. TRANSACTION HISTORY ───────────────────────────

    def get_transaction_history(
        self,
        account_no: str,
        from_date: datetime.datetime | None = None,
        to_date: datetime.datetime | None = None,
        access_token: str | None = None,
        page_size: int = 400,
    ) -> TransactionHistory:
        """Lấy lịch sử giao dịch."""
        token = access_token or self.access_token
        if not token:
            raise RuntimeError("Chưa có access_token.")

        now = datetime.datetime.now()
        if to_date is None:
            to_date = now
        if from_date is None:
            from_date = now - datetime.timedelta(days=30)

        data = self._post(TRANSACTION_URL, {
            "pageNumber": 1,
            "pageSize": page_size,
            "accountNo": account_no,
            "currency": "VND",
            "maxAcentrysrno": "",
            "fromDate": from_date.strftime("%Y%m%d"),
            "toDate": to_date.strftime("%Y%m%d"),
            "keyword": "",
        }, token=token)

        txns = [
            Transaction(
                id=tx.get("id", ""),
                reference=tx.get("reference", ""),
                description=tx.get("description", ""),
                amount=float(tx.get("amount", 0) or 0),
                credit_debit_indicator=tx.get("creditDebitIndicator", ""),
                booking_date=tx.get("bookingDate", ""),
                running_balance=float(tx.get("runningBalance", 0) or 0),
                perform_date=tx.get("performDate", ""),
                transaction_date=tx.get("transactionDate", ""),
            )
            for tx in (data.get("transactionInfos") or [])
        ]

        return TransactionHistory(
            account_number=account_no,
            from_date=from_date.strftime("%Y-%m-%d"),
            to_date=to_date.strftime("%Y-%m-%d"),
            total=int(data.get("totalRows", 0) or 0),
            transactions=txns,
        )
