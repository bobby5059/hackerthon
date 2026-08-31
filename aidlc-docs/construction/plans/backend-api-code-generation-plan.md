# Code Generation Plan — Unit 1 (backend-api)

> AI-DLC CONSTRUCTION / Unit 1 (backend-api) / Code Generation / **Part 1 — Planning**
> **본 계획서는 Code Generation의 단일 진실 원천(Single Source of Truth)이다.** Part 2(Generation)는 이 계획의 단계를 순서대로 실행하며, 완료 시마다 체크박스를 [x]로 갱신한다.
> 근거: `integration-contract.md` v1.0(SSOT), `functional-design/*`(domain-entities/business-logic-model/business-rules), `nfr-requirements/*`(nfr-requirements/tech-stack-decisions), `nfr-design/*`(nfr-design-patterns/logical-components), `unit-of-work-story-map.md`.
> 확장: **Security Baseline(Yes, 블로킹)**, **PBT(Partial — 순수 계산·직렬화 라운드트립)**, Resiliency(No).

---

## 0. 유닛 컨텍스트 (Step 1 · Step 3)

### 0.1 코드 위치 (Critical Rule)
- **워크스페이스 루트**: `/Users/chygg/workspace/hackerthon` (aidlc-state.md의 `~/aidlc-workshop/table-order`는 stale 값 — 실제 리포지토리 루트 기준)
- **애플리케이션 코드**: `backend/` (워크스페이스 루트 하위, greenfield — 기존 디렉토리 없음)
- **문서(마크다운 요약)**: `aidlc-docs/construction/backend-api/code/`
- 프로젝트 유형: **Greenfield multi-unit** — 유닛별 디렉토리(`backend/`). tech-stack §3 트리 준수.

### 0.2 이 유닛이 구현하는 스토리 (backend-api 서버측 지원)
| 스토리 | 엔드포인트(계약 §2.6) | 구현 위치 |
|---|---|---|
| A1-S1 매장 로그인 | `POST /api/admin/login` | AuthService, AuthRouter |
| A1-S2 16h 세션·서버측 검증 | (JWT exp/iss 매요청 검증) | security/jwt, deps |
| A1-S3 로그인 시도 제한 | (RateLimiter) | security/ratelimit |
| C1-S1 테이블 자동 로그인 | `POST /api/table/login` | AuthService, AuthRouter |
| C1-S2 세션 컨텍스트 유지 | (세션 스코프·신규 세션) | TableSessionService |
| C2-S1 메뉴 목록 | `GET /api/menu` | MenuService, MenuRouter |
| C2-S2 메뉴 상세 | `GET /api/menu/{menu_id}` | MenuService, MenuRouter |
| C4-S1~S3 주문 확정 | `POST /api/orders` | OrderService, OrderRouter |
| C5-S1/S2 세션 주문 내역(폴링) | `GET /api/orders` | OrderService, OrderRouter |
| A2-S1/S2/S5 대시보드(폴링) | `GET /api/tables/dashboard` | TableSessionService, TableRouter |
| A2-S4 주문 상태 변경 | `PATCH /api/orders/{order_id}/status` | OrderService, OrderRouter |
| A3-S1 테이블 초기 설정 | `POST /api/tables/{table_id}/setup` | TableSessionService, TableRouter |
| A3-S2 주문 직권 삭제 | `DELETE /api/orders/{order_id}` | OrderService, OrderRouter |
| A3-S3 이용 완료(세션 종료) | `POST /api/tables/{table_id}/complete` | TableSessionService, HistoryService, TableRouter |
| A3-S4 과거 이력 조회 | `GET /api/history` | HistoryService, HistoryRouter |

### 0.3 의존성·인터페이스·계약
- **제공자/SSOT**: backend-api는 계약 v1.0의 제공자. FastAPI OpenAPI(`/docs`, `/openapi.json`)가 런타임 진실 원천. **계약 §3(모델)·§4(클레임) 변경 없음.**
- **소비 유닛**: `shared`(TS 타입 미러), `customer-web`(🔑T), `admin-web`(🔑A). 본 유닛은 이들에 대한 런타임 의존 없음(제공자). CORS 오리진만 env로 허용.
- **소유 DB 엔티티**: Store, AdminUser, Table, TableSession, Category, Menu, Order, OrderItem, OrderHistory, OrderHistoryItem, AuditLog, LoginAttempt (domain-entities.md).

---

## 1. 목표 디렉토리 트리 (tech-stack §3 확정)

