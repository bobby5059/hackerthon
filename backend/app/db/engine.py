"""SQLAlchemy 엔진 + connect 훅 PRAGMA (C9, NFR §2).

- 단일 전역 엔진 + QueuePool(기본).
- 모든 신규 물리 연결에 PRAGMA 적용: WAL / foreign_keys=ON / busy_timeout.
- `check_same_thread=False`로 동기 라우트 스레드풀 사용 허용(요청-스레드 격리는 세션 단위).
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import get_settings


def _build_engine() -> Engine:
    settings = get_settings()
    engine = create_engine(
        f"sqlite:///{settings.db_path}",
        connect_args={"check_same_thread": False},
        # QueuePool이 기본. 다중 스레드 병행 읽기 지원(폴링).
        future=True,
        echo=False,
    )

    busy_timeout_ms = settings.db_busy_timeout_ms

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):  # type: ignore[no-untyped-def]
        """모든 신규 물리 연결에 PRAGMA 적용 (NFR-BE-R-05)."""
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")  # 다중 읽기 동시성(폴링)
            cursor.execute("PRAGMA foreign_keys=ON")  # FK 무결성 강제(연결마다 필수)
            cursor.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")  # 잠금 대기
        finally:
            cursor.close()

    return engine


# 전역 엔진 + 세션팩토리
engine: Engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def reset_engine(db_path: str | None = None) -> None:
    """테스트용: 엔진/세션팩토리 재생성(임시 DB 경로 주입 후 호출)."""
    global engine, SessionLocal
    engine.dispose()
    engine = _build_engine()
    SessionLocal.configure(bind=engine)
