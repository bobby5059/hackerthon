# Tech Stack Decisions — Unit 1 (backend-api)

> backend-api 실행 서비스(FastAPI + SQLite, 로컬 배포)의 툴체인 결정.
> 사용자 답변: **Q1~Q12 전부 추천안(A)** (2026-08-31).
> 확장: Security Baseline(Yes), PBT Partial(Hypothesis). 정합: `shared` tech-stack(ruff/mypy 대응 없음 — TS 유닛이므로 툴체인 독립, CI 게이트 정책만 정합).

---

## 1. 결정 요약

| # | 항목 | 결정 | 비고 |
|---|---|---|---|
| Q1 | 웹 프레임워크/런타임 | **FastAPI + Uvicorn + Pydantic v2** | 비동기 폴링·자동 OpenAPI(계약 SSOT)·검증 통합 |
| Q2 | Python 버전 | **Python 3.12** | 최신 안정·타이핑/성능 개선 |
| Q3 | DB 접근 계층 | **SQLAlchemy 2.0 (Core/ORM) + 세션 트랜잭션** | 트랜잭션·연결·파라미터 바인딩 안전, 테스트 용이 |
| Q4 | 스키마 관리 | **기동 시 create tables + 시드 스크립트** | Alembic 없음(로컬 MVP 단순), 고정 스키마 |
| Q5 | SQLite PRAGMA | **WAL + `foreign_keys=ON` + `busy_timeout=5000ms`** | 동시 읽기 향상·FK 강제·잠금 대기 |
| Q6 | JWT | **PyJWT + HS256**, 서명키 env `JWT_SECRET` | 관리자 16h / 테이블 세션 잔여 TTL(≤16h) |
| Q7 | 해싱 | **passlib[bcrypt]** | cost factor 설정, 관리자 8자↑/PIN 4~6자리 |
| Q8 | 로그인 rate limit | **인메모리 슬라이딩 윈도우**, 5회 실패/5분 → 429, cooldown 5분 | `LoginAttempt` 테이블은 감사 기록 |
| Q9 | 입력 상한 | items≤100, quantity 1..999, table_no≤20, name≤100, description≤500, 본문≤1MB | SECURITY-05 최소 상한 |
| Q10 | CORS | env `CORS_ORIGINS`, 기본 customer `:5173` / admin `:5174` | 와일드카드 금지 |
| Q11 | 성능/확장 | 단일 Uvicorn 워커, 수평 확장 없음, p95<300ms, 폴링 2s | 가용성/DR N/A(로컬) |
| Q12 | 테스트/로깅/CI | pytest + Hypothesis + httpx, JSON 로깅+request_id, 보안 헤더 미들웨어, ruff+mypy | 전역 커버리지 게이트 없음 |

---

## 2. 의존성 (버전은 Code Generation에서 lock — SECURITY-10)

**dependencies (런타임)**
```
fastapi
uvicorn[standard]
pydantic (v2)
sqlalchemy (2.0)
pyjwt
passlib[bcrypt]
python-dotenv        # 환경설정(.env) 주입
```

**devDependencies (테스트/품질)**
```
pytest
hypothesis           # PBT Partial (순수 계산·직렬화 라운드트립)
httpx                # TestClient 통합 테스트
ruff                 # lint + format
mypy                 # 정적 타입 검사
```
> 정확한 버전은 Code Generation에서 lock 파일(`requirements.txt` 핀 또는 `uv.lock`)로 고정. 취약점 스캔(SECURITY-10)은 CI 설정 시 포함.

---

## 3. 프로젝트 구성 (워크스페이스 루트 하위 `backend/`)

