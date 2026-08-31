"""요청/응답 구조화 로깅 미들웨어 (C3, NFR §7, SECURITY-03).

요청 메서드·경로·상태코드·소요시간을 JSON으로 기록. 본문은 로깅하지 않는다
(민감정보 노출 방지). request_id는 포맷터가 contextvar에서 자동 부착.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging_config import get_logger

_logger = get_logger("table-order.access")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        _logger.info(
            "request",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "elapsed_ms": elapsed_ms,
                }
            },
        )
        return response
