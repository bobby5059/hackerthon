"""OrderHistory 리포지토리 — 이력 이관/조회 (SECURITY-05)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import OrderHistory


def insert_history(db: Session, history: OrderHistory) -> None:
    """history + items(관계) 삽입. 호출부 트랜잭션에 참여."""
    db.add(history)


def query(
    db: Session,
    store_id: str,
    *,
    table_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> list[OrderHistory]:
    """completed_at 역순(계약 §2.5). 날짜 필터는 completed_at 기준(BR-HIST-02)."""
    stmt = select(OrderHistory).where(OrderHistory.store_id == store_id)
    if table_id is not None:
        stmt = stmt.where(OrderHistory.table_id == table_id)
    if date_from is not None:
        stmt = stmt.where(OrderHistory.completed_at >= date_from)
    if date_to is not None:
        # date_to는 해당 일자 끝까지 포함(YYYY-MM-DD + 'T23:59:59...' 보다 단순히 다음날 미만)
        stmt = stmt.where(OrderHistory.completed_at <= f"{date_to}T23:59:59.999999+09:00")
    stmt = stmt.order_by(OrderHistory.completed_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


def count(
    db: Session,
    store_id: str,
    *,
    table_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> int:
    stmt = select(func.count()).select_from(OrderHistory).where(OrderHistory.store_id == store_id)
    if table_id is not None:
        stmt = stmt.where(OrderHistory.table_id == table_id)
    if date_from is not None:
        stmt = stmt.where(OrderHistory.completed_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(OrderHistory.completed_at <= f"{date_to}T23:59:59.999999+09:00")
    return int(db.scalar(stmt) or 0)
