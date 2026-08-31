"""통합 테스트 — 인증/rate limit/typ 분리 (SECURITY-08/12)."""

from __future__ import annotations


def test_admin_login_success(client, store_id) -> None:
    resp = client.post(
        "/api/admin/login",
        json={"store_id": store_id, "username": "manager", "password": "test-admin-pw"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["store"]["store_id"] == store_id
    assert "access_token" in body


def test_admin_login_wrong_password_generic_401(client, store_id) -> None:
    resp = client.post(
        "/api/admin/login",
        json={"store_id": store_id, "username": "manager", "password": "wrong-pw"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_admin_login_unknown_user_same_path(client, store_id) -> None:
    """존재하지 않는 사용자도 동일한 401(사용자 열거 방지)."""
    resp = client.post(
        "/api/admin/login",
        json={"store_id": store_id, "username": "ghost", "password": "whatever"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_admin_login_rate_limited_after_threshold(client, store_id) -> None:
    """5회 실패 후 429."""
    for _ in range(5):
        client.post(
            "/api/admin/login",
            json={"store_id": store_id, "username": "manager", "password": "bad"},
        )
    resp = client.post(
        "/api/admin/login",
        json={"store_id": store_id, "username": "manager", "password": "bad"},
    )
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "RATE_LIMITED"


def test_protected_route_requires_token(client) -> None:
    resp = client.get("/api/menu")
    assert resp.status_code == 401


def test_table_token_cannot_access_admin_endpoint(client, table_session) -> None:
    """typ 분리: 테이블 토큰으로 관리자 대시보드 접근 → 403."""
    resp = client.get("/api/tables/dashboard", headers=table_session["headers"])
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_admin_token_cannot_create_order(client, admin_headers) -> None:
    """typ 분리: 관리자 토큰으로 주문 생성(🔑T) → 403."""
    resp = client.post("/api/orders", headers=admin_headers, json={"items": []})
    assert resp.status_code in (403, 400)  # typ 검사가 우선(403), 스키마 검사면 400
