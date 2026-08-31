"""PBT — 금액 계산 불변식 (NFR-T-01, PBT-03).

property-based-testing Partial 모드: 순수 계산 로직에 한정 적용.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.services import pricing

# 도메인 제약 준수 생성기(PBT-07): price>=0 정수, qty 1..999
prices = st.integers(min_value=0, max_value=10_000_000)
quantities = st.integers(min_value=1, max_value=999)


@given(price=prices, qty=quantities)
def test_line_amount_nonnegative_and_product(price: int, qty: int) -> None:
    la = pricing.line_amount(price, qty)
    assert la == price * qty
    assert la >= 0


@given(amounts=st.lists(st.integers(min_value=0, max_value=10_000_000), max_size=200))
def test_total_amount_is_sum(amounts: list[int]) -> None:
    assert pricing.total_amount(amounts) == sum(amounts)


@given(amounts=st.lists(st.integers(min_value=0, max_value=10_000_000), min_size=1, max_size=200))
def test_total_amount_order_independent(amounts: list[int]) -> None:
    """항목 순서와 무관하게 총합 동일(교환·결합)."""
    import random

    shuffled = amounts[:]
    random.Random(0).shuffle(shuffled)
    assert pricing.total_amount(amounts) == pricing.total_amount(shuffled)


def test_total_amount_empty_is_zero() -> None:
    assert pricing.total_amount([]) == 0
