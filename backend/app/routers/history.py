"""HistoryRouter — 과거 주문 내역 (🔑A, 계약 §2.5)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.history import HistoryListResponse
from app.security.deps import Principal, require_admin
from app.services import history_service

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=HistoryListResponse)
def list_history(
    table_id: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> HistoryListResponse:
    """과거 주문 내역 (A3-S4). 🔑A. completed_at 역순."""
    return history_service.list_history(
        db,
        principal.store_id,
        table_id=table_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )
