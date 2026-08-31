"""요청 단위 세션 (C10) + 쓰기 경합 재시도 헬퍼 (C11, NFR §1/§3).

- `get_db()`: FastAPI 의존성. 요청마다 세션 오픈 → try/finally close.
- `@retry_on_write_conflict`: SQLITE_BUSY/UNIQUE 위반 시 제한적 재시도(max 3, 10/20/40ms).
  멱등 재실행 가능한 쓰기(채번+삽입 등)에만 적용. 소진 시 전파 → 전역 핸들러가 500.
- 트랜잭션 경계는 Service 계층에서 `with session.begin()`으로 수행(부분 성공 금지, fail closed).
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable, Iterator
from typing import TypeVar

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.engine import SessionLocal

T = TypeVar("T")

# 재시도 정책 (logical-components §6)
MAX_RETRIES = 3
BACKOFF_SECONDS = (0.010, 0.020, 0.040)  # 10 / 20 / 40 ms


def get_db() -> Iterator[Session]:
    """요청 단위 세션 제공(요청 종료 시 반드시 close)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _is_write_conflict(exc: BaseException) -> bool:
    """SQLITE_BUSY(락 경합) 또는 database is locked 여부."""
    if isinstance(exc, OperationalError):
        msg = str(exc.orig).lower() if exc.orig else str(exc).lower()
        return "locked" in msg or "busy" in msg
    return False


def retry_on_write_conflict(func: Callable[..., T]) -> Callable[..., T]:
    """쓰기 경합 시 트랜잭션 전체를 재실행하는 데코레이터.

    데코레이트되는 함수는 **멱등 재실행 가능**해야 한다(채번은 재조회로 새 순번 확보).
    도메인 예외(AppError)는 재시도하지 않고 즉시 전파한다.
    """

    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> T:
        last_exc: BaseException | None = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except OperationalError as exc:  # noqa: PERF203
                if not _is_write_conflict(exc):
                    raise
                last_exc = exc
                if attempt < MAX_RETRIES - 1:
                    time.sleep(BACKOFF_SECONDS[attempt])
        # 재시도 소진 → 전파(전역 핸들러가 500 INTERNAL_ERROR, fail closed)
        assert last_exc is not None
        raise last_exc

    return wrapper
