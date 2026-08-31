"""테스트 공통 픽스처 — 임시 DB, 시드, TestClient, 토큰.

각 테스트는 격리된 임시 SQLite 파일을 사용한다(엔진 재생성). 시드로 매장/관리자/테이블/메뉴 준비.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest

# env를 테스트 값으로 고정(엔진 생성 전에 설정)
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "test-admin-pw")
os.environ.setdefault("RATE_LIMIT_MAX", "5")
os.environ.setdefault("BCRYPT_COST", "4")  # 테스트 속도


@pytest.fixture()
def temp_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """임시 DB 경로로 엔진 재생성 + create_all + seed."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setenv("DB_PATH", path)

    from app.config import get_settings

    get_settings.cache_clear()

    # 엔진/세션팩토리 재빌드 (새 DB_PATH 반영)
    import app.db.engine as engine_mod

    engine_mod.engine.dispose()
    engine_mod.engine = engine_mod._build_engine()
    engine_mod.SessionLocal.configure(bind=engine_mod.engine)

    from app.db.schema import create_all
    from app.db.seed import seed

    create_all(engine_mod.engine)
    db = engine_mod.SessionLocal()
    try:
        seed(db)
    finally:
        db.close()

    yield path

    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture()
def client(temp_db: str):  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def store_id() -> str:
    return "store-001"


@pytest.fixture()
def admin_token(client, store_id: str) -> str:  # type: ignore[no-untyped-def]
    resp = client.post(
        "/api/admin/login",
        json={"store_id": store_id, "username": "manager", "password": "test-admin-pw"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def admin_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def seeded_menu_ids(client, admin_headers) -> list[str]:  # type: ignore[no-untyped-def]
    resp = client.get("/api/menu", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    return [m["menu_id"] for m in resp.json()["menus"]]


@pytest.fixture()
def table_session(client, admin_headers, store_id):  # type: ignore[no-untyped-def]
    """테이블 setup 후 테이블 토큰 발급. (table_id, table_no, table_token) 반환."""
    # 대시보드에서 첫 테이블 id 확보
    dash = client.get("/api/tables/dashboard", headers=admin_headers)
    assert dash.status_code == 200, dash.text
    table = dash.json()["tables"][0]
    table_id = table["table_id"]
    table_no = table["table_no"]

    setup = client.post(
        f"/api/tables/{table_id}/setup",
        headers=admin_headers,
        json={"table_no": table_no, "table_password": "1234"},
    )
    assert setup.status_code == 200, setup.text

    login = client.post(
        "/api/table/login",
        json={"store_id": store_id, "table_no": table_no, "table_password": "1234"},
    )
    assert login.status_code == 200, login.text
    return {
        "table_id": table_id,
        "table_no": table_no,
        "token": login.json()["access_token"],
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }
