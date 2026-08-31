"""AuthService — 관리자/테이블 로그인 (FD §2, SECURITY-12).

- RateLimiter 선검사 → bcrypt 검증(존재 여부 무관 동일 경로) → LoginAttempt 감사 → JWT 발급.
- 실패는 일반화 401(사용자 열거 방지). 세션 만료/부재는 TOKEN_EXPIRED.
- 비밀번호는 로그/응답 노출 금지.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import AuthError, RateLimitedError, TokenExpiredError
from app.logging_config import security_event
from app.repositories import store_repo, table_repo
from app.repositories.ids import new_id
from app.security.hashing import verify_password
from app.security.jwt import issue_jwt
from app.security.ratelimit import login_rate_limiter
from app.time_utils import now_kst, parse_iso, to_iso


def _record_attempt(
    db: Session, *, store_id: str, principal: str, attempt_type: str, success: bool
) -> None:
    from app.db.models import LoginAttempt

    db.add(
        LoginAttempt(
            attempt_id=new_id("att"),
            store_id=store_id,
            principal=principal,
            attempt_type=attempt_type,
            success=1 if success else 0,
            attempted_at=to_iso(now_kst()),
        )
    )
    db.commit()


def authenticate_admin(db: Session, store_id: str, username: str, password: str) -> dict:
    """관리자 로그인 → AdminLoginResponse dict (계약 §2.1)."""
    key = login_rate_limiter.admin_key(store_id, username)
    if login_rate_limiter.is_locked(key):
        security_event("login_rate_limited", attempt_type="ADMIN", store_id=store_id)
        raise RateLimitedError()

    admin = store_repo.get_admin(db, store_id, username)
    ok = admin is not None and verify_password(password, admin.password_hash)

    _record_attempt(
        db, store_id=store_id, principal=username, attempt_type="ADMIN", success=ok
    )
    if not ok:
        login_rate_limiter.record_failure(key)
        security_event("login_failed", attempt_type="ADMIN", store_id=store_id)
        raise AuthError()  # 일반화 401

    login_rate_limiter.record_success(key)
    security_event("login_success", attempt_type="ADMIN", store_id=store_id)

    settings = get_settings()
    ttl = timedelta(hours=settings.admin_token_ttl_hours)
    claims = {
        "sub": f"admin:{username}",
        "typ": "admin",
        "store_id": store_id,
        "username": username,
    }
    token, expires_at = issue_jwt(claims, ttl)
    store = store_repo.get_store(db, store_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "store": {"store_id": store_id, "name": store.name if store else ""},
    }


def authenticate_table(db: Session, store_id: str, table_no: str, table_password: str) -> dict:
    """테이블 자동 로그인 → TableLoginResponse dict (계약 §2.1).

    유효 활성 세션이 있어야 토큰 발급. 세션 만료/부재 시 401 TOKEN_EXPIRED(관리자 재설정).
    """
    key = login_rate_limiter.table_key(store_id, table_no)
    if login_rate_limiter.is_locked(key):
        security_event("login_rate_limited", attempt_type="TABLE", store_id=store_id)
        raise RateLimitedError()

    table = table_repo.get_table_by_no(db, store_id, table_no)
    ok = (
        table is not None
        and table.auto_login_enabled == 1
        and table.table_password_hash is not None
        and verify_password(table_password, table.table_password_hash)
    )

    _record_attempt(
        db, store_id=store_id, principal=table_no, attempt_type="TABLE", success=ok
    )
    if not ok or table is None:
        login_rate_limiter.record_failure(key)
        security_event("login_failed", attempt_type="TABLE", store_id=store_id)
        raise AuthError()

    login_rate_limiter.record_success(key)

    # 활성 세션 확인 + 만료 검사(Q7=A)
    session = table_repo.get_active_session(db, store_id, table.table_id)
    if session is None:
        raise TokenExpiredError()
    now = now_kst()
    if now >= parse_iso(session.expires_at):
        table_repo.mark_session_status(session, "EXPIRED")
        db.commit()
        raise TokenExpiredError()

    security_event("login_success", attempt_type="TABLE", store_id=store_id)

    ttl = parse_iso(session.expires_at) - now  # 세션 잔여(≤16h)
    claims = {
        "sub": f"table:{table.table_id}",
        "typ": "table",
        "store_id": store_id,
        "table_id": table.table_id,
        "session_id": session.session_id,
    }
    token, expires_at = issue_jwt(claims, ttl)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "table": {"table_id": table.table_id, "table_no": table.table_no},
        "session": {"session_id": session.session_id, "started_at": session.started_at},
    }
