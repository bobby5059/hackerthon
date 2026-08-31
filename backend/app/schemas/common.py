"""공통 스키마 — PageMeta, 에러 응답, 에러 코드, 페이지네이션 쿼리 (계약 §1.3/§1.4/§3)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """표준 에러 코드 (계약 §1.3)."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    ORDER_EMPTY = "ORDER_EMPTY"
    TOTAL_MISMATCH = "TOTAL_MISMATCH"
    SESSION_CLOSED = "SESSION_CLOSED"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    """표준 에러 응답 형태 (계약 §1.3)."""

    error: ErrorBody


class PageMeta(BaseModel):
    page: int
    size: int
    total: int


class Pagination(BaseModel):
    """페이지네이션 쿼리 (계약 §1.4, BR-VAL-06). page>=1, size 1..100."""

    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size
