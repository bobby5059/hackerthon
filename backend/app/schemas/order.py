"""주문 스키마 — 입력/응답/목록/상태변경/삭제 (계약 §2.3, §3.2, 입력 상한 Q9)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.db.models import ORDER_STATUSES
from app.schemas.common import PageMeta

# 입력 상한 (Q9, BR-VAL-02)
MAX_ITEMS_PER_ORDER = 100
MAX_QTY_PER_ITEM = 999


class OrderItemInput(BaseModel):
    menu_id: str = Field(min_length=1, max_length=64)
    quantity: int = Field(ge=1, le=MAX_QTY_PER_ITEM)


class CreateOrderRequest(BaseModel):
    # store/table/session은 토큰에서 도출(요청 본문 무시, BR-ORD-02)
    items: list[OrderItemInput] = Field(min_length=1, max_length=MAX_ITEMS_PER_ORDER)


class OrderItem(BaseModel):
    menu_id: str
    name: str  # 주문 시점 스냅샷
    unit_price: int  # 주문 시점 스냅샷
    quantity: int
    line_amount: int


class Order(BaseModel):
    order_id: str
    order_number: str
    table_id: str
    session_id: str
    status: str
    items: list[OrderItem]
    total_amount: int
    created_at: str


class OrdersListResponse(BaseModel):
    items: list[Order]
    page_meta: PageMeta
    server_time: str  # 폴링 정합(계약 §5.1)


class StatusUpdateRequest(BaseModel):
    status: str = Field(pattern="^(PENDING|PREPARING|COMPLETED)$")

    @staticmethod
    def allowed() -> tuple[str, ...]:
        return ORDER_STATUSES


class DeleteResult(BaseModel):
    deleted_order_id: str
    table_id: str
    table_total_amount: int
