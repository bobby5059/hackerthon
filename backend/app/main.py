"""FastAPI 애플리케이션 진입점 — 미들웨어 체인·에러 핸들러·라우터 등록 (NFR §7).

미들웨어 등록 순서(Starlette는 나중에 추가한 것이 아우터):
  add 순서 [보안헤더 → 본문크기 → CORS → 로깅 → request_id]
  → 실행 시 아우터부터: request_id → 로깅 → CORS → 본문크기 → 보안헤더 → 라우팅
에러 핸들러는 exception_handler로 등록되어 미들웨어 바깥에서 예외를 표준화한다(§4).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.schema import create_all
from app.errors import register_error_handlers
from app.logging_config import configure_logging, get_logger
from app.middleware.body_size import BodySizeLimitMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routers import auth, history, menu, order, table


@asynccontextmanager
async def lifespan(_app: FastAPI):  # type: ignore[no-untyped-def]
    """기동 시 create tables (Q4=A, Alembic 없음)."""
    configure_logging()
    create_all()
    get_logger().info("backend-api started")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Table Order Service — backend-api", version="1.0.0", lifespan=lifespan)

    # ── 에러 핸들러(§4) ──
    register_error_handlers(app)

    # ── 미들웨어 체인 (add 역순이 실행 아우터) ──
    # 이너 → 아우터 순으로 add: 보안헤더 → 본문크기 → CORS → 로깅 → request_id
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,  # 명시 오리진, 와일드카드 금지
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
    )
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # ── 라우터 ──
    app.include_router(auth.router)
    app.include_router(menu.router)
    app.include_router(order.router)
    app.include_router(table.router)
    app.include_router(history.router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
