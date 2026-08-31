"""JWT 발급/검증 — PyJWT HS256 (FD §2.3, 계약 §4).

- issue_jwt: iss/iat/exp 세팅, HS256 서명. 서명키는 env(하드코딩 금지, BR-AUTH-06).
- verify_jwt: 서명·exp·iss 서버측 검증(매 요청, BR-AUTHZ-06). 민감정보 미포함.
- 만료 → TokenExpiredError, 그 외 무효 → AuthError.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import jwt

from app.config import get_settings
from app.errors import AuthError, TokenExpiredError
from app.time_utils import now_kst, to_iso

_ALGO = "HS256"


def issue_jwt(claims: dict[str, Any], ttl: timedelta) -> tuple[str, str]:
    """클레임 + TTL로 토큰 발급. (token, expires_at_iso) 반환.

    claims에는 계약 §4 필드(sub, typ, store_id, ...)를 담고, iss/iat/exp는 여기서 세팅.
    """
    settings = get_settings()
    iat = now_kst()
    exp = iat + ttl
    payload: dict[str, Any] = {
        **claims,
        "iss": settings.jwt_issuer,
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=_ALGO)
    return token, to_iso(exp)


def verify_jwt(token: str) -> dict[str, Any]:
    """토큰 검증 → 클레임 반환. 실패 시 AuthError/TokenExpiredError."""
    settings = get_settings()
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[_ALGO],
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iss"]},
        )
        return claims
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError() from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError() from exc
