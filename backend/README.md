# Table Order Service — backend-api

테이블 오더 서비스의 백엔드 API. 계약(Integration Contract v1.0)의 **제공자(Provider)**이며,
FastAPI OpenAPI(`/docs`, `/openapi.json`)가 런타임 진실 원천이다.

- **스택**: FastAPI + Uvicorn / Python 3.12 / SQLAlchemy 2.0(sync) / SQLite(WAL) / Pydantic v2 / PyJWT(HS256) / passlib[bcrypt]
- **테스트**: pytest + Hypothesis(PBT) + httpx(TestClient)

## 1. 설치

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Python 3.12 권장
pip install -e .            # pyproject.toml 기반 (런타임 deps)
pip install -r requirements-dev.txt   # 테스트/린트 도구
```

> `requirements.txt`는 런타임 의존성 버전 lock(SECURITY-10). `pyproject.toml`이 소스 오브 트루스.

## 2. 환경 변수

`.env.example`를 `.env`로 복사 후 값 지정. 핵심 변수:

| 변수 | 설명 | 기본 |
|---|---|---|
| `JWT_SECRET` | HS256 서명 키 (**필수, 하드코딩 금지**) | — |
| `JWT_ISSUER` | 토큰 iss 클레임 | `table-order` |
| `ADMIN_TOKEN_TTL_HOURS` | 관리자 세션 TTL | `16` |
| `CORS_ORIGINS` | 허용 오리진(콤마 구분) | — |
| `DB_PATH` | SQLite 파일 경로 | `./table_order.db` |
| `RATE_LIMIT_MAX` / `_WINDOW` / `_COOLDOWN` | 로그인 시도 제한 | `5` / `300` / `300` |
| `BCRYPT_COST` | bcrypt 라운드 | `12` |
| `MAX_BODY_BYTES` | 요청 본문 상한 | `1048576` (1MB) |
| `SEED_ADMIN_PASSWORD` | 시드 관리자 비밀번호(≥8자) | — |

## 3. 기동

```bash
uvicorn app.main:app --reload --port 8000
```

기동 시 `create_all`로 테이블을 생성한다(Q4=A, Alembic 미사용). WAL/foreign_keys/busy_timeout PRAGMA가 커넥션마다 적용된다.

## 4. 시드

```bash
SEED_ADMIN_PASSWORD='<8자이상>' python -m app.db.seed
```

단일 매장(Store) + 관리자(AdminUser) + 테이블 3개 + 카테고리(식사/음료/주류) 및 샘플 메뉴를 멱등하게 생성한다.

## 5. 테스트

```bash
pytest                 # 전체
pytest tests/unit      # PBT(순수 계산·채번·직렬화)
pytest tests/integration
```

> 테스트는 임시 DB 파일에 시드 후 실행(`BCRYPT_COST=4`로 가속). 상세 실행 절차는 Build & Test 단계 지침 참조.

## 6. 아키텍처 (계층)

```
config / time_utils / logging_config
  → db(engine · models · schema · session)
  → schemas(Pydantic v2)
  → security(jwt · hashing · ratelimit · deps)
  → middleware + errors
  → repositories → services → routers → main
```

- **인증/인가**: JWT `typ`(A=관리자 / T=테이블) 분리, deny-by-default, 매 요청 exp/iss 서버측 검증
- **채번**: `{store_id}-{YYYYMMDD}-{NNN}` (Asia/Seoul), 트랜잭션 내 MAX+1
- **금액**: 정수 KRW, 서버 재계산(스냅샷 unit_price·line_amount)
- **동시성**: SQLITE_BUSY 시 write 재시도 max 3(10/20/40ms), 이후 fail-closed 500
- **시각**: 모든 타임스탬프 ISO 8601 `+09:00`

## 7. 엔드포인트 (계약 §2.6)

| 메서드 | 경로 | 인증 |
|---|---|---|
| POST | `/api/admin/login` | 🔓 |
| POST | `/api/table/login` | 🔓 |
| GET | `/api/menu` · `/api/menu/{menu_id}` | 🔑T/A |
| POST | `/api/orders` | 🔑T |
| GET | `/api/orders` | 🔑T |
| PATCH | `/api/orders/{order_id}/status` | 🔑A |
| DELETE | `/api/orders/{order_id}` | 🔑A |
| POST | `/api/tables/{table_id}/setup` | 🔑A |
| GET | `/api/tables/dashboard` | 🔑A |
| POST | `/api/tables/{table_id}/complete` | 🔑A |
| GET | `/api/history` | 🔑A |
| GET | `/health` | 🔓 |
