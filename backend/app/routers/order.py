"""OrderRouter — 주문 생성/목록/상태변경/삭제 (계약 §2.3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.order import (
    CreateOrderRequest,
    DeleteResult,
    Order,
    OrdersListResponse,
    StatusUpdateRequest,
)
from app.security.deps import Principal, require_admin, require_table
from app.services import order_service

router = APIRouter(prefix="/api/orders", tags=["order"])


@router.post("", response_model=Order, status_code=201)
def create_order(
    req: CreateOrderRequest,
    principal: Principal = Depends(require_table),
    db: Session = Depends(get_db),
) -> Order:
    """주문 생성 (C4-S1~S3). 🔑T. store/table/session은 토큰에서 도출."""
    return order_service.create_order(db, principal, req)


@router.get("", response_model=OrdersListResponse)
def list_orders(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(require_table),
    db: Session = Depends(get_db),
) -> OrdersListResponse:
    """현재 세션 주문 내역 (폴링, C5-S1/S2). 🔑T."""
    return order_service.list_session_orders(db, principal, page, size)


@router.patch("/{order_id}/status", response_model=Order)
def update_status(
    order_id: str,
    req: StatusUpdateRequest,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Order:
    """주문 상태 변경 (A2-S4). 🔑A."""
    return order_service.update_status(db, principal, order_id, req.status)


@router.delete("/{order_id}", response_model=DeleteResult)
def delete_order(
    order_id: str,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DeleteResult:
    """주문 직권 삭제 (A3-S2). 🔑A. soft-delete + 총액 재계산 + 감사."""
    return order_service.delete_order(db, principal, order_id)
