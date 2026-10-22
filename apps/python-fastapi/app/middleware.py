import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger("app.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request/response to make it easier to troubleshoot client integrations."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        body = await request.body()
        started = time.perf_counter()
        logger.info(
            "request method=%s path=%s query=%s headers=%s body=%s client=%s",
            request.method,
            request.url.path,
            request.url.query,
            dict(request.headers),
            body.decode(errors="replace"),
            request.client.host if request.client else None,
        )

        response = await call_next(request)

        logger.info(
            "response method=%s path=%s status=%s duration_ms=%.1f",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )
        return response
