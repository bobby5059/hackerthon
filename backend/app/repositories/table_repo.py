"""Table/TableSession 리포지토리 — 파라미터화 쿼리 (SECURITY-05)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Table, TableSession
from app.repositories.ids import new_id
from app.time_utils import now_kst, to_iso


def get_table_by_id(db: Session, store_id: str, table_id: str) -> Table | None:
    return db.scalar(
        select(Table).where(Table.store_id == store_id, Table.table_id == table_id)
    )


def get_table_by_no(db: Session, store_id: str, table_no: str) -> Table | None:
    return db.scalar(
        select(Table).where(Table.store_id == store_id, Table.table_no == table_no)
    )


def list_tables(db: Session, store_id: str, table_id: str | None = None) -> list[Table]:
    stmt = select(Table).where(Table.store_id == store_id)
    if table_id is not None:
        stmt = stmt.where(Table.table_id == table_id)
    return list(db.scalars(stmt).all())


def upsert_table(
    db: Session,
    *,
    store_id: str,
    table_no: str,
    table_password_hash: str,
) -> Table:
    """테이블 생성 또는 갱신(비번 해시·auto_login 활성). 호출부 트랜잭션에 참여."""
    table = get_table_by_no(db, store_id, table_no)
    if table is None:
        table = Table(
            table_id=new_id("tbl"),
            store_id=store_id,
            table_no=table_no,
            table_password_hash=table_password_hash,
            auto_login_enabled=1,
            created_at=to_iso(now_kst()),
        )
        db.add(table)
    else:
        table.table_password_hash = table_password_hash
        table.auto_login_enabled = 1
    return table


def get_active_session(db: Session, store_id: str, table_id: str) -> TableSession | None:
    return db.scalar(
        select(TableSession).where(
            TableSession.store_id == store_id,
            TableSession.table_id == table_id,
            TableSession.status == "ACTIVE",
        )
    )


def get_session(db: Session, store_id: str, session_id: str) -> TableSession | None:
    return db.scalar(
        select(TableSession).where(
            TableSession.store_id == store_id,
            TableSession.session_id == session_id,
        )
    )


def create_session(
    db: Session,
    *,
    store_id: str,
    table_id: str,
    started_at_iso: str,
    expires_at_iso: str,
) -> TableSession:
    session = TableSession(
        session_id=new_id("sess"),
        store_id=store_id,
        table_id=table_id,
        status="ACTIVE",
        started_at=started_at_iso,
        expires_at=expires_at_iso,
    )
    db.add(session)
    return session


def mark_session_status(
    session: TableSession,
    status: str,
    completed_at_iso: str | None = None,
) -> None:
    session.status = status
    if completed_at_iso is not None:
        session.completed_at = completed_at_iso
