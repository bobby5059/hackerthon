"""OrderService — 주문 생성/목록/상태변경/삭제 (FD §4).

트랜잭션 경계·채번 MAX+1·총액 서버 재검증·스냅샷·soft-delete·감사.
쓰기 트랜잭션은 retry_on_write_conflict로 감싼다(fail closed).
"""

from __future__ import annotations

import math

from sqlalchemy.orm import Session

from app.db.models import Order as OrderModel
from app.db.models import OrderItem as OrderItemModel
from app.db.session import retry_on_write_conflict
from app.errors import (
    ForbiddenError,
    NotFoundError,
    OrderEmptyError,
    SemanticValidationError,
)
from app.logging_config import get_logger
from app.repositories import menu_repo, order_repo
from app.repositories.audit_repo import record_audit
from app.repositories.ids import new_id
from app.schemas.common import PageMeta
from app.schemas.order import (
    CreateOrderRequest,
    DeleteResult,
    Order,
    OrderItem,
    OrdersListResponse,
)
from app.security.deps import Principal
from app.services import pricing
from app.services.order_number import format_order_number
from app.services.session_service import get_or_start_session
from app.time_utils import date_str, now_kst, to_iso, today_kst

_logger = get_logger("table-order.order")


def _to_order_schema(order: OrderModel) -> Order:
    items = [
        OrderItem(
            menu_id=i.menu_id,
            name=i.name,
            unit_price=i.unit_price,
            quantity=i.quantity,
            line_amount=i.line_amount,
        )
        for i in order.items
    ]
    return Order(
        order_id=order.order_id,
        order_number=order.order_number,
        table_id=order.table_id,
        session_id=order.session_id,
        status=order.status,
        items=items,
        total_amount=order.total_amount,
        created_at=order.created_at,
    )


@retry_on_write_conflict
def create_order(db: Session, principal: Principal, req: CreateOrderRequest) -> Order:
    """주문 생성 [C4-S1~S3]. 단일 트랜잭션(채번+삽입 원자적, fail closed)."""
    if not req.items:
        raise OrderEmptyError()  # BR-ORD-01 (스키마에서도 min_length=1)

    store_id = principal.store_id
    table_id = principal.table_id
    if table_id is None:
        raise ForbiddenError()

    with db.begin():
        # 세션 확보 + 토큰-세션 정합 검사(BR-SESS-02)
        session = get_or_start_session(db, store_id, table_id, token_session_id=principal.session_id)

        # 단가 조회 + 스냅샷 구성(서버 단가 사용, BR-ORD-04)
        item_models: list[OrderItemModel] = []
        line_amounts: list[int] = []
        for item in req.items:
            menu = menu_repo.get_menu(db, store_id, item.menu_id)
            if menu is None:
                raise SemanticValidationError("유효하지 않은 메뉴가 포함되어 있습니다.")
            la = pricing.line_amount(menu.price, item.quantity)
            line_amounts.append(la)
            item_models.append(
                OrderItemModel(
                    order_item_id=new_id("oi"),
                    menu_id=menu.menu_id,
                    name=menu.name,  # 스냅샷
                    unit_price=menu.price,  # 스냅샷
                    quantity=item.quantity,
                    line_amount=la,
                )
            )

        total = pricing.total_amount(line_amounts)  # 서버 재검증(클라 총액 신뢰 안 함)

        # 채번 MAX+1 (동일 트랜잭션 내, BR-NUM-02)
        order_date = today_kst()
        order_date_iso = order_date.isoformat()
        next_seq = order_repo.max_order_seq(db, store_id, order_date_iso) + 1
        order_number = format_order_number(store_id, date_str(order_date), next_seq)

        order = OrderModel(
            order_id=new_id("o"),
            store_id=store_id,
            table_id=table_id,
            session_id=session.session_id,
            order_number=order_number,
            order_seq=next_seq,
            order_date=order_date_iso,
            status="PENDING",
            total_amount=total,
            created_at=to_iso(now_kst()),
            items=item_models,
        )
        order_repo.insert_order(db, order)
        # with db.begin() 종료 시 commit (실패 시 rollback → 주문 미생성)

    db.refresh(order)
    return _to_order_schema(order)


def list_session_orders(
    db: Session, principal: Principal, page: int, size: int
) -> OrdersListResponse:
    """현재 세션 주문 내역 (폴링, C5-S1). soft-delete 제외, created_at 오름차순."""
    store_id = principal.store_id
    session_id = principal.session_id
    if session_id is None:
        raise ForbiddenError()

    total = order_repo.count_by_session(db, store_id, session_id)
    offset = (page - 1) * size
    rows = order_repo.list_by_session(db, store_id, session_id, offset=offset, limit=size)
    items = [_to_order_schema(o) for o in rows]
    return OrdersListResponse(
        items=items,
        page_meta=PageMeta(page=page, size=size, total=total),
        server_time=to_iso(now_kst()),
    )


@retry_on_write_conflict
def update_status(db: Session, principal: Principal, order_id: str, status: str) -> Order:
    """주문 상태 변경 [A2-S4]. 자유 전이(Q1=B) + 감사."""
    store_id = principal.store_id
    with db.begin():
        order = order_repo.get(db, store_id, order_id)
        if order is None:
            raise NotFoundError("주문을 찾을 수 없습니다.")  # 부재/타 매장 은닉
        old_status = order.status
        order_repo.update_status(order, status)
        record_audit(
            db,
            store_id=store_id,
            actor=principal.username or "admin",
            action="ORDER_STATUS_CHANGE",
            target_type="Order",
            target_id=order_id,
            before={"status": old_status},
            after={"status": status},
        )
    db.refresh(order)
    return _to_order_schema(order)


@retry_on_write_conflict
def delete_order(db: Session, principal: Principal, order_id: str) -> DeleteResult:
    """주문 직권 삭제 [A3-S2]. soft-delete + 총액 재계산 + 감사 (단일 트랜잭션)."""
    store_id = principal.store_id
    actor = principal.username or "admin"
    with db.begin():
        order = order_repo.get(db, store_id, order_id)
        if order is None:
            raise NotFoundError("주문을 찾을 수 없습니다.")
        table_id = order.table_id
        session_id = order.session_id
        before = {
            "order_number": order.order_number,
            "status": order.status,
            "total_amount": order.total_amount,
        }
        order_repo.soft_delete(order, deleted_at_iso=to_iso(now_kst()), deleted_by=actor)
        record_audit(
            db,
            store_id=store_id,
            actor=actor,
            action="ORDER_DELETE",
            target_type="Order",
            target_id=order_id,
            before=before,
            after={"deleted": True},
        )
        # 총액 재계산(현재 세션 유효 주문 Σ, soft-delete 제외)
        table_total = order_repo.sum_table_total(db, store_id, session_id)

    return DeleteResult(
        deleted_order_id=order_id,
        table_id=table_id,
        table_total_amount=table_total,
    )


def total_pages(total: int, size: int) -> int:
    """페이지 총 수(참고용)."""
    return max(1, math.ceil(total / size)) if size else 1
