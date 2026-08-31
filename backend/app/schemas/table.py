"""테이블/세션 스키마 — setup/complete/dashboard, TableCard, OrderPreview (계약 §2.4, §3.2)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.schemas.order import OrderItem


# ── 테이블 초기 설정 (A3-S1) ──
class SetupRequest(BaseModel):
    table_no: str = Field(min_length=1, max_length=20)  # BR-VAL-03
    table_password: str = Field(min_length=4, max_length=6)  # 4~6자리 숫자 PIN (Q4=A)

    @field_validator("table_password")
    @classmethod
    def _digits_only(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("table_password must be 4-6 numeric digits")
        return v


class SetupSessionInfo(BaseModel):
    session_id: str
    started_at: str
    expires_at: str


class SetupResponse(BaseModel):
    table_id: str
    table_no: str
    auto_login_enabled: bool
    session: SetupSessionInfo


# ── 대시보드 (A2-S1/S2/S5) ──
class OrderPreview(BaseModel):
    order_id: str
    order_number: str
    created_at: str
    item_summary: str  # "김치찌개 외 2건"
    total_amount: int


class TableCard(BaseModel):
    table_id: str
    table_no: str
    total_amount: int
    recent_orders: list[OrderPreview]
    has_new: bool = False  # Q9=A: 서버 미계산이나 항상 false로 포함(생략 금지)


class DashboardResponse(BaseModel):
    tables: list[TableCard]
    server_time: str


# ── 이용 완료 (A3-S3) ──
class CompleteResult(BaseModel):
    table_id: str
    archived_order_count: int
    completed_at: str
    table_total_amount: int  # 0 리셋


# 참조 표준화(선형 import 방지용 re-export)
__all__ = [
    "SetupRequest",
    "SetupResponse",
    "SetupSessionInfo",
    "OrderPreview",
    "TableCard",
    "DashboardResponse",
    "CompleteResult",
    "OrderItem",
]