```
backend/
├── pyproject.toml          # deps, ruff/mypy/pytest 설정
├── requirements.txt        # 버전 lock (SECURITY-10)
├── .env.example            # JWT_SECRET, CORS_ORIGINS, DB_PATH 등
├── README.md               # 실행/시드/테스트 방법
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI app, 미들웨어·에러핸들러·라우터 등록, 기동 시 create tables
│   ├── config.py           # Pydantic Settings (env 로딩)
│   ├── logging_config.py   # 구조화 JSON 로깅 + request_id + 마스킹 (C3)
│   ├── errors.py           # AppError 예외 계층 + 전역 핸들러 (C1, §4)
│   ├── time_utils.py       # Asia/Seoul now/ISO8601 (NFR-D-03)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── engine.py       # SQLAlchemy engine + connect 훅 PRAGMA (C9)
│   │   ├── models.py       # ORM 매핑(전 엔티티)
│   │   ├── schema.py       # create_all (기동 시, Q4=A)
│   │   ├── session.py      # get_db 요청 단위 세션 (C10) + tx 헬퍼/retry (C11)
│   │   └── seed.py         # 단일 매장 시드 스크립트
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py       # PageMeta, ErrorResponse, 에러 코드 enum
│   │   ├── auth.py         # 로그인 요청/응답
│   │   ├── menu.py         # Category, Menu
│   │   ├── order.py        # OrderItemInput, OrderItem, Order, 목록 응답
│   │   ├── table.py        # setup/complete/dashboard, TableCard, OrderPreview
│   │   └── history.py      # HistoryEntry, 목록 응답
│   ├── security/
│   │   ├── __init__.py
│   │   ├── jwt.py          # PyJWT HS256 발급/검증 (typ/exp/iss)
│   │   ├── hashing.py      # passlib[bcrypt]
│   │   ├── ratelimit.py    # 인메모리 슬라이딩 윈도우 (C8)
│   │   └── deps.py         # get_claims/require_admin/require_table/get_store_scope (C7)
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── request_id.py   # C2
│   │   ├── logging.py      # C3 요청/응답 로깅
│   │   ├── body_size.py    # C5 본문 ≤1MB
│   │   └── security_headers.py  # C6
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── store_repo.py   # get_admin, get_store
│   │   ├── table_repo.py   # 테이블/세션 CRUD, 활성 세션 조회
│   │   ├── menu_repo.py    # 카테고리/메뉴 조회
│   │   ├── order_repo.py   # 주문 CRUD, 채번 MAX+1, 총액 합계, soft-delete
│   │   └── history_repo.py # 이력 이관/조회
│   └── services/
│       ├── __init__.py
│       ├── auth_service.py     # authenticate_admin/table, issue/verify jwt
│       ├── menu_service.py     # list_menu, get_menu
│       ├── order_service.py    # create/list/update_status/delete + 채번 + 총액
│       ├── session_service.py  # setup/get_or_start/dashboard/complete
│       └── history_service.py  # archive_session, list_history
├── routers/  → app/routers/
│   ├── __init__.py
│   ├── auth.py
│   ├── menu.py
│   ├── order.py
│   ├── table.py
│   └── history.py
└── tests/
    ├── __init__.py
    ├── conftest.py         # TestClient, 인메모리/임시 DB fixture, 시드
    ├── unit/
    │   ├── __init__.py
    │   ├── test_pricing_pbt.py    # PBT: line_amount/total_amount invariant (NFR-T-01)
    │   ├── test_order_number_pbt.py  # PBT: 채번 포맷 라운드트립
    │   └── test_serialization_pbt.py # PBT: Pydantic 직렬화 라운드트립
    └── integration/
        ├── __init__.py
        ├── test_auth.py           # 로그인·rate limit·typ 분리
        ├── test_order_flow.py     # 주문 생성/목록/상태/삭제
        ├── test_session_flow.py   # setup/dashboard/complete/이력
        └── test_security.py       # deny-by-default·IDOR·에러 형식
```
> `app/routers/`는 tech-stack §3의 `routers/`를 `app/` 하위로 배치(패키지 일관성). 나머지는 §3 그대로.

---

## 2. 생성 단계 (Steps — 순서대로 실행)

> 규칙: 각 단계 완료 즉시 체크박스 [x]. 계층 순서(설정 → DB → 스키마 → 보안 → 미들웨어/에러 → 리포지토리 → 서비스 → 라우터 → 앱 조립 → 시드 → 테스트 → 문서)로 진행하여 하위 의존이 상위보다 먼저 존재하도록 한다.

