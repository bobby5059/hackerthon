"""TableSessionService — 테이블 설정/세션 시작/대시보드/이용 완료 (FD §5)."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import TableSession
from app.db.session import retry_on_write_conflict
from app.errors import ConflictError, NotFoundError
from app.repositories import order_repo, table_repo
from app.repositories.audit_repo import record_audit
from app.schemas.table import (
    CompleteResult,
    DashboardResponse,
    OrderPreview,
    SetupResponse,
    SetupSessionInfo,
    TableCard,
)
from app.security.deps import Principal
from app.security.hashing import hash_password
from app.services import history_service
from app.time_utils import now_kst, parse_iso, to_iso

SESSION_TTL = timedelta(hours=16)


def get_or_start_session(
    db: Session,
    store_id: str,
    table_id: str,
    *,
    token_session_id: str | None = None,
) -> TableSession:
    """활성 세션 조회 또는 첫 주문 시 신규 세션 시작 (FD §5.2).

    **주의**: 호출부(order_service.create_order)의 트랜잭션 내에서 실행된다.
    자체 트랜잭션을 열지 않고 세션 객체를 추가/반환한다.
    """
    session = table_repo.get_active_session(db, store_id, table_id)
    now = now_kst()

    if session is not None:
        if now >= parse_iso(session.expires_at):
            # 만료 처리(Q7=A) → 세션 없음으로 취급
            table_repo.mark_session_status(session, "EXPIRED")
            session = None
        else:
            # 토큰-세션 정합 검사(BR-SESS-02)
            if token_session_id is not None and token_session_id != session.session_id:
                raise ConflictError("세션이 유효하지 않습니다.")
            return session

    # 활성 세션 없음: 토큰이 특정(만료된) 세션에 묶여 있으면 신규 시작 불가
    if token_session_id is not None:
        raise ConflictError("세션이 종료되었습니다. 관리자 재설정이 필요합니다.")

    started = now
    expires = started + SESSION_TTL
    return table_repo.create_session(
        db,
        store_id=store_id,
        table_id=table_id,
        started_at_iso=to_iso(started),
        expires_at_iso=to_iso(expires),
    )


@retry_on_write_conflict
def setup_table(
    db: Session, principal: Principal, table_id: str, table_no: str, table_password: str
) -> SetupResponse:
    """테이블 초기 설정 [A3-S1]. 테이블 upsert + 세션 생성 (단일 트랜잭션).

    활성 세션이 있는 테이블 재-setup은 거부(Q5=C, 409).
    """
    store_id = principal.store_id
    with db.begin():
        # 활성 세션 존재 검사(BR-SESS-03) — table_no 기준
        existing = table_repo.get_table_by_no(db, store_id, table_no)
        if existing is not None:
            active = table_repo.get_active_session(db, store_id, existing.table_id)
            if active is not None and now_kst() < parse_iso(active.expires_at):
                raise ConflictError("활성 세션이 있어 재설정할 수 없습니다. 먼저 이용 완료해 주세요.")

        table = table_repo.upsert_table(
            db,
            store_id=store_id,
            table_no=table_no,
            table_password_hash=hash_password(table_password),
        )
        started = now_kst()
        expires = started + SESSION_TTL
        session = table_repo.create_session(
            db,
            store_id=store_id,
            table_id=table.table_id,
            started_at_iso=to_iso(started),
            expires_at_iso=to_iso(expires),
        )
        record_audit(
            db,
            store_id=store_id,
            actor=principal.username or "admin",
            action="TABLE_SETUP",
            target_type="Table",
            target_id=table.table_id,
            after={"table_no": table_no, "auto_login_enabled": True},
        )

    db.refresh(table)
    db.refresh(session)
    return SetupResponse(
        table_id=table.table_id,
        table_no=table.table_no,
        auto_login_enabled=bool(table.auto_login_enabled),
        session=SetupSessionInfo(
            session_id=session.session_id,
            started_at=session.started_at,
            expires_at=session.expires_at,
        ),
    )


def _item_summary(order) -> str:  # type: ignore[no-untyped-def]
    """대표 메뉴명 + 외 N건 (BR-DASH-01)."""
    items = order.items
    if not items:
        return ""
    first = items[0].name
    extra = len(items) - 1
    return f"{first} 외 {extra}건" if extra > 0 else first


def get_dashboard(db: Session, principal: Principal, table_filter: str | None) -> DashboardResponse:
    """테이블별 대시보드 (폴링, A2-S1/S2/S5)."""
    store_id = principal.store_id
    tables = table_repo.list_tables(db, store_id, table_id=table_filter)
    cards: list[TableCard] = []
    for table in tables:
        active = table_repo.get_active_session(db, store_id, table.table_id)
        if active is None or now_kst() >= parse_iso(active.expires_at):
            total = 0
            previews: list[OrderPreview] = []
        else:
            total = order_repo.sum_table_total(db, store_id, active.session_id)
            recent = order_repo.recent_orders(db, store_id, active.session_id, limit=3)
            previews = [
                OrderPreview(
                    order_id=o.order_id,
                    order_number=o.order_number,
                    created_at=o.created_at,
                    item_summary=_item_summary(o),
                    total_amount=o.total_amount,
                )
                for o in recent
            ]
        cards.append(
            TableCard(
                table_id=table.table_id,
                table_no=table.table_no,
                total_amount=total,
                recent_orders=previews,
                has_new=False,  # Q9=A: 서버 미계산이나 항상 false로 포함
            )
        )
    return DashboardResponse(tables=cards, server_time=to_iso(now_kst()))


@retry_on_write_conflict
def complete_session(db: Session, principal: Principal, table_id: str) -> CompleteResult:
    """이용 완료/세션 종료 [A3-S3]. 이력 이관 + 세션 종료 + 감사 (단일 원자 트랜잭션).

    미완료(PENDING/PREPARING) 주문 존재 시 완료 차단(Q2=B, 409).
    """
    store_id = principal.store_id
    with db.begin():
        session = table_repo.get_active_session(db, store_id, table_id)
        if session is None:
            raise NotFoundError("활성 세션을 찾을 수 없습니다.")

        pending = order_repo.count_pending(db, store_id, session.session_id)
        if pending > 0:
            raise ConflictError("미완료 주문이 있어 이용 완료할 수 없습니다. 상태를 먼저 정리해 주세요.")

        completed_at = to_iso(now_kst())
        archived = history_service.archive_session(
            db, store_id, session.session_id, completed_at
        )
        table_repo.mark_session_status(session, "COMPLETED", completed_at_iso=completed_at)
        record_audit(
            db,
            store_id=store_id,
            actor=principal.username or "admin",
            action="SESSION_COMPLETE",
            target_type="TableSession",
            target_id=session.session_id,
            after={"archived_order_count": archived, "completed_at": completed_at},
        )

    return CompleteResult(
        table_id=table_id,
        archived_order_count=archived,
        completed_at=completed_at,
        table_total_amount=0,
    )
