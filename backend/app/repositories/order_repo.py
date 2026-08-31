"""Order/OrderItem 리포지토리 — 파라미터화 쿼리 (SECURITY-05).

채번 MAX+1, 총액 합계(soft-delete 제외), soft-delete, 세션 목록/최근 N건/상태 카운트.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Order, OrderItem


def max_order_seq(db: Session, store_id: str, order_date: str) -> int:
    """매장·일자 기준 최대 순번(없으면 0). soft-delete 포함(순번 재사용 방지, BR-NUM-03)."""
    result = db.scalar(
        select(func.max(Order.order_seq)).where(
            Order.store_id == store_id,
            Order.order_date == order_date,
        )
    )
    return int(result) if result is not None else 0


def insert_order(db: Session, order: Order) -> None:
    """order + items(관계) 삽입. 호출부 트랜잭션에 참여."""
    db.add(order)


def get(db: Session, store_id: str, order_id: str, include_deleted: bool = False) -> Order | None:
    stmt = select(Order).where(Order.store_id == store_id, Order.order_id == order_id)
    if not include_deleted:
        stmt = stmt.where(Order.deleted_at.is_(None))
    return db.scalar(stmt)


def update_status(order: Order, status: str) -> None:
    order.status = status


def soft_delete(order: Order, deleted_at_iso: str, deleted_by: str) -> None:
    order.deleted_at = deleted_at_iso
    order.deleted_by = deleted_by


def list_by_session(
    db: Session,
    store_id: str,
    session_id: str,
    *,
    offset: int = 0,
    limit: int | None = None,
) -> list[Order]:
    """현재 세션 유효 주문(soft-delete 제외), created_at 오름차순(계약 §2.3)."""
    stmt = (
        select(Order)
        .where(
            Order.store_id == store_id,
            Order.session_id == session_id,
            Order.deleted_at.is_(None),
        )
        .order_by(Order.created_at.asc(), Order.order_seq.asc())
    )
    if limit is not None:
        stmt = stmt.offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


def count_by_session(db: Session, store_id: str, session_id: str) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.store_id == store_id,
                Order.session_id == session_id,
                Order.deleted_at.is_(None),
            )
        )
        or 0
    )


def sum_table_total(db: Session, store_id: str, session_id: str) -> int:
    """활성 세션의 유효 주문 Σ total_amount(soft-delete 제외, BR-DASH-02)."""
    result = db.scalar(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            Order.store_id == store_id,
            Order.session_id == session_id,
            Order.deleted_at.is_(None),
        )
    )
    return int(result or 0)


def recent_orders(db: Session, store_id: str, session_id: str, limit: int = 3) -> list[Order]:
    """최근 N건(created_at 내림차순, soft-delete 제외, BR-DASH-01)."""
    return list(
        db.scalars(
            select(Order)
            .where(
                Order.store_id == store_id,
                Order.session_id == session_id,
                Order.deleted_at.is_(None),
            )
            .order_by(Order.created_at.desc(), Order.order_seq.desc())
            .limit(limit)
        ).all()
    )


def count_pending(db: Session, store_id: str, session_id: str) -> int:
    """PENDING/PREPARING 주문 수(soft-delete 제외, BR-SESS-04)."""
    return int(
        db.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.store_id == store_id,
                Order.session_id == session_id,
                Order.deleted_at.is_(None),
                Order.status.in_(("PENDING", "PREPARING")),
            )
        )
        or 0
    )
