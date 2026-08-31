# Logical Components — Unit 1 (backend-api)

> AI-DLC CONSTRUCTION / Unit 1 (backend-api) / NFR Design.
> 목적: NFR 패턴(`nfr-design-patterns.md`)을 실현하는 **논리 컴포넌트**의 책임·상호작용·설정 파라미터를 확정한다. 실제 코드/파일은 Code Generation에서 생성.
> 근거: `nfr-design-patterns.md`, `tech-stack-decisions.md`(§3 프로젝트 구성/§4 env), `nfr-requirements.md`, FD.
> 사용자 답변: **Q1~Q6 전부 추천안(A)**. 계약 §3(모델)·§4(클레임) 변경 없음.

---

## 1. 컴포넌트 목록 (책임 · 설정)

| # | 컴포넌트 | 유형 | 책임 | 설정(env/상수) | 근거 |
|---|---|---|---|---|---|
| C1 | `ErrorHandler` | 예외 핸들러 | 도메인 예외(`AppError`)·Pydantic·미분류 예외를 표준 응답으로 변환, request_id 포함 | — | §4, NFR-BE-R-03 |
| C2 | `RequestIdMiddleware` | 미들웨어 | 요청당 UUID 생성 → contextvar set, 응답 헤더/로그/에러에 전파 | — | §7, NFR-BE-S-07 |
| C3 | `LoggingMiddleware` + `JsonFormatter` | 미들웨어/필터 | 구조화 JSON 로깅(요청/응답), 민감필드 마스킹, 보안 이벤트 기록 | 마스킹 필드: password/token/PIN | §7, SECURITY-03/07/13 |
| C4 | `CORSMiddleware` | 미들웨어 | 명시 오리진 허용(와일드카드 금지) | `CORS_ORIGINS`(기본 `:5173`,`:5174`) | §7, NFR-BE-S-06 |
| C5 | `BodySizeLimitMiddleware` | 미들웨어 | 요청 본문 ≤1MB 강제, 초과 시 413/400 | `MAX_BODY_BYTES`(1MB) | §7, NFR-BE-S-04 |
| C6 | `SecurityHeadersMiddleware` | 미들웨어 | 적용 가능한 보안 헤더 부착(`X-Content-Type-Options: nosniff` 등) | — | §7, NFR-BE-S-09 |
| C7 | `AuthDependencies` | FastAPI 의존성 | `get_claims`/`require_admin`/`require_table`/`get_store_scope` — 인증·typ·스코프 | `JWT_SECRET`/`JWT_ISSUER`/TTL | §5, NFR-BE-S-01 |
| C8 | `RateLimiter` | 인메모리 서비스 | 로그인 슬라이딩 윈도우 5/5min→429, cooldown, 메모리 bound(sweep/eviction), 스레드 안전 | `RATE_LIMIT_MAX=5`/`_WINDOW_SEC=300`/`_COOLDOWN_SEC=300`, key cap | §6, NFR-BE-S-03 |
| C9 | `DbEngine` + `connect` 훅 | 인프라 | 단일 엔진, QueuePool, 연결 시 PRAGMA(WAL/foreign_keys/busy_timeout) 적용 | `DB_PATH`, busy_timeout=5000 | §2, NFR-BE-R-05 |
| C10 | `SessionProvider`(`get_db`) | FastAPI 의존성 | 요청 단위 세션 오픈/close(`try/finally`) | — | §1, NFR-BE-M-02 |
| C11 | `TransactionManager` | Service 헬퍼 | `with session.begin()` 원자 트랜잭션 경계 + 쓰기 경합 재시도(`@retry_on_write_conflict`) | max_retries=3, backoff 10/20/40ms | §1/§3, NFR-BE-R-01/02 |

> 도메인 서비스(Auth/Menu/Order/TableSession/History) 자체는 Functional Design 산출물에 정의됨. 본 문서는 **비기능 관심사(cross-cutting)** 컴포넌트에 집중한다.

---

## 2. 미들웨어 체인 흐름 (아우터 → 이너)

```
[Client]
   |
   v
+----------------------------+  ← 아우터(가장 먼저 진입 / 가장 나중 응답)
| C1 ErrorHandler            |  예외 캐치 → 표준 {error:{code,message,request_id}}
+----------------------------+
| C2 RequestIdMiddleware     |  request_id 생성 → contextvar
+----------------------------+
| C3 LoggingMiddleware       |  요청/응답 JSON 로깅 + 마스킹 + 보안 이벤트
+----------------------------+
| C4 CORSMiddleware          |  명시 오리진 검사
+----------------------------+
| C5 BodySizeLimitMiddleware |  본문 ≤1MB
+----------------------------+
| C6 SecurityHeadersMw       |  보안 헤더 부착
+----------------------------+
   |
   v
+----------------------------+  ← 이너(라우팅 진입)
| Router                     |
|  Depends: C7 AuthDeps      |  get_claims → require_admin/table → get_store_scope
|  Depends: C10 get_db       |  요청 단위 세션
|     |                      |
|     v                      |
|  Service                   |  C11 TransactionManager: with session.begin() (+retry)
|     |                      |
|     v                      |
|  Repository                |  param query (C9 엔진/세션)
+----------------------------+
```

