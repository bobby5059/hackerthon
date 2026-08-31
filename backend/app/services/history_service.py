"""HistoryService — 세션 이력 이관/조회 (FD §6)."""

from __future__ import annotations

import math

from sqlalchemy.orm import Session

from app.db.models import OrderHistory as HistoryModel
from app.db.models import OrderHistoryItem as HistoryItemModel
from app.repositories import history_repo, order_repo
from app.repositories.ids import new_id
from app.schemas.common import PageMeta
from app.schemas.history import HistoryEntry, HistoryListResponse
from app.schemas.order import OrderItem


def archive_session(db: Session, store_id: str, session_id: str, completed_at_iso: str) -> int:
    """유효 주문(soft-delete 제외)을 OrderHistory(+Item)로 스냅샷 이관.

    호출부(complete_session)의 트랜잭션에 참여(원자성). 반환: 이관 건수.
    """
    orders = order_repo.list_by_session(db, store_id, session_id)
    for order in orders:
        history = HistoryModel(
            history_id=new_id("hist"),
            store_id=store_id,
            table_id=order.table_id,
            session_id=session_id,
            order_id=order.order_id,
            order_number=order.order_number,
            total_amount=order.total_amount,
            status=order.status,
            created_at=order.created_at,
            completed_at=completed_at_iso,
            items=[
                HistoryItemModel(
                    history_item_id=new_id("hi"),
                    menu_id=i.menu_id,
                    name=i.name,
                    unit_price=i.unit_price,
                    quantity=i.quantity,
                    line_amount=i.line_amount,
                )
                for i in order.items
            ],
        )
        history_repo.insert_history(db, history)
    return len(orders)


def _to_entry(h: HistoryModel) -> HistoryEntry:
    return HistoryEntry(
        order_id=h.order_id,
        order_number=h.order_number,
        table_id=h.table_id,
        items=[
            OrderItem(
                menu_id=i.menu_id,
                name=i.name,
                unit_price=i.unit_price,
                quantity=i.quantity,
                line_amount=i.line_amount,
            )
            for i in h.items
        ],
        total_amount=h.total_amount,
        created_at=h.created_at,
        completed_at=h.completed_at,
    )


def list_history(
    db: Session,
    store_id: str,
    *,
    table_id: str | None,
    date_from: str | None,
    date_to: str | None,
    page: int,
    size: int,
) -> HistoryListResponse:
    """과거 주문 내역 [A3-S4]. completed_at 역순."""
    total = history_repo.count(
        db, store_id, table_id=table_id, date_from=date_from, date_to=date_to
    )
    offset = (page - 1) * size
    rows = history_repo.query(
        db,
        store_id,
        table_id=table_id,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=size,
    )
    return HistoryListResponse(
        items=[_to_entry(h) for h in rows],
        page_meta=PageMeta(page=page, size=size, total=total),
    )


def total_pages(total: int, size: int) -> int:
    return max(1, math.ceil(total / size)) if size else 1