### Step 1 — 프로젝트 스캐폴딩 (Project Structure Setup, greenfield)
- [x] `backend/pyproject.toml` — 프로젝트 메타, deps(런타임/dev), ruff·mypy·pytest 설정 (tech-stack §2, Q12)
- [x] `backend/requirements.txt` — 버전 lock(핀) (SECURITY-10)
- [x] `backend/.env.example` — env 변수 전체(§tech-stack §4) + 주석
- [x] `backend/README.md` — 설치·env·기동(uvicorn)·시드·테스트 실행 방법
- [x] 패키지 `__init__.py` 골격 생성(app, db, schemas, security, middleware, repositories, services, routers, tests)
- [x] `backend/.gitignore` 항목(예: `*.db`, `.env`, `__pycache__`) — 루트 .gitignore 보완 필요 시

### Step 2 — 설정·시각·로깅 기반 (Config / Time / Logging)
- [x] `app/config.py` — Pydantic Settings: JWT_SECRET/ISSUER/TTL, CORS_ORIGINS, DB_PATH, RATE_LIMIT_*, BCRYPT_COST, MAX_BODY_BYTES, busy_timeout (logical-components §6)
- [x] `app/time_utils.py` — `now_kst()`, ISO8601(+09:00) 직렬화 헬퍼 (NFR-D-03)
- [x] `app/logging_config.py` — JSON 포맷터 + request_id 필드 + 민감필드(password/token/PIN) 마스킹 (C3, SECURITY-03)

### Step 3 — DB 엔진·모델·스키마·세션 (Repository Layer 기반: DB)
- [x] `app/db/engine.py` — 단일 Engine + `connect` 이벤트 훅으로 PRAGMA(WAL/foreign_keys=ON/busy_timeout=5000), `check_same_thread=False`, QueuePool (C9, §2)
- [x] `app/db/models.py` — 전 엔티티 ORM 매핑: Store/AdminUser/Table/TableSession/Category/Menu/Order/OrderItem/OrderHistory/OrderHistoryItem/AuditLog/LoginAttempt. CHECK(enum)·UNIQUE((store_id,order_date,order_seq) 등)·인덱스(domain-entities §2/§4)
- [x] `app/db/schema.py` — 기동 시 `create_all`(Q4=A, Alembic 없음)
- [x] `app/db/session.py` — `get_db()` 요청 단위 세션(try/finally close, C10) + `@retry_on_write_conflict`(max 3, backoff 10/20/40ms, SQLITE_BUSY/UNIQUE, C11) + `run_in_transaction` 헬퍼

### Step 4 — DB 계층 Unit Test (Repository Layer Unit Testing 일부) + 요약
- [x] (DB 관련 단위 검증은 Step 12 통합/PBT에 포함 — 별도 파일 생성 없이 conftest 픽스처에서 create_all 검증)
- [x] **Repository Layer Summary(부분)**: `aidlc-docs/construction/backend-api/code/repository-layer-summary.md`는 Step 8 이후 종합 작성

### Step 5 — Pydantic 스키마 (계약 §3 미러 + 입력 상한 Q9)
- [x] `app/schemas/common.py` — `PageMeta`, `ErrorResponse`, `ErrorCode`(리터럴), 페이지네이션 쿼리(page≥1, size 1..100 BR-VAL-06)
- [x] `app/schemas/auth.py` — AdminLoginRequest/Response, TableLoginRequest/Response (계약 §2.1, §4)
- [x] `app/schemas/menu.py` — Category, Menu (계약 §3.2, 가용성 필드 없음 Q10=A)
- [x] `app/schemas/order.py` — OrderItemInput(quantity≥1), OrderItem, Order, CreateOrderRequest(items≤100), OrdersListResponse(items/page_meta/server_time), StatusUpdateRequest(enum), DeleteResult
- [x] `app/schemas/table.py` — SetupRequest(table_no≤20, PIN 4~6 숫자 BR-VAL-03), SetupResponse, TableCard(has_new 필수), OrderPreview, DashboardResponse(tables/server_time), CompleteResult
- [x] `app/schemas/history.py` — HistoryEntry, HistoryListResponse
- [x] 입력 상한(Q9): items≤100, quantity 1..999, table_no≤20, name≤100, description≤500 (BR-VAL-02)

