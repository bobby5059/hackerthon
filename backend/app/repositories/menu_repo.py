"""Category/Menu 리포지토리 — 파라미터화 쿼리 (SECURITY-05)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Category, Menu


def list_categories(db: Session, store_id: str) -> list[Category]:
    return list(
        db.scalars(
            select(Category)
            .where(Category.store_id == store_id)
            .order_by(Category.display_order.asc())
        ).all()
    )


def list_menus(db: Session, store_id: str) -> list[Menu]:
    return list(db.scalars(select(Menu).where(Menu.store_id == store_id)).all())


def get_menu(db: Session, store_id: str, menu_id: str) -> Menu | None:
    return db.scalar(
        select(Menu).where(Menu.store_id == store_id, Menu.menu_id == menu_id)
    )
