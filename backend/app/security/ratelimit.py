"""로그인 rate limiter — 인메모리 슬라이딩 윈도우 (C8, NFR §6, SECURITY-12).

- 키: {scope}:{store_id}:{identifier} (ADMIN:store:username / TABLE:store:table_no)
- 윈도우 내 실패 >= MAX → 429 + cooldown. cooldown 중 요청은 자격증명 검증 없이 즉시 429.
- 메모리 bound: lazy 제거 + 주기적 sweep + 키 수 상한(eviction).
- 스레드풀 환경이므로 Lock으로 원자 갱신.
- 인메모리는 판정용(재기동 시 초기화 허용). 감사 기록은 LoginAttempt 테이블(FD §2.1).
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque

from app.config import get_settings


class _Entry:
    __slots__ = ("failures", "cooldown_until")

    def __init__(self) -> None:
        self.failures: deque[float] = deque()
        self.cooldown_until: float = 0.0


class RateLimiter:
    """인메모리 슬라이딩 윈도우 rate limiter (스레드 안전)."""

    def __init__(
        self,
        max_failures: int,
        window_sec: int,
        cooldown_sec: int,
        key_cap: int,
    ) -> None:
        self._max = max_failures
        self._window = window_sec
        self._cooldown = cooldown_sec
        self._cap = key_cap
        self._lock = threading.Lock()
        # LRU 성격: 오래된 키부터 eviction
        self._store: OrderedDict[str, _Entry] = OrderedDict()
        self._last_sweep = time.monotonic()

    def _prune_entry(self, entry: _Entry, now: float) -> None:
        """윈도우 밖 실패 타임스탬프 lazy 제거."""
        threshold = now - self._window
        while entry.failures and entry.failures[0] < threshold:
            entry.failures.popleft()

    def _maybe_sweep(self, now: float) -> None:
        """주기적 sweep: 만료 키(윈도우+cooldown 경과) 정리. (window 주기)."""
        if now - self._last_sweep < self._window:
            return
        self._last_sweep = now
        dead: list[str] = []
        for key, entry in self._store.items():
            self._prune_entry(entry, now)
            if not entry.failures and entry.cooldown_until <= now:
                dead.append(key)
        for key in dead:
            self._store.pop(key, None)

    def _evict_if_needed(self) -> None:
        """키 수 상한 초과 시 가장 오래된 키 eviction."""
        while len(self._store) > self._cap:
            self._store.popitem(last=False)

    def is_locked(self, key: str) -> bool:
        """cooldown 중이면 True (자격증명 검증 전 즉시 429 판정, FD §2.1 step 1)."""
        now = time.monotonic()
        with self._lock:
            self._maybe_sweep(now)
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.cooldown_until > now:
                self._store.move_to_end(key)
                return True
            return False

    def record_failure(self, key: str) -> None:
        """실패 기록. 윈도우 내 실패가 임계 도달 시 cooldown 설정."""
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                entry = _Entry()
                self._store[key] = entry
            self._store.move_to_end(key)
            self._prune_entry(entry, now)
            entry.failures.append(now)
            if len(entry.failures) >= self._max:
                entry.cooldown_until = now + self._cooldown
                entry.failures.clear()
            self._evict_if_needed()

    def record_success(self, key: str) -> None:
        """성공 시 해당 키 상태 초기화."""
        with self._lock:
            self._store.pop(key, None)

    @staticmethod
    def admin_key(store_id: str, username: str) -> str:
        return f"ADMIN:{store_id}:{username}"

    @staticmethod
    def table_key(store_id: str, table_no: str) -> str:
        return f"TABLE:{store_id}:{table_no}"


def _build_default() -> RateLimiter:
    s = get_settings()
    return RateLimiter(
        max_failures=s.rate_limit_max,
        window_sec=s.rate_limit_window_sec,
        cooldown_sec=s.rate_limit_cooldown_sec,
        key_cap=s.rate_limit_key_cap,
    )


# 전역 싱글턴(단일 워커 전제, NFR §9). 다중 인스턴스 전환 시 공유 저장소 필요.
login_rate_limiter: RateLimiter = _build_default()
