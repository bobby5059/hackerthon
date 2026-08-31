"""메뉴 스키마 — Category, Menu (계약 §3.2). 가용성 필드 없음(Q10=A)."""

from __future__ import annotations

from pydantic import BaseModel


class Category(BaseModel):
    category_id: str
    name: str
    display_order: int


class Menu(BaseModel):
    menu_id: str
    category_id: str
    name: str
    price: int  # 정수 KRW
    description: str | None = None
    image_url: str | None = None


class MenuListResponse(BaseModel):
    categories: list[Category]
    menus: list[Menu]
