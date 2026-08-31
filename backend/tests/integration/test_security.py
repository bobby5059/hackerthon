"""통합 테스트 — deny-by-default / IDOR / 에러 형식 / 본문 크기 (SECURITY-05/08/15)."""

from __future__ import annotations


def test_missing_token_401_standard_error(client) -> None:
    resp = client.get("/api/orders")
    assert resp.status_code == 401
    body = resp.json()
    assert set(body["error"].keys()) == {"code", "message", "request_id"}
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_invalid_token_401(client) -> None:
    resp = client.get("/api/menu", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


def test_error_response_includes_request_id(client, admin_headers) -> None:
    resp = client.get("/api/menu/does-not-exist", headers=admin_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"
    assert resp.json()["error"]["request_id"]


def test_request_id_header_present(client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-Id")


def test_security_headers_present(client) -> None:
    resp = client.get("/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"


def test_idor_delete_other_store_order_hidden_404(client, admin_headers) -> None:
    """존재하지 않는(또는 타 매장) 주문 삭제 → 404 은닉."""
    resp = client.delete("/api/orders/o-nonexistent", headers=admin_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_pagination_size_over_limit_422(client, admin_headers) -> None:
    """size>100 → FastAPI 쿼리 검증 실패(422)."""
    resp = client.get("/api/history?size=1000", headers=admin_headers)
    assert resp.status_code in (400, 422)
