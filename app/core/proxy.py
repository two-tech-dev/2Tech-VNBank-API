import httpx
from fastapi import Request, HTTPException
from fastapi.responses import Response
import logging

logger = logging.getLogger(__name__)

# Connection pool tối ưu cho việc chuyển tiếp request
_client = httpx.AsyncClient(
    limits=httpx.Limits(max_keepalive_connections=50, max_connections=100),
    timeout=httpx.Timeout(30.0),
)


async def forward_request(request: Request, target_url: str) -> Response:
    """
    Forward request từ client sang backend service đích.

    Args:
        request: Request gốc từ client.
        target_url: URL đầy đủ của backend service.

    Returns:
        Response từ backend service.
    """
    headers = dict(request.headers)
    headers.pop("host", None)

    url = httpx.URL(target_url)
    if request.url.query:
        url = url.copy_with(query=request.url.query.encode("utf-8"))

    try:
        content = await request.body()
    except Exception:
        content = None

    try:
        proxy_req = _client.build_request(
            method=request.method,
            url=url,
            headers=headers,
            content=content,
        )
        proxy_response = await _client.send(proxy_req, stream=True)
        resp_content = await proxy_response.aread()

        # Lọc bỏ các header hop-by-hop
        out_headers = dict(proxy_response.headers)
        for h in ("content-length", "transfer-encoding", "content-encoding", "connection"):
            out_headers.pop(h, None)

        return Response(
            content=resp_content,
            status_code=proxy_response.status_code,
            headers=out_headers,
            media_type=proxy_response.headers.get("content-type"),
        )
    except httpx.RequestError as exc:
        logger.error("Lỗi khi chuyển tiếp request tới %s: %s", target_url, exc)
        raise HTTPException(status_code=502, detail="Bad Gateway: Backend service không phản hồi.")
