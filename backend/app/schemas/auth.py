"""인증 스키마 — 로그인 요청/응답 (계약 §2.1, §4)."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── 관리자 로그인 (A1-S1) ──
class AdminLoginRequest(BaseModel):
    store_id: str = Field(min_length=1, max_length=64)
    username: str = Field(min_length=1, max_length=50)  # BR-VAL-04
    password: str = Field(min_length=1, max_length=200)


class StoreInfo(BaseModel):
    store_id: str
    name: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str  # ISO8601 +09:00
    store: StoreInfo


# ── 테이블 자동 로그인 (C1-S1) ──
class TableLoginRequest(BaseModel):
    store_id: str = Field(min_length=1, max_length=64)
    table_no: str = Field(min_length=1, max_length=20)  # BR-VAL-03
    table_password: str = Field(min_length=1, max_length=20)


class TableInfo(BaseModel):
    table_id: str
    table_no: str


class SessionInfo(BaseModel):
    session_id: str
    started_at: str


class TableLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    table: TableInfo
    session: SessionInfo
