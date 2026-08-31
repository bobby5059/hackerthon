"""MenuRouter — 메뉴 목록/상세 (🔑T/A, 계약 §2.2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.menu import Menu, MenuListResponse
from app.security.deps import Principal, require_any
from app.services import menu_service

router = APIRouter(prefix="/api/menu", tags=["menu"])


@router.get("", response_model=MenuListResponse)
def list_menu(
    principal: Principal = Depends(require_any),
    db: Session = Depends(get_db),
) -> MenuListResponse:
    """카테고리 + 메뉴 목록 (C2-S1)."""
    return menu_service.list_menu(db, principal.store_id)


@router.get("/{menu_id}", response_model=Menu)
def get_menu(
    menu_id: str,
    principal: Principal = Depends(require_any),
    db: Session = Depends(get_db),
) -> Menu:
    """메뉴 상세 (C2-S2)."""
    return menu_service.get_menu(db, principal.store_id, menu_id)
