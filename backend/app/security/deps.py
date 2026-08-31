"""인증/인가 의존성 체인 (C7, NFR §5, SECURITY-08, BR-AUTHZ).

get_claims → require_admin/require_table → get_store_scope
- deny-by-default: 보호 라우트는 인증 의존성 필수. 공개 라우트(로그인 2종)만 예외.
- typ 분리: 관리자/테이블 토큰 혼용 시 403 FORBIDDEN.
- store 스코프 주입(테넌트 격리). 객체 소유권(IDOR) 재검증은 Service 계층.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Request

from app.errors import AuthError, ForbiddenError
from app.logging_config import security_event
from app.security.jwt import verify_jwt


@dataclass(frozen=True)
class Principal:
    """검증된 요청 주체(계약 §4 클레임 기반)."""

    typ: str  # "admin" | "table"
    store_id: str
    username: str | None = None
    table_id: str | None = None
    session_id: str | None = None
    raw: dict[str, Any] | None = None


def _extract_bearer(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise AuthError("인증 토큰이 필요합니다.")
    token = auth[len("Bearer ") :].strip()
    if not token:
        raise AuthError("인증 토큰이 필요합니다.")
    return token


def get_claims(request: Request) -> Principal:
    """Bearer 파싱 + JWT 검증(서명/exp/iss) → Principal. 매 요청 수행(BR-AUTHZ-06)."""
    token = _extract_bearer(request)
    claims = verify_jwt(token)
    typ = claims.get("typ")
    store_id = claims.get("store_id")
    if typ not in ("admin", "table") or not store_id:
        raise AuthError()
    return Principal(
        typ=typ,
        store_id=store_id,
        username=claims.get("username"),
        table_id=claims.get("table_id"),
        session_id=claims.get("session_id"),
        raw=claims,
    )


def require_admin(principal: Principal = Depends(get_claims)) -> Principal:
    """관리자 토큰 전용(🔑A). typ 불일치 → 403 (BR-AUTHZ-02)."""
    if principal.typ != "admin":
        security_event("authz_denied", reason="typ_mismatch", required="admin", got=principal.typ)
        raise ForbiddenError()
    return principal


def require_table(principal: Principal = Depends(get_claims)) -> Principal:
    """테이블 토큰 전용(🔑T). typ 불일치 → 403."""
    if principal.typ != "table":
        security_event("authz_denied", reason="typ_mismatch", required="table", got=principal.typ)
        raise ForbiddenError()
    return principal


def require_any(principal: Principal = Depends(get_claims)) -> Principal:
    """관리자 또는 테이블(🔑T/A) — 메뉴 조회 등 공용 보호 라우트."""
    return principal
