"""ID 생성 유틸 — 응답 ID는 문자열(계약 §1.1). 내부 PK는 접두어 + uuid4 hex."""

from __future__ import annotations

import uuid


def new_id(prefix: str) -> str:
    """`{prefix}-{uuid4hex}` 형태의 문자열 ID 생성."""
    return f"{prefix}-{uuid.uuid4().hex}"
