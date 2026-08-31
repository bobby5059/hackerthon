"""도메인 예외 계층 + 전역 에러 핸들러 (C1, NFR §4, 계약 §1.3).

- 각 AppError가 (http_status, error_code)를 보유 → 전역 핸들러가 표준 응답으로 변환.
- 표준 응답: {"error": {"code", "message", "request_id"}}. 내부 스택/경로/DB 미노출(SECURITY-15/09).
- request_id는 contextvar에서 읽어 응답에 포함.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.logging_config import get_logger, request_id_ctx
from app.schemas.common import ErrorCode


class AppError(Exception):
    """도메인 예외 기반 클래스. http_status/error_code/기본 메시지 보유."""

    http_status: int = 500
    error_code: str = ErrorCode.INTERNAL_ERROR.value
    default_message: str = "처리 중 오류가 발생했습니다."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class ValidationError(AppError):
    http_status = 400
    error_code = ErrorCode.VALIDATION_ERROR.value
    default_message = "입력값이 유효하지 않습니다."


class OrderEmptyError(AppError):
    http_status = 400
    error_code = ErrorCode.ORDER_EMPTY.value
    default_message = "장바구니가 비어 있어 주문을 생성할 수 없습니다."


class AuthError(AppError):
    """토큰 없음/무효 → 401 UNAUTHORIZED (일반화)."""

    http_status = 401
    error_code = ErrorCode.UNAUTHORIZED.value
    default_message = "인증에 실패했습니다."


class TokenExpiredError(AppError):
    http_status = 401
    error_code = ErrorCode.TOKEN_EXPIRED.value
    default_message = "세션이 만료되었습니다. 관리자 재설정이 필요합니다."


class ForbiddenError(AppError):
    http_status = 403
    error_code = ErrorCode.FORBIDDEN.value
    default_message = "권한이 없습니다."


class NotFoundError(AppError):
    http_status = 404
    error_code = ErrorCode.NOT_FOUND.value
    default_message = "리소스를 찾을 수 없습니다."


class ConflictError(AppError):
    """세션 상태 충돌 → 409 SESSION_CLOSED (재-setup/미완료/종료 세션)."""

    http_status = 409
    error_code = ErrorCode.SESSION_CLOSED.value
    default_message = "세션 상태가 유효하지 않습니다."


class TotalMismatchError(AppError):
    http_status = 422
    error_code = ErrorCode.TOTAL_MISMATCH.value
    default_message = "총액이 일치하지 않습니다."


class SemanticValidationError(AppError):
    """의미 검증 실패(유효하지 않은 menu_id 등) → 422 VALIDATION_ERROR."""

    http_status = 422
    error_code = ErrorCode.VALIDATION_ERROR.value
    default_message = "요청을 처리할 수 없습니다."


class RateLimitedError(AppError):
    http_status = 429
    error_code = ErrorCode.RATE_LIMITED.value
    default_message = "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요."


def _error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id_ctx.get(),
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """전역 예외 핸들러 3종 등록 (§4)."""
    logger = get_logger("table-order.error")

    @app.exception_handler(AppError)
    async def _handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        # 4xx는 정보 로깅, 5xx는 error 로깅
        if exc.http_status >= 500:
            logger.error(exc.message)
        else:
            logger.info(f"{exc.error_code}: {exc.message}")
        return _error_response(exc.http_status, exc.error_code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info(f"VALIDATION_ERROR: {exc.errors()!r}")
        return _error_response(
            400, ErrorCode.VALIDATION_ERROR.value, "입력값이 유효하지 않습니다."
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        # 상세는 서버 로그에만(스택 미노출, SECURITY-15)
        logger.error("Unhandled exception", exc_info=exc)
        return _error_response(
            500, ErrorCode.INTERNAL_ERROR.value, "처리 중 오류가 발생했습니다."
        )
