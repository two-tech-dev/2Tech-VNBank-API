import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """
    Cấu hình logging format chuẩn cho toàn bộ ứng dụng.
    Gọi hàm này 1 lần duy nhất khi khởi chạy app.
    """
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    # Giảm noise từ thư viện bên ngoài
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
