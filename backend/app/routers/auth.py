"""AuthRouter — 로그인 (공개 🔓, 계약 §2.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import (
    AdminLoginRequest,
    AdminLoginResponse,
    TableLoginRequest,
    TableLoginResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/admin/login", response_model=AdminLoginResponse)
def admin_login(req: AdminLoginRequest, db: Session = Depends(get_db)) -> AdminLoginResponse:
    """관리자 로그인 (A1-S1). 공개 엔드포인트."""
    result = auth_service.authenticate_admin(db, req.store_id, req.username, req.password)
    return AdminLoginResponse(**result)


@router.post("/table/login", response_model=TableLoginResponse)
def table_login(req: TableLoginRequest, db: Session = Depends(get_db)) -> TableLoginResponse:
    """테이블 자동 로그인 (C1-S1). 공개 엔드포인트."""
    result = auth_service.authenticate_table(db, req.store_id, req.table_no, req.table_password)
    return TableLoginResponse(**result)
