"""request_id 미들웨어 (C2, NFR §7, SECURITY-07).

요청마다 UUID 생성 → contextvar set → 로깅/에러 응답/응답 헤더에 전파.
동기 라우트는 스레드풀에서 실행되지만, contextvar는 요청 진입 시 set 되어
Starlette가 컨텍스트를 복사·전파하므로 워커 스레드에서도 값이 유지된다.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging_config import request_id_ctx


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        try:
            response: Response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-Id"] = request_id
        return response
