"""MenuService — 메뉴 목록/상세 (FD §3)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.repositories import menu_repo
from app.schemas.menu import Category, Menu, MenuListResponse


def _to_menu(m) -> Menu:  # type: ignore[no-untyped-def]
    return Menu(
        menu_id=m.menu_id,
        category_id=m.category_id,
        name=m.name,
        price=m.price,
        description=m.description,
        image_url=m.image_url,
    )


def list_menu(db: Session, store_id: str) -> MenuListResponse:
    categories = [
        Category(category_id=c.category_id, name=c.name, display_order=c.display_order)
        for c in menu_repo.list_categories(db, store_id)
    ]
    menus = [_to_menu(m) for m in menu_repo.list_menus(db, store_id)]
    return MenuListResponse(categories=categories, menus=menus)


def get_menu(db: Session, store_id: str, menu_id: str) -> Menu:
    m = menu_repo.get_menu(db, store_id, menu_id)
    if m is None:
        raise NotFoundError("메뉴를 찾을 수 없습니다.")  # 소유권 없어도 404 은닉
    return _to_menu(m)
