"""PBT — Pydantic 직렬화 라운드트립 (NFR-T-01, PBT-02).

serialize → deserialize = identity (스냅샷 필드 보존).
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.schemas.order import Order, OrderItem

names = st.text(min_size=1, max_size=100)
prices = st.integers(min_value=0, max_value=10_000_000)
quantities = st.integers(min_value=1, max_value=999)


@st.composite
def order_items(draw) -> OrderItem:  # type: ignore[no-untyped-def]
    unit_price = draw(prices)
    quantity = draw(quantities)
    return OrderItem(
        menu_id=draw(st.from_regex(r"m-[0-9]{1,6}", fullmatch=True)),
        name=draw(names),
        unit_price=unit_price,
        quantity=quantity,
        line_amount=unit_price * quantity,
    )


@given(item=order_items())
def test_order_item_roundtrip(item: OrderItem) -> None:
    dumped = item.model_dump()
    restored = OrderItem.model_validate(dumped)
    assert restored == item
    # 스냅샷 필드 보존 확인
    assert restored.name == item.name
    assert restored.unit_price == item.unit_price


@given(items=st.lists(order_items(), max_size=20))
def test_order_roundtrip(items: list[OrderItem]) -> None:
    order = Order(
        order_id="o-1",
        order_number="store-001-20260831-001",
        table_id="tbl-1",
        session_id="sess-1",
        status="PENDING",
        items=items,
        total_amount=sum(i.line_amount for i in items),
        created_at="2026-08-31T14:03:00+09:00",
    )
    restored = Order.model_validate(order.model_dump())
    assert restored == order
