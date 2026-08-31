"""시각 유틸 — Asia/Seoul(+09:00) 기준 (NFR-D-03, 계약 §1.1).

모든 시각 생성·직렬화는 Asia/Seoul 오프셋을 포함하는 ISO 8601로 통일한다.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

# Asia/Seoul 고정 오프셋(+09:00). DST 없음.
KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    """현재 시각(Asia/Seoul, tz-aware)."""
    return datetime.now(KST)


def to_iso(dt: datetime) -> str:
    """datetime을 ISO 8601(+09:00) 문자열로 직렬화.

    naive datetime은 KST로 간주하여 오프셋을 부여한다.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt.astimezone(KST).isoformat()


def parse_iso(value: str) -> datetime:
    """ISO 8601 문자열을 tz-aware datetime(KST)으로 파싱."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt.astimezone(KST)


def today_kst() -> date:
    """Asia/Seoul 기준 오늘 날짜(채번 기준, BR-NUM-01)."""
    return now_kst().date()


def date_str(d: date) -> str:
    """YYYYMMDD 형식(주문번호 채번용)."""
    return d.strftime("%Y%m%d")
