"""Store/AdminUser 리포지토리 — 파라미터화 쿼리 (SECURITY-05)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AdminUser, Store


def get_store(db: Session, store_id: str) -> Store | None:
    return db.scalar(select(Store).where(Store.store_id == store_id))


def get_admin(db: Session, store_id: str, username: str) -> AdminUser | None:
    return db.scalar(
        select(AdminUser).where(
            AdminUser.store_id == store_id,
            AdminUser.username == username,
        )
    )
