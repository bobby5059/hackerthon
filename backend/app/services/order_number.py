"""주문번호 채번 포맷/파싱 (PBT 대상 라운드트립, BR-NUM-01~03, 계약 §6).

형식: {store_id}-{YYYYMMDD}-{NNN}  (NNN은 001부터, 999 초과 시 자릿수 확장)
store_id에 '-'가 포함될 수 있으므로 파싱은 우측 2개 세그먼트를 기준으로 분해한다.
"""

from __future__ import annotations


def format_order_number(store_id: str, date_yyyymmdd: str, seq: int) -> str:
    """채번 문자열 생성."""
    return f"{store_id}-{date_yyyymmdd}-{seq:03d}"


def parse_order_number(order_number: str) -> tuple[str, str, int]:
    """(store_id, YYYYMMDD, seq) 로 분해. format의 역함수(라운드트립)."""
    store_id, date_part, seq_part = order_number.rsplit("-", 2)
    return store_id, date_part, int(seq_part)
