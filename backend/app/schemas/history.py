"""이력 스키마 — HistoryEntry, 목록 응답 (계약 §2.5, §3.2)."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import PageMeta
from app.schemas.order import OrderItem


class HistoryEntry(BaseModel):
    order_id: str
    order_number: str
    table_id: str
    items: list[OrderItem]
    total_amount: int
    created_at: str
    completed_at: str  # 이용 완료 시각


class HistoryListResponse(BaseModel):
    items: list[HistoryEntry]
    page_meta: PageMeta
