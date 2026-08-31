"""단일 매장 시드 스크립트 (Q8=B 최소 시드).

- Store 1 + AdminUser 1(bcrypt≥8자, env 주입) + Table 샘플 + Category/Menu 샘플.
- 관리자 비밀번호·시드 값은 env(SEED_*)에서 주입(하드코딩 금지, BR-AUTH-06).
- 실행: `python -m app.db.seed` (기동 전 1회). 이미 존재하면 idempotent(중복 생성 안 함).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.engine import SessionLocal
from app.db.models import AdminUser, Category, Menu, Store, Table
from app.db.schema import create_all
from app.repositories import store_repo
from app.repositories.ids import new_id
from app.security.hashing import hash_password
from app.time_utils import now_kst, to_iso

# 샘플 메뉴 시드(카테고리별)
_SEED_MENU = {
    "식사": [
        ("김치찌개", 9000, "얼큰한 김치찌개"),
        ("된장찌개", 8000, "구수한 된장찌개"),
        ("제육볶음", 10000, "매콤한 제육볶음"),
    ],
    "음료": [
        ("콜라", 2000, None),
        ("사이다", 2000, None),
    ],
    "주류": [
        ("소주", 5000, None),
        ("맥주", 5000, None),
    ],
}


def seed(db: Session) -> None:
    settings = get_settings()
    store_id = settings.seed_store_id
    now = to_iso(now_kst())

    if store_repo.get_store(db, store_id) is not None:
        # 이미 시드됨 — idempotent
        return

    if len(settings.seed_admin_password) < 8:
        raise ValueError("SEED_ADMIN_PASSWORD must be at least 8 characters (SECURITY-12)")

    db.add(Store(store_id=store_id, name=settings.seed_store_name, created_at=now))
    db.add(
        AdminUser(
            admin_id=new_id("admin"),
            store_id=store_id,
            username=settings.seed_admin_username,
            password_hash=hash_password(settings.seed_admin_password),
            created_at=now,
        )
    )

    # 샘플 테이블 3개(setup 전 상태: 비번 없음, auto_login 비활성)
    for no in ("1", "2", "3"):
        db.add(
            Table(
                table_id=new_id("tbl"),
                store_id=store_id,
                table_no=no,
                table_password_hash=None,
                auto_login_enabled=0,
                created_at=now,
            )
        )

    # 카테고리 + 메뉴
    for order_idx, (cat_name, menus) in enumerate(_SEED_MENU.items()):
        category_id = new_id("cat")
        db.add(
            Category(
                category_id=category_id,
                store_id=store_id,
                name=cat_name,
                display_order=order_idx,
            )
        )
        for name, price, desc in menus:
            db.add(
                Menu(
                    menu_id=new_id("m"),
                    store_id=store_id,
                    category_id=category_id,
                    name=name,
                    price=price,
                    description=desc,
                    image_url=None,
                )
            )

    db.commit()


def main() -> None:
    create_all()
    db = SessionLocal()
    try:
        seed(db)
        print("Seed complete.")  # noqa: T201
    finally:
        db.close()


if __name__ == "__main__":
    main()