- 공개 라우트(로그인 2종)만 C7 인증을 생략(deny-by-default 예외). 이 경로에서 C8 `RateLimiter`가 자격증명 검증 이전에 개입.

---

## 3. 로그인 경로 컴포넌트 상호작용 (C7·C8 + AuthService)

```
POST /api/auth/{admin|table}
   |
   v
Router (공개 — 인증 의존성 없음)
   |
   v
AuthService.authenticate_*
   |
   |-- 1. C8 RateLimiter.check(key)  --[cooldown 중]--> 429 RATE_LIMITED (C1 표준화)
   |        key = ADMIN:store:username / TABLE:store:table_no
   |
   |-- 2. Repository.get_admin/get_table  (C9 세션, param query)
   |
   |-- 3. bcrypt.verify(password, hash)   (존재 여부 무관 동일 경로 — 열거 방지)
   |
   |-- 4. LoginAttempt 기록 (감사) + 실패 시 C8.record_failure(key)
   |        C3 보안 이벤트 로깅(성공/실패)
   |
   |-- 5. 실패 → 401 UNAUTHORIZED(일반화)  /  성공 → issue_jwt(HS256)
   v
AdminToken / TableToken (계약 §4 클레임)
```

---

## 4. 쓰기 트랜잭션 경합 처리 (C10·C11·C9)

```
Service.create_order / delete_order / setup_table / complete_session
   |
   v
C11 @retry_on_write_conflict (max 3, backoff 10/20/40ms)
   |
   v
with session.begin():            ← 원자 경계(fail closed)
   ├─ 채번 MAX+1 (create_order)   FD §4.2
   ├─ insert / soft-delete / archive
   └─ AuditLog
   |
   ├─ SQLITE_BUSY / UNIQUE 위반? → 재시도(트랜잭션 재실행)
   ├─ 3회 소진 → rollback → 500 INTERNAL_ERROR (C1)
   └─ 도메인 예외(§4) → 즉시 전파(재시도 안 함) → C1 표준화

C9 엔진: busy_timeout=5000ms로 잠금 대기, WAL로 폴링 읽기 병행
```

- 재시도는 **멱등 재실행 가능한** 쓰기에 한정(채번은 재조회로 새 순번 확보).

---

## 5. request_id 전파 경로 (C2·C1·C3)

```
C2 RequestIdMiddleware: uuid4() → contextvar.set(request_id)
        |
        +--> C3 JsonFormatter: 모든 로그 레코드에 request_id 필드
        +--> C1 ErrorHandler: 에러 응답 error.request_id 에 삽입
        +--> 동기 라우트(스레드풀): contextvar 값이 워커 스레드에 전파되도록 설정
```

---

## 6. 설정 파라미터 요약 (env — tech-stack §4 정합)

| 변수 | 컴포넌트 | 기본값(로컬) |
|---|---|---|
| `JWT_SECRET` / `JWT_ISSUER` / `ADMIN_TOKEN_TTL_HOURS` | C7 | (필수) / `table-order` / 16 |
| `CORS_ORIGINS` | C4 | `http://localhost:5173,http://localhost:5174` |
| `DB_PATH` | C9 | `./table_order.db` |
| `RATE_LIMIT_MAX` / `RATE_LIMIT_WINDOW_SEC` / `RATE_LIMIT_COOLDOWN_SEC` | C8 | 5 / 300 / 300 |
| `BCRYPT_COST` | AuthService(hashing) | 12 |
| busy_timeout(PRAGMA) | C9 | 5000ms |
| max_retries / backoff | C11 | 3 / 10·20·40ms |
| MAX_BODY_BYTES | C5 | 1MB |

---

## 7. 컴포넌트 ↔ NFR 추적성

| 컴포넌트 | NFR-BE | SECURITY | 계약 |
|---|---|---|---|
| C1 ErrorHandler | R-03 | 09/15 | §1.3 |
| C2 RequestIdMiddleware | S-07 | 03/13 | — |
| C3 LoggingMiddleware | S-07 | 03/07/13/14 | — |
| C4 CORSMiddleware | S-06 | 08 | §8 |
| C5 BodySizeLimit | S-04 | 05 | — |
| C6 SecurityHeaders | S-09 | 04 | §8 |
| C7 AuthDependencies | S-01 | 08 | §4 |
| C8 RateLimiter | S-03 | 05/12 | — |
| C9 DbEngine+PRAGMA | R-05 | — | — |
| C10 SessionProvider | M-02 | — | — |
| C11 TransactionManager | R-01/02/04 | 15 | — |

> **주의**: 본 단계는 논리 컴포넌트·상호작용만 확정한다. 실제 파일 구조(`backend/app/...`, tech-stack §3)·코드·lock 파일·테스트는 **Code Generation(backend-api)** 에서 생성한다. 계약 §3/§4 변경 없음.
