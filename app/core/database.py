from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    """Lấy hoặc tạo MongoDB client (singleton)."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGODB_URI)
    return _client


def get_database():
    """Lấy database instance."""
    return get_client()[settings.MONGODB_DB_NAME]


def get_collection(name: str):
    """Lấy collection theo tên."""
    return get_database()[name]


# Collection chứa thông tin tài khoản MB Bank
def mbbank_accounts_collection():
    return get_collection("mbbank_accounts")


# Collection chứa thông tin tài khoản SeABank
def seabank_accounts_collection():
    return get_collection("seabank_accounts")


# Collection chứa thông tin tài khoản TPBank
def tpbank_accounts_collection():
    return get_collection("tpbank_accounts")


# Collection chứa thông tin pending verification TPBank
def tpbank_pending_collection():
    return get_collection("tpbank_pending")