### Step 6 — 보안 컴포넌트 (Security: jwt/hashing/ratelimit/deps)
- [x] `app/security/hashing.py` — passlib[bcrypt] `hash_password`/`verify_password`, cost=env (BR-AUTH-01)
- [x] `app/security/jwt.py` — `issue_jwt(claims, ttl)`/`verify_jwt(token)` HS256, iss/exp/typ 검증, 만료→TOKEN_EXPIRED (FD §2.3, 계약 §4)
- [x] `app/security/ratelimit.py` — 인메모리 슬라이딩 윈도우 RateLimiter: check/record_failure, lazy-remove+sweep+key cap eviction, Lock 스레드 안전 (C8, §6)
- [x] `app/security/deps.py` — `get_claims`→`require_admin`/`require_table`→`get_store_scope`, deny-by-default, typ 불일치 403 (C7, §5, BR-AUTHZ)

### Step 7 — 미들웨어·에러 핸들러 (API Layer 횡단 관심사)
- [x] `app/errors.py` — `AppError` 계층(ValidationError/AuthError/ForbiddenError/NotFoundError/ConflictError/TotalMismatchError/RateLimitedError) 각 (http_status, error_code) 보유 + 전역 핸들러 3종(AppError / RequestValidationError→400 / Exception→500) (C1, §4, 계약 §1.3)
- [x] `app/middleware/request_id.py` — request_id contextvar 생성/전파 (C2)
- [x] `app/middleware/logging.py` — 요청/응답 JSON 로깅 + 보안 이벤트 (C3)
- [x] `app/middleware/body_size.py` — 본문 ≤1MB, 초과 413/400 (C5, BR-VAL-05)
- [x] `app/middleware/security_headers.py` — X-Content-Type-Options: nosniff 등 (C6)

### Step 8 — Repository 계층 (파라미터화 쿼리, SECURITY-05)
- [x] `app/repositories/store_repo.py` — get_store, get_admin(store_id, username)
- [x] `app/repositories/table_repo.py` — get_table_by_no, upsert_table, create_session, get_active_session, end_session, list_tables
- [x] `app/repositories/menu_repo.py` — list_categories, list_menus, get_menu
- [x] `app/repositories/order_repo.py` — insert_order(+items), max_order_seq, get, update_status, soft_delete, list_by_session, sum_table_total, recent_orders, count_by_status
- [x] `app/repositories/history_repo.py` — insert_history(+items), query(filters)
- [x] AuditLog 기록 헬퍼(공용) — actor/action/target/before/after/request_id (BR-AUD-01)
- [x] **Repository Layer Summary**: `aidlc-docs/construction/backend-api/code/repository-layer-summary.md`

### Step 9 — Service 계층 (트랜잭션 경계·비즈니스 로직)
- [x] `app/services/auth_service.py` — authenticate_admin/authenticate_table (RateLimiter→bcrypt→LoginAttempt→JWT, 일반화 401, 세션 검증) (FD §2)
- [x] `app/services/menu_service.py` — list_menu, get_menu (FD §3)
- [x] `app/services/order_service.py` — create_order(채번 MAX+1 + 스냅샷 + 총액 재검증, 단일 tx + retry), list_session_orders, update_status(자유 전이 Q1=B + 감사), delete_order(soft-delete + 총액 재계산 + 감사, 단일 tx), recalculate_table_total (FD §4, PBT 대상 §8)
- [x] `app/services/session_service.py` — setup_table(활성 세션 재-setup 409 Q5=C), get_or_start_session(만료 검사 Q7=A), get_dashboard(카드 집계·has_new=false), complete_session(미완료 주문 409 Q2=B + 이력 이관 + 세션 종료, 단일 tx) (FD §5)
- [x] `app/services/history_service.py` — archive_session, list_history (FD §6)
- [x] **Business Logic Summary**: `aidlc-docs/construction/backend-api/code/business-logic-summary.md`

### Step 10 — Router 계층 (API Layer Generation, 계약 §2.6)
- [x] `app/routers/auth.py` — `POST /api/admin/login`(🔓), `POST /api/table/login`(🔓)
- [x] `app/routers/menu.py` — `GET /api/menu`(🔑T/A), `GET /api/menu/{menu_id}`(🔑T/A)
- [x] `app/routers/order.py` — `POST /api/orders`(🔑T), `GET /api/orders`(🔑T), `PATCH /api/orders/{order_id}/status`(🔑A), `DELETE /api/orders/{order_id}`(🔑A)
- [x] `app/routers/table.py` — `POST /api/tables/{table_id}/setup`(🔑A), `GET /api/tables/dashboard`(🔑A), `POST /api/tables/{table_id}/complete`(🔑A)
- [x] `app/routers/history.py` — `GET /api/history`(🔑A)
- [x] 모든 보호 라우트에 인증 의존성 명시(deny-by-default), 상태코드·응답 모델을 계약과 일치
- [x] **API Layer Summary**: `aidlc-docs/construction/backend-api/code/api-layer-summary.md`

