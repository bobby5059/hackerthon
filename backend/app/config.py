"""환경설정 로딩 (Pydantic Settings).

logical-components §6 / tech-stack §4 정합. 모든 비밀·경로·상한을 env로 주입한다
(하드코딩 금지, BR-AUTH-06). `.env`는 python-dotenv 경유로 로딩된다.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정. env 변수명과 1:1 매핑(대소문자 무시)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── JWT ──
    jwt_secret: str = "dev-insecure-secret-change-me"  # 운영은 env 필수 주입
    jwt_issuer: str = "table-order"
    admin_token_ttl_hours: int = 16

    # ── CORS ──
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    # ── DB ──
    db_path: str = "./table_order.db"
    db_busy_timeout_ms: int = 5000

    # ── Rate limit (로그인) ──
    rate_limit_max: int = 5
    rate_limit_window_sec: int = 300
    rate_limit_cooldown_sec: int = 300
    rate_limit_key_cap: int = 10000

    # ── 해싱 ──
    bcrypt_cost: int = 12

    # ── 본문 크기 ──
    max_body_bytes: int = 1_048_576  # 1MB

    # ── 시드 ──
    seed_store_id: str = "store-001"
    seed_store_name: str = "샘플 매장"
    seed_admin_username: str = "manager"
    seed_admin_password: str = "change-me-8chars"

    @property
    def cors_origin_list(self) -> list[str]:
        """콤마 구분 문자열을 오리진 리스트로 변환(공백 제거, 와일드카드 금지)."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip() and o.strip() != "*"]


@lru_cache
def get_settings() -> Settings:
    """설정 싱글턴. 테스트에서는 `get_settings.cache_clear()`로 초기화 가능."""
    return Settings()
