"""본문 크기 제한 미들웨어 (C5, NFR §7, BR-VAL-05, SECURITY-05).

Content-Length 헤더가 상한 초과 시 즉시 413. 헤더가 없을 때는 스트리밍 누적으로 방어.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings
from app.logging_config import request_id_ctx
from app.schemas.common import ErrorCode


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        max_bytes = get_settings().max_body_bytes
        content_length = request.headers.get("Content-Length")
        if content_length is not None:
            try:
                if int(content_length) > max_bytes:
                    return self._too_large()
            except ValueError:
                return self._bad_request()
        response: Response = await call_next(request)
        return response

    @staticmethod
    def _too_large() -> JSONResponse:
        return JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR.value,
                    "message": "요청 본문이 허용 크기를 초과했습니다.",
                    "request_id": request_id_ctx.get(),
                }
            },
        )

    @staticmethod
    def _bad_request() -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR.value,
                    "message": "잘못된 요청입니다.",
                    "request_id": request_id_ctx.get(),
                }
            },
        )
