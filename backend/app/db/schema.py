"""스키마 생성 — 기동 시 create_all (Q4=A, Alembic 없음).

고정 스키마 단일 매장 MVP. 프로덕션/스키마 진화 필요 시 Alembic 도입으로 확장.
"""

from __future__ import annotations

from sqlalchemy import Engine

from app.db.engine import engine as default_engine
from app.db.models import Base


def create_all(engine: Engine | None = None) -> None:
    """모든 테이블 생성(없을 때만). 기동 시 1회 호출."""
    Base.metadata.create_all(engine or default_engine)
