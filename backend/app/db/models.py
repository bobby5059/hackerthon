"""ORM 매핑 — 전 엔티티 (domain-entities.md §2/§3/§4).

- 모든 ID는 string(TEXT). 금액·수량·순번은 INTEGER(정수 KRW).
- 시각은 TEXT(ISO8601 +09:00), date는 TEXT(YYYY-MM-DD).
- enum은 TEXT + CHECK 제약. UNIQUE·인덱스는 도메인 규칙 반영.
- 파라미터화 쿼리만 사용(SECURITY-05) — Repository 계층에서 강제.
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# 열거형 허용값(CHECK 제약용)
ORDER_STATUSES = ("PENDING", "PREPARING", "COMPLETED")
SESSION_STATUSES = ("ACTIVE", "COMPLETED", "EXPIRED")
LOGIN_ATTEMPT_TYPES = ("ADMIN", "TABLE")


class Base(DeclarativeBase):
    pass


class Store(Base):
    __tablename__ = "stores"

    store_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class AdminUser(Base):
    __tablename__ = "admin_users"
    __table_args__ = (UniqueConstraint("store_id", "username", name="uq_admin_store_username"),)

    admin_id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.store_id"), nullable=False)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)  # bcrypt (SECURITY-12)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class Table(Base):
    __tablename__ = "tables"
    __table_args__ = (UniqueConstraint("store_id", "table_no", name="uq_table_store_no"),)

    table_id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.store_id"), nullable=False)
    table_no: Mapped[str] = mapped_column(String(20), nullable=False)
    table_password_hash: Mapped[str | None] = mapped_column(String, nullable=True)  # bcrypt PIN
    auto_login_enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class TableSession(Base):
    __tablename__ = "table_sessions"
    __table_args__ = (
        CheckConstraint(
            f"status IN {SESSION_STATUSES}", name="ck_session_status"
        ),
        Index("ix_session_store_table_status", "store_id", "table_id", "status"),
    )

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.store_id"), nullable=False)
    table_id: Mapped[str] = mapped_column(String, ForeignKey("tables.table_id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")
    started_at: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[str] = mapped_column(Text, nullable=False)  # started_at + 16h
    completed_at: Mapped[str | None] = mapped_column(Text, nullable=True)


class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.store_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Menu(Base):
    __tablename__ = "menus"

    menu_id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.store_id"), nullable=False)
    category_id: Mapped[str] = mapped_column(
        String, ForeignKey("categories.category_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)  # 정수 KRW, >= 0
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(f"status IN {ORDER_STATUSES}", name="ck_order_status"),
        # 채번 이중 안전장치 (BR-NUM-04): 삭제 포함 순번 유일성
        UniqueConstraint("store_id", "order_date", "order_seq", name="uq_order_seq"),
        Index("ix_order_session_deleted", "store_id", "session_id", "deleted_at"),
        Index("ix_order_store_date", "store_id", "order_date"),
        Index("ix_order_table_deleted", "store_id", "table_id", "deleted_at"),
    )

    order_id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, ForeignKey("stores.store_id"), nullable=False)
    table_id: Mapped[str] = mapped_column(String, ForeignKey("tables.table_id"), nullable=False)
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("table_sessions.session_id"), nullable=False
    )
    order_number: Mapped[str] = mapped_column(String, nullable=False)
    order_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    order_date: Mapped[str] = mapped_column(Text, nullable=False)  # YYYY-MM-DD (KST)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_at: Mapped[str | None] = mapped_column(Text, nullable=True)  # soft delete (Q3=B)
    deleted_by: Mapped[str | None] = mapped_column(String, nullable=True)

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str] = mapped_column(String, ForeignKey("orders.order_id"), nullable=False)
    menu_id: Mapped[str] = mapped_column(String, nullable=False)  # 참조(FK 강제 안 함, 스냅샷)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 주문 시점 스냅샷
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)  # 주문 시점 스냅샷
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_amount: Mapped[int] = mapped_column(Integer, nullable=False)  # unit_price * quantity

    order: Mapped[Order] = relationship(back_populates="items")


class OrderHistory(Base):
    __tablename__ = "order_histories"
    __table_args__ = (
        CheckConstraint(f"status IN {ORDER_STATUSES}", name="ck_history_status"),
        Index("ix_history_store_session", "store_id", "session_id"),
        Index("ix_history_store_completed", "store_id", "completed_at"),
    )

    history_id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, nullable=False)
    table_id: Mapped[str] = mapped_column(String, nullable=False)
    session_id: Mapped[str] = mapped_column(String, nullable=False)
    order_id: Mapped[str] = mapped_column(String, nullable=False)  # 원본 추적
    order_number: Mapped[str] = mapped_column(String, nullable=False)
    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)  # 원 주문 생성 시각
    completed_at: Mapped[str] = mapped_column(Text, nullable=False)  # 세션 종료 시각

    items: Mapped[list[OrderHistoryItem]] = relationship(
        back_populates="history", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderHistoryItem(Base):
    __tablename__ = "order_history_items"

    history_item_id: Mapped[str] = mapped_column(String, primary_key=True)
    history_id: Mapped[str] = mapped_column(
        String, ForeignKey("order_histories.history_id"), nullable=False
    )
    menu_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_amount: Mapped[int] = mapped_column(Integer, nullable=False)

    history: Mapped[OrderHistory] = relationship(back_populates="items")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_store_created", "store_id", "created_at"),)

    audit_id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    before_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    __table_args__ = (
        CheckConstraint(f"attempt_type IN {LOGIN_ATTEMPT_TYPES}", name="ck_attempt_type"),
        Index("ix_attempt_store_principal", "store_id", "principal", "attempted_at"),
    )

    attempt_id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[str] = mapped_column(String, nullable=False)
    principal: Mapped[str] = mapped_column(String, nullable=False)
    attempt_type: Mapped[str] = mapped_column(String, nullable=False)
    success: Mapped[int] = mapped_column(Integer, nullable=False)
    attempted_at: Mapped[str] = mapped_column(Text, nullable=False)