```
backend/
├── pyproject.toml         # deps, ruff/mypy 설정
├── requirements.txt       # 버전 lock (또는 uv.lock)
├── .env.example           # JWT_SECRET, CORS_ORIGINS, DB_PATH 등
├── app/
│   ├── main.py            # FastAPI app, 미들웨어(CORS/request_id/보안헤더/에러핸들러) 등록
│   ├── config.py          # 환경설정 로딩(Pydantic Settings)
│   ├── db/
│   │   ├── engine.py      # SQLAlchemy engine + PRAGMA(WAL/foreign_keys/busy_timeout)
│   │   ├── models.py      # ORM 매핑(Store/Table/Session/Menu/Order/OrderItem/OrderHistory/LoginAttempt/AuditLog)
│   │   ├── schema.py      # create tables (기동 시)
│   │   └── seed.py        # 단일 매장 시드 스크립트
│   ├── schemas/           # Pydantic v2 요청/응답 모델(계약 §3 미러, 입력 상한 Q9)
│   ├── security/
│   │   ├── jwt.py         # PyJWT HS256 발급/검증(typ/exp/iss)
│   │   ├── hashing.py     # passlib[bcrypt]
│   │   ├── ratelimit.py   # 인메모리 슬라이딩 윈도우(5/5min, cooldown 5min)
│   │   └── deps.py        # 인증/인가 의존성(deny-by-default, IDOR, store 스코프)
│   ├── routers/           # auth/menu/order/table/history
│   ├── services/          # 트랜잭션 경계(채번/삭제/이용완료), 총액 재검증
│   ├── repositories/      # 파라미터화 쿼리
│   └── logging_config.py  # 구조화 JSON 로깅 + request_id + 마스킹
└── tests/
    ├── unit/              # PBT(Hypothesis): 금액 계산·주문번호·직렬화 라운드트립
    └── integration/       # httpx TestClient: 인증/주문/세션/보안 경로
```
> 애플리케이션 코드는 **워크스페이스 루트**에 위치(문서는 aidlc-docs/ 전용). 정확한 트리는 Code Generation에서 확정.

---

## 4. 환경설정 변수 (env)

| 변수 | 용도 | 기본값(로컬) |
|---|---|---|
| `JWT_SECRET` | HS256 서명키(BR-AUTH-06) | (필수, .env 주입) |
| `JWT_ISSUER` | 토큰 `iss` | `table-order` |
| `ADMIN_TOKEN_TTL_HOURS` | 관리자 토큰 TTL | 16 |
| `CORS_ORIGINS` | 허용 오리진(콤마 구분) | `http://localhost:5173,http://localhost:5174` |
| `DB_PATH` | SQLite 파일 경로 | `./table_order.db` |
| `RATE_LIMIT_MAX` / `RATE_LIMIT_WINDOW_SEC` / `RATE_LIMIT_COOLDOWN_SEC` | 로그인 제한 | 5 / 300 / 300 |
| `BCRYPT_COST` | bcrypt cost factor | 12 |

---

## 5. 근거·트레이드오프

- **FastAPI + Pydantic v2(Q1=A)**: 자동 OpenAPI로 계약 SSOT(§7) 자동 유지, 요청 검증(입력 상한 Q9)과 통합. 폴링 엔드포인트 비동기 처리.
- **SQLAlchemy 2.0(Q3=A)**: 세션 기반 트랜잭션으로 다중 쓰기 원자성(채번 MAX+1, soft-delete+총액재계산, 이용완료 이력이관) 보장. 파라미터 바인딩으로 SECURITY-05 안전. `sqlite3` 직접(B) 대비 트랜잭션·테스트 용이.
- **create tables + 시드(Q4=A)**: 고정 스키마 단일 매장 MVP에 Alembic 불필요. 프로덕션·스키마 진화 필요 시 Alembic 도입으로 확장.
- **WAL + PRAGMA(Q5=A)**: 폴링(다중 읽기)과 쓰기 트랜잭션 병행 시 잠금 대기(`busy_timeout`)로 채번 경합 안전성 보강, FK 무결성 강제.
- **PyJWT + passlib(Q6/Q7=A)**: 표준 라이브러리로 HS256 서명·bcrypt 해시. 서명키는 env 주입(하드코딩 금지).
- **인메모리 rate limit(Q8=A)**: 로컬 단일 인스턴스 MVP에 적합(재기동 시 초기화 허용). `LoginAttempt` 테이블로 감사 병행. 다중 인스턴스 전환 시 공유 저장소(예: Redis) 필요.
- **ruff + mypy + pytest/Hypothesis/httpx(Q12=A)**: `shared`의 CI 정책(lint+typecheck+test, 전역 커버리지 게이트 없음)과 정합. PBT는 Partial 범위(순수 계산·직렬화)에 한정.

---

## 6. 다음 단계

본 결정을 근거로 **NFR Design(backend-api)** 에서 미들웨어 체인(CORS/request_id/보안헤더/에러핸들러)·트랜잭션 경계·rate limit·로깅 구조를 설계에 반영하고, 이후 **Code Generation(backend-api)** 에서 실제 코드·설정·테스트·lock 파일을 생성한다.

> **주의**: 본 단계는 계약 §3(공유 모델)·§4(클레임)를 변경하지 않는다. 툴체인·구현 NFR·FD 유보 수치만 확정.