### Step 11 — 앱 조립·시드 (Main App / Deployment Artifacts)
- [x] `app/main.py` — FastAPI 앱 생성, 미들웨어 체인 등록(아우터→이너: 에러핸들러→request_id→로깅→CORS→본문크기→보안헤더, logical-components §2), 라우터 등록, 기동 시 create tables (§7)
- [x] `app/db/seed.py` — 단일 매장 시드(Store, AdminUser bcrypt≥8자, Table 샘플, Category/Menu 샘플). 시드 비번은 env/인자 주입(BR-AUTH-06, 하드코딩 금지)
- [x] `backend/.env.example` 최종 점검(모든 참조 변수 포함)

### Step 12 — 테스트 (Unit PBT + Integration)
- [x] `tests/conftest.py` — 임시 파일/인메모리 DB, create_all, 시드, TestClient, 관리자·테이블 토큰 픽스처
- [x] `tests/unit/test_pricing_pbt.py` — Hypothesis: line_amount=price*qty≥0, total_amount=Σ 순서무관 (PBT-03, NFR-T-01)
- [x] `tests/unit/test_order_number_pbt.py` — Hypothesis: `{store}-{YYYYMMDD}-{NNN}` format↔parse 라운드트립 (PBT-02)
- [x] `tests/unit/test_serialization_pbt.py` — Hypothesis: Pydantic 직렬화 라운드트립(스냅샷 필드 보존) (PBT-02)
- [x] `tests/integration/test_auth.py` — 관리자/테이블 로그인 성공·실패(일반화 401)·rate limit 429·typ 분리 403
- [x] `tests/integration/test_order_flow.py` — 주문 생성(채번·총액·스냅샷)·빈 장바구니 400·목록 폴링(server_time)·상태 변경·soft-delete + 총액 재계산
- [x] `tests/integration/test_session_flow.py` — setup(재-setup 409)·dashboard 집계(has_new=false)·complete(미완료 409, 이력 이관·총액 0)
- [x] `tests/integration/test_security.py` — deny-by-default 401·IDOR 404/403·에러 응답 형식(§1.3)·본문 크기 제한
> 테스트는 Build & Test 단계에서 실행. 본 단계는 생성만.

### Step 13 — 문서 종합 (Documentation Generation)
- [x] `aidlc-docs/construction/backend-api/code/README-generation.md` — 생성 파일 인벤토리(경로·책임), 계약 정합성 요약, 실행/시드/테스트 요약, Security/PBT 준수 요약

---

## 3. 매핑 요약 (계약·NFR·보안 추적성)

| 관심사 | 반영 위치 | 근거 |
|---|---|---|
| 계약 §2 엔드포인트 12개 | Step 10 routers | integration-contract §2.6 |
| 계약 §3 공유 모델(필드명 동일) | Step 5 schemas | §3, Q10=A(가용성 없음), has_new 필수=false |
| 계약 §4 JWT 클레임 | Step 6 jwt/deps | §4 (변경 없음) |
| 계약 §1.3 표준 에러 | Step 7 errors | §1.3, SECURITY-15 |
| 채번 MAX+1 + UNIQUE + retry | Step 9 order_service, Step 3 session | FD §4.2, NFR §3 |
| 트랜잭션 원자성(fail closed) | Step 9 services + Step 3 tx 헬퍼 | FD §7, NFR §3 |
| bcrypt·rate limit·서버측 만료 | Step 6 security | SECURITY-12, NFR §6 |
| deny-by-default·IDOR·typ | Step 6 deps + Step 10 routers | SECURITY-08, NFR §5 |
| PRAGMA WAL/FK/busy_timeout | Step 3 engine | NFR §2 |
| 미들웨어 체인·request_id·마스킹 | Step 2/7 + Step 11 main | NFR §7 |
| PBT(금액·채번·직렬화) | Step 12 unit tests | PBT Partial, NFR-T-01 |
| 감사 로깅 | Step 8 헬퍼 + Step 9 services | SECURITY-13, BR-AUD |

---

## 4. 완료 기준 (Completion Criteria)
- 본 계획서 승인 후 Part 2에서 Step 1~13 전부 [x].
- 계약 §2/§3/§4와 일치하는 엔드포인트·모델·클레임(OpenAPI가 계약과 일치).
- 모든 코드·테스트·lock 파일·시드·문서 생성(테스트 실행은 Build & Test).
- Security Baseline 블로킹 결함 없음(설계 단계 준수 사항 코드 반영).
- 계약 §3/§4 변경 없음.
