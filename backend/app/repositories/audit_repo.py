"""감사 로그 기록 헬퍼 (BR-AUD-01, SECURITY-13).

중요 변경(주문 삭제·상태변경·세션 종료·테이블 설정)을 append-only로 기록.
민감정보(비밀번호/토큰/PIN)는 before/after에 담지 않는다.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLog
from app.logging_config import request_id_ctx
from app.repositories.ids import new_id
from app.time_utils import now_kst, to_iso


def record_audit(
    db: Session,
    *,
    store_id: str,
    actor: str,
    action: str,
    target_type: str,
    target_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    """감사 로그 1건 추가(호출부 트랜잭션에 참여)."""
    db.add(
        AuditLog(
            audit_id=new_id("audit"),
            store_id=store_id,
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before_value=json.dumps(before, ensure_ascii=False) if before is not None else None,
            after_value=json.dumps(after, ensure_ascii=False) if after is not None else None,
            request_id=request_id_ctx.get(),
            created_at=to_iso(now_kst()),
        )
    )
