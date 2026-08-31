"""비밀번호 해싱 — passlib[bcrypt] (BR-AUTH-01, SECURITY-12).

관리자 비밀번호(8자↑)·테이블 PIN(4~6자리) 모두 bcrypt로 해시 저장. 평문/로그 노출 금지.
"""

from __future__ import annotations

from passlib.context import CryptContext

from app.config import get_settings

_settings = get_settings()
_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=_settings.bcrypt_cost,
)


def hash_password(password: str) -> str:
    """bcrypt 해시 생성."""
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """bcrypt 검증. 해시가 None/빈 값이면 False(안전 실패)."""
    if not password_hash:
        return False
    try:
        return _pwd_context.verify(password, password_hash)
    except ValueError:
        return False
