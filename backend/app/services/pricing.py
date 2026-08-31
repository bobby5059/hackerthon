"""순수 금액 계산 로직 (PBT 대상, NFR-T-01, business-logic-model §8).

부수효과 없는 순수 함수 — Hypothesis property-based test로 불변식 검증.
"""

from __future__ import annotations


def line_amount(unit_price: int, quantity: int) -> int:
    """항목 금액 = 단가 × 수량. (price>=0, qty>=1 전제) 결과 >= 0."""
    return unit_price * quantity


def total_amount(line_amounts: list[int]) -> int:
    """총액 = Σ line_amount. 항목 순서와 무관(교환·결합). 빈 목록은 0."""
    return sum(line_amounts)
