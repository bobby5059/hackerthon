"""PBT — 주문번호 포맷↔파싱 라운드트립 (NFR-T-01, PBT-02, BR-NUM)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.services.order_number import format_order_number, parse_order_number

# store_id는 '-'를 포함할 수 있음(예: store-001). 세그먼트 텍스트는 '-' 미포함 허용 문자.
store_ids = st.from_regex(r"[a-z]+-[0-9]{1,4}", fullmatch=True)
dates = st.from_regex(r"20[0-9]{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])", fullmatch=True)
seqs = st.integers(min_value=1, max_value=99_999)


@given(store_id=store_ids, date=dates, seq=seqs)
def test_format_parse_roundtrip(store_id: str, date: str, seq: int) -> None:
    number = format_order_number(store_id, date, seq)
    parsed_store, parsed_date, parsed_seq = parse_order_number(number)
    assert parsed_store == store_id
    assert parsed_date == date
    assert parsed_seq == seq


def test_format_zero_pads_to_three_digits() -> None:
    assert format_order_number("store-001", "20260831", 1) == "store-001-20260831-001"


def test_format_expands_beyond_999() -> None:
    assert format_order_number("store-001", "20260831", 1000) == "store-001-20260831-1000"
