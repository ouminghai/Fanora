"""Cross-cutting request logging and metrics middleware."""

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import bind_log_context, clear_log_context, logger
from app.core.metrics import http_request_duration_seconds, http_requests_total


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        clear_log_context()
        started_at = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            endpoint = getattr(route, "path", request.url.path)
            duration = time.perf_counter() - started_at
            bind_log_context(method=request.method, endpoint=endpoint)
            http_requests_total.labels(request.method, endpoint, str(status_code)).inc()
            http_request_duration_seconds.labels(request.method, endpoint).observe(duration)
            logger.info("request_completed", status_code=status_code, duration_ms=round(duration * 1000, 2))
            clear_log_context()
