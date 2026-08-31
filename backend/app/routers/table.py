"""TableRouter — 테이블 설정/대시보드/이용 완료 (🔑A, 계약 §2.4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.table import CompleteResult, DashboardResponse, SetupRequest, SetupResponse
from app.security.deps import Principal, require_admin
from app.services import session_service

router = APIRouter(prefix="/api/tables", tags=["table"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    table_id: str | None = Query(default=None),
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    """테이블별 대시보드 (폴링, A2-S1/S2/S5). 🔑A."""
    return session_service.get_dashboard(db, principal, table_id)


@router.post("/{table_id}/setup", response_model=SetupResponse)
def setup_table(
    table_id: str,
    req: SetupRequest,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SetupResponse:
    """테이블 초기 설정 (A3-S1). 🔑A."""
    return session_service.setup_table(db, principal, table_id, req.table_no, req.table_password)


@router.post("/{table_id}/complete", response_model=CompleteResult)
def complete(
    table_id: str,
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CompleteResult:
    """이용 완료/세션 종료 (A3-S3). 🔑A."""
    return session_service.complete_session(db, principal, table_id)
