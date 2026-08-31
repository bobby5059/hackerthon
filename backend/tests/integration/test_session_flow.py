"""통합 테스트 — 테이블 설정/대시보드/이용 완료/이력 (A3-S1/S3/S4, A2-S1)."""

from __future__ import annotations


def _first_menu_id(client, headers) -> str:
    return client.get("/api/menu", headers=headers).json()["menus"][0]["menu_id"]


def test_dashboard_aggregates_and_has_new_false(client, table_session, admin_headers) -> None:
    headers = table_session["headers"]
    menu_id = _first_menu_id(client, headers)
    client.post("/api/orders", headers=headers, json={"items": [{"menu_id": menu_id, "quantity": 2}]})

    resp = client.get("/api/tables/dashboard", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "server_time" in body
    card = next(t for t in body["tables"] if t["table_id"] == table_session["table_id"])
    assert card["total_amount"] > 0
    assert card["has_new"] is False  # Q9=A: 항상 false 포함
    assert len(card["recent_orders"]) >= 1


def test_re_setup_active_session_conflict(client, table_session, admin_headers) -> None:
    """활성 세션이 있는 테이블 재-setup → 409 (Q5=C)."""
    resp = client.post(
        f"/api/tables/{table_session['table_id']}/setup",
        headers=admin_headers,
        json={"table_no": table_session["table_no"], "table_password": "5678"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "SESSION_CLOSED"


def test_complete_blocked_by_pending_orders(client, table_session, admin_headers) -> None:
    """미완료(PENDING) 주문이 있으면 이용 완료 차단 → 409 (Q2=B)."""
    headers = table_session["headers"]
    menu_id = _first_menu_id(client, headers)
    client.post("/api/orders", headers=headers, json={"items": [{"menu_id": menu_id, "quantity": 1}]})

    resp = client.post(f"/api/tables/{table_session['table_id']}/complete", headers=admin_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "SESSION_CLOSED"


def test_complete_archives_and_resets(client, table_session, admin_headers) -> None:
    """모든 주문 COMPLETED 후 이용 완료 → 이력 이관 + 총액 0."""
    headers = table_session["headers"]
    menu_id = _first_menu_id(client, headers)
    order = client.post("/api/orders", headers=headers, json={"items": [{"menu_id": menu_id, "quantity": 1}]}).json()
    client.patch(f"/api/orders/{order['order_id']}/status", headers=admin_headers, json={"status": "COMPLETED"})

    resp = client.post(f"/api/tables/{table_session['table_id']}/complete", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["archived_order_count"] == 1
    assert body["table_total_amount"] == 0

    # 이력 조회에 등장
    hist = client.get("/api/history", headers=admin_headers).json()
    assert any(h["order_id"] == order["order_id"] for h in hist["items"])

    # 대시보드 총액 리셋
    dash = client.get("/api/tables/dashboard", headers=admin_headers).json()
    card = next(t for t in dash["tables"] if t["table_id"] == table_session["table_id"])
    assert card["total_amount"] == 0


def test_history_pagination_and_sort(client, table_session, admin_headers) -> None:
    hist = client.get("/api/history?page=1&size=10", headers=admin_headers)
    assert hist.status_code == 200
    assert hist.json()["page_meta"]["page"] == 1
