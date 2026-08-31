"""통합 테스트 — 주문 생성/목록/상태변경/삭제 (C4/C5/A2-S4/A3-S2)."""

from __future__ import annotations


def _first_two_menu_ids(client, headers) -> list[str]:
    resp = client.get("/api/menu", headers=headers)
    assert resp.status_code == 200
    menus = resp.json()["menus"]
    return [menus[0]["menu_id"], menus[1]["menu_id"]]


def test_create_order_computes_total_and_snapshot(client, table_session) -> None:
    headers = table_session["headers"]
    menu_ids = _first_two_menu_ids(client, headers)
    resp = client.post(
        "/api/orders",
        headers=headers,
        json={"items": [{"menu_id": menu_ids[0], "quantity": 2}, {"menu_id": menu_ids[1], "quantity": 1}]},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "PENDING"
    assert body["order_number"].startswith("store-001-")
    # 서버 계산 총액 = Σ line_amount
    assert body["total_amount"] == sum(i["line_amount"] for i in body["items"])
    # 스냅샷 필드 존재
    for item in body["items"]:
        assert item["unit_price"] == item["line_amount"] // item["quantity"]
        assert item["name"]


def test_create_order_empty_cart_400(client, table_session) -> None:
    resp = client.post("/api/orders", headers=table_session["headers"], json={"items": []})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] in ("ORDER_EMPTY", "VALIDATION_ERROR")


def test_create_order_invalid_menu_422(client, table_session) -> None:
    resp = client.post(
        "/api/orders",
        headers=table_session["headers"],
        json={"items": [{"menu_id": "m-nonexistent", "quantity": 1}]},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_orders_polling_has_server_time(client, table_session) -> None:
    headers = table_session["headers"]
    menu_ids = _first_two_menu_ids(client, headers)
    client.post("/api/orders", headers=headers, json={"items": [{"menu_id": menu_ids[0], "quantity": 1}]})
    resp = client.get("/api/orders", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "server_time" in body
    assert body["page_meta"]["total"] >= 1
    assert len(body["items"]) >= 1


def test_order_number_increments(client, table_session) -> None:
    headers = table_session["headers"]
    menu_ids = _first_two_menu_ids(client, headers)
    n1 = client.post("/api/orders", headers=headers, json={"items": [{"menu_id": menu_ids[0], "quantity": 1}]}).json()
    n2 = client.post("/api/orders", headers=headers, json={"items": [{"menu_id": menu_ids[0], "quantity": 1}]}).json()
    seq1 = int(n1["order_number"].rsplit("-", 1)[1])
    seq2 = int(n2["order_number"].rsplit("-", 1)[1])
    assert seq2 == seq1 + 1


def test_update_status_free_transition(client, table_session, admin_headers) -> None:
    headers = table_session["headers"]
    menu_ids = _first_two_menu_ids(client, headers)
    order = client.post("/api/orders", headers=headers, json={"items": [{"menu_id": menu_ids[0], "quantity": 1}]}).json()
    order_id = order["order_id"]
    # PENDING → COMPLETED (건너뛰기 허용, Q1=B)
    resp = client.patch(f"/api/orders/{order_id}/status", headers=admin_headers, json={"status": "COMPLETED"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"
    # 역방향 COMPLETED → PENDING 허용
    resp2 = client.patch(f"/api/orders/{order_id}/status", headers=admin_headers, json={"status": "PENDING"})
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "PENDING"


def test_delete_order_soft_delete_recalculates_total(client, table_session, admin_headers) -> None:
    headers = table_session["headers"]
    menu_ids = _first_two_menu_ids(client, headers)
    o1 = client.post("/api/orders", headers=headers, json={"items": [{"menu_id": menu_ids[0], "quantity": 1}]}).json()
    client.post("/api/orders", headers=headers, json={"items": [{"menu_id": menu_ids[1], "quantity": 1}]})

    resp = client.delete(f"/api/orders/{o1['order_id']}", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["deleted_order_id"] == o1["order_id"]
    # 삭제된 주문은 목록에서 사라짐
    listing = client.get("/api/orders", headers=headers).json()
    assert o1["order_id"] not in [o["order_id"] for o in listing["items"]]


def test_invalid_status_value_400(client, table_session, admin_headers) -> None:
    headers = table_session["headers"]
    menu_ids = _first_two_menu_ids(client, headers)
    order = client.post("/api/orders", headers=headers, json={"items": [{"menu_id": menu_ids[0], "quantity": 1}]}).json()
    resp = client.patch(f"/api/orders/{order['order_id']}/status", headers=admin_headers, json={"status": "SHIPPED"})
    assert resp.status_code == 400
