# NFR Design Patterns — Unit 1 (backend-api)

> AI-DLC CONSTRUCTION / Unit 1 (backend-api) / NFR Design.
> 목적: 승인된 NFR Requirements(NFR-BE-*) + tech-stack(Q1~Q12=A)를 **실제 설계 패턴**으로 구체화한다. 계약 §3(모델)·§4(클레임)는 변경하지 않는다.
> 사용자 답변(NFR Design 계획서): **Q1~Q6 전부 추천안(A)** (2026-08-31).
> 근거: `nfr-requirements.md`, `tech-stack-decisions.md`, `functional-design/business-logic-model.md`(FD §1/§4/§7), `integration-contract.md` v1.0(§1/§4/§5/§8).
> 확장: **Security Baseline(Yes, 블로킹)**, **PBT(Partial)**, Resiliency(No).

---

## 1. 라우트 실행 모델 · DB 세션 수명주기 (Q1=A) — Performance / Maintainability

**패턴**: 동기 `def` 라우트 + Starlette 스레드풀 오프로딩 + 요청 단위 세션(FastAPI `Depends` 주입).

- **실행 모델**: 라우트는 동기 `def`. FastAPI가 동기 라우트를 워커 스레드풀에서 실행하므로, 동기 SQLAlchemy 2.0(Q3=A) 호출이 이벤트 루프를 블로킹하지 않는다. 폴링(다중 읽기)은 스레드풀 동시성으로, 쓰기는 SQLite write lock으로 직렬화된다.
- **세션 수명주기(요청 단위)**: `get_db()` 의존성이 `sessionmaker`로 세션을 열고 `try/finally`로 요청 종료 시 반드시 `close()`. 세션은 요청 컨텍스트에 1:1 바인딩되어 스레드 간 공유되지 않는다(SQLite `check_same_thread=False` + 요청-스레드 격리).
- **트랜잭션 경계 = Service 계층**(NFR-BE-M-02, FD §7): Router는 검증·의존성만, Service가 `with session.begin(): ...`로 원자 트랜잭션을 수행한다. Repository는 파라미터화 쿼리만 담당(SECURITY-05).
- **읽기 경로**: 폴링/조회는 명시적 트랜잭션 없이 세션 read → WAL 덕분에 쓰기와 병행 가능(NFR-BE-P-02/04).

```
요청 → get_claims(의존성) → require_admin/table → get_db(세션 오픈)
     → Router → Service(with session.begin(): 원자 쓰기) → Repository(param query)
     → 응답 직렬화 → finally: session.close()
```

**근거 매핑**: NFR-BE-P-02(p95<300ms), NFR-BE-P-04(N+1 회피), NFR-BE-M-02(계층 분리), FD §1(공통 실행 컨텍스트).

---

## 2. DB 엔진 · 커넥션 풀 · PRAGMA (Q2=A) — Reliability / Logical Components

**패턴**: 단일 엔진 + `QueuePool`(기본) + `connect` 이벤트 훅으로 연결 시 PRAGMA 자동 적용.

- **엔진**: 애플리케이션 전역 단일 `Engine`. `connect_args={"check_same_thread": False}`로 스레드풀 사용 허용.
- **PRAGMA 적용 훅**(NFR-BE-R-05): SQLAlchemy `event.listen(engine, "connect", ...)`로 **모든 신규 물리 연결**에 아래를 적용.
  - `PRAGMA journal_mode=WAL` — 다중 읽기 동시성(폴링) 허용, 읽기가 쓰기를 블로킹하지 않음.
  - `PRAGMA foreign_keys=ON` — FK 무결성 강제(SQLite 기본 OFF이므로 연결마다 필수).
  - `PRAGMA busy_timeout=5000` — 쓰기 잠금 대기(즉시 `SQLITE_BUSY` 실패 방지), Q3 재시도와 함께 경합 완화.
- **풀 구성**: `QueuePool` 기본으로 다중 스레드 병행 읽기 지원. `StaticPool`(단일 공유 연결, B안)은 폴링 동시성을 떨어뜨려 채택하지 않음.
- **초기화 순서**: 엔진 생성 → connect 훅 등록 → `create tables`(기동 시, Q4=A, Alembic 없음) → 필요 시 시드.

**근거 매핑**: NFR-BE-R-05(WAL/FK/busy_timeout), NFR-BE-R-02(채번 경합 완화), NFR-BE-M-04(create tables + seed), tech-stack Q3/Q5.

---

## 3. 쓰기 경합 · `SQLITE_BUSY` 재시도 (Q3=A) — Reliability (Resiliency 확장 No이나 로컬 경합 실존)

**패턴**: 트랜잭션 단위 제한적 재시도(최대 3회, 지수 백오프) → 실패 시 fail closed.

- **대상**: `SQLITE_BUSY`(락 경합) 및 채번 UNIQUE 위반(`(store_id, order_date, order_seq)`). **멱등 재실행 가능한 쓰기**(채번+삽입 등, FD §4.2)에 한정.
- **정책**: 최대 3회 재시도, 백오프 예시 **10 / 20 / 40ms**(짧은 지수 백오프). 재시도 시 트랜잭션 전체를 재실행(채번 MAX+1 재조회 포함)하여 새 순번을 확보.
- **소진 시**: 롤백 후 500 `INTERNAL_ERROR`(fail closed, SECURITY-15). 부분 성공 없음.
- **적용 방식**: Service의 쓰기 트랜잭션을 감싸는 재시도 데코레이터/헬퍼(`@retry_on_write_conflict`). 재시도 대상 예외만 캐치하고, 그 외 도메인 예외(§4)는 즉시 전파.
- **비대상**: 읽기 트랜잭션, 비멱등 부수효과가 있는 쓰기는 재시도하지 않는다.

```
attempt 1 → SQLITE_BUSY/UNIQUE? → sleep 10ms → attempt 2 → 20ms → attempt 3 → 40ms
  → 여전히 실패 → rollback → 500 INTERNAL_ERROR (스택 미노출, 서버 로그에 상세)
```

**근거 매핑**: NFR-BE-R-01/02/04, FD §4.2(채번 직렬화 + UNIQUE 이중 안전), SECURITY-15(fail closed).

---

## 4. 전역 에러 핸들러 · 예외 분류 → HTTP 매핑 (Q4=A) — Reliability / Security

**패턴**: 도메인 예외 계층(`AppError`) → 각 예외가 `(http_status, error_code)` 보유 → 전역 핸들러가 표준 응답으로 변환.

- **예외 계층**:

| 예외 | HTTP | error_code | 사용처(FD/계약) |
|---|---|---|---|
| `ValidationError`(도메인) | 400 | `VALIDATION_ERROR` | 의미 검증 실패 |
| Pydantic `RequestValidationError` | 400 | `VALIDATION_ERROR` | 스키마 검증(전용 핸들러로 매핑) |
| `AuthError` | 401 | `UNAUTHORIZED` / `TOKEN_EXPIRED` | JWT 검증 실패/만료(FD §2.3) |
| `ForbiddenError` | 403 | `FORBIDDEN` | typ 불일치·소유권 위반(비은닉) |
| `NotFoundError` | 404 | `NOT_FOUND` | 부재·소유권 은닉(FD §3.2/§4.4) |
| `ConflictError` | 409 | `SESSION_CLOSED` 등 | 세션 상태 충돌(FD §4.1/§5.4) |
| `TotalMismatchError` | 422 | `TOTAL_MISMATCH` | 총액 재검증(FD §4.1) |
| `RateLimitedError` | 429 | `RATE_LIMITED` | 로그인 제한(FD §2.1) |
| (미분류/예상외) | 500 | `INTERNAL_ERROR` | 스택 미노출, 서버 로그에만 상세 |

- **표준 응답 형태**(계약 §1.3): `{"error": {"code": ..., "message": ..., "request_id": ...}}`. 내부 스택/파일 경로/DB 메시지 미노출(SECURITY-15/09).
- **핸들러 구성**: (1) `AppError` 핸들러 — 예외의 `http_status`/`error_code`로 표준 응답. (2) `RequestValidationError` 핸들러 — 400 `VALIDATION_ERROR`. (3) 포괄 `Exception` 핸들러 — 500 `INTERNAL_ERROR`(상세는 서버 로그로만).
- **request_id 주입**: 핸들러는 contextvar(§7)에서 `request_id`를 읽어 응답에 포함.

**근거 매핑**: NFR-BE-R-03(전역 정규화), 계약 §1.3, SECURITY-09/15.

---

## 5. 인증 / 인가 의존성 체인 (Q5=A) — Security (deny-by-default · typ · IDOR)

**패턴**: 재사용 FastAPI 의존성 체인 + Service 계층 소유권 재검증(defense in depth).

```
get_claims                → Bearer 파싱 + 서명(HS256)/exp/iss 검증 → 실패 401
   ↓                          (만료=TOKEN_EXPIRED, 그 외=UNAUTHORIZED)
require_admin / require_table → claims.typ 검사, 불일치 시 403 FORBIDDEN
   ↓
get_store_scope           → claims.store_id 주입(테넌트 스코프)
   ↓
Service.assert_owns_resource → 객체 조회 후 store_id 소유권 재검증
                              (위반 시 404 은닉 또는 403, FD §4.4/§4.5)
```

- **deny-by-default**: 모든 보호 라우트는 인증 의존성을 **필수 지정**. 미지정은 금지. **공개 라우트는 로그인 2종**(`POST /api/auth/admin`, `POST /api/auth/table`)만 명시적 예외.
- **typ 분리**: 관리자 API는 `require_admin`, 테이블 API는 `require_table`. typ 불일치 접근은 403(FD §2.3).
- **IDOR 방어**(SECURITY-08, BR-AUTHZ): 라우트 파라미터의 `order_id`/`table_id` 등은 `store_id` 스코프로 조회하고, 부재/타 매장은 404로 은닉. Service의 `assert_owns_resource`가 2차 방어선.
- **클레임 사용**: 계약 §4 클레임(`typ`, `store_id`, `table_id?`, `session_id?`)만 신뢰. 민감정보 미포함.

**근거 매핑**: NFR-BE-S-01, FD §1/§2.3/§4.4/§4.5, SECURITY-08, BR-AUTHZ-01~07. (계약 §4 클레임 구조 변경 없음.)

---

## 6. 로그인 Rate Limiter (Q6=A) — Security / Logical Components (인메모리, 메모리 bound)

**패턴**: 인메모리 슬라이딩 윈도우 + lazy 제거 + 주기적 sweep + 키 수 상한(eviction), 스레드 안전(lock).

- **키 스킴**: `{scope}:{store_id}:{identifier}`
  - 관리자: `ADMIN:{store_id}:{username}`
  - 테이블: `TABLE:{store_id}:{table_no}`
- **값**: 실패 타임스탬프 `deque` + `cooldown_until`.
- **판정**(NFR-BE-S-03): 윈도우(기본 300s) 내 실패 ≥ 5 → 429 `RATE_LIMITED`, cooldown 300s. cooldown 중 요청은 자격증명 검증 없이 즉시 429(FD §2.1 step 1).
- **메모리 bound**(SECURITY-05, 무한 증가 방지):
  - **lazy 제거**: 키 접근 시 윈도우 밖 타임스탬프 제거.
  - **주기적 sweep**: 만료 키(윈도우+cooldown 경과) 정리.
  - **키 수 상한(cap)**: 초과 시 가장 오래된 키 eviction.
- **동시성**: 스레드풀 환경이므로 `Lock`으로 원자 갱신.
- **감사 분리**: 인메모리는 판정용(재기동 시 초기화 허용). `LoginAttempt` 테이블은 감사 기록(FD §2.1 step 4).
- **파라미터**(env): `RATE_LIMIT_MAX=5` / `RATE_LIMIT_WINDOW_SEC=300` / `RATE_LIMIT_COOLDOWN_SEC=300`.

**근거 매핑**: NFR-BE-S-03, SECURITY-05/12, FD §2.1/§2.4, BR-AUTH-03.

---

## 7. 미들웨어 체인 · request_id · 로깅 (확정 — 재질문 없음) — Security

**미들웨어 체인 순서**(아우터 → 이너, NFR-BE-S-06/07/09, R-03):

```
① 에러 핸들러(예외 캐치·표준화, §4)
② request_id 생성/전파(contextvar)
③ 구조화 JSON 로깅(요청/응답, 민감정보 마스킹)
④ CORS(명시 오리진, 와일드카드 금지)
⑤ 본문 크기 제한(≤1MB, 초과 시 413/400)
⑥ 보안 헤더(X-Content-Type-Options: nosniff 등)
→ 라우팅
```

- **request_id 전파**(NFR-BE-S-07): `contextvar` 기반. 미들웨어에서 요청당 UUID 생성 → 로깅 포맷터·에러 응답(§4)에서 참조. 동기 라우트가 스레드풀에서 실행되므로 contextvar 값이 워커 스레드로 전파되도록 설정(요청 진입 시 set, 스레드 오프로딩 경계에서 유지).
- **로깅 마스킹**(SECURITY-03/07/13): `password`/`token`/`PIN` 필드는 포맷터 단계에서 마스킹. 보안 이벤트(로그인 성공·실패, rate limit 429, 인가 거부 401/403)는 별도 기록.
- **CORS**(NFR-BE-S-06): env `CORS_ORIGINS`(기본 `:5173`,`:5174`), 와일드카드 금지.
- **본문 크기**(NFR-BE-S-04): ≤1MB 미들웨어 방어. Pydantic v2가 필드 상한(items≤100, quantity 1..999 등) 1차 검증.
- **보안 헤더**(NFR-BE-S-09): API-only이므로 `X-Content-Type-Options: nosniff` 등 적용 가능한 헤더만. CSP 등은 N/A.

**근거 매핑**: NFR-BE-S-04/06/07/09, R-03, 계약 §8.

---

## 8. 성능 패턴 (확정) — Performance

- **라우트 실행 모델**: §1(동기 def + 스레드풀). 폴링 읽기는 WAL로 쓰기와 병행.
- **폴링 정합**(NFR-BE-P-01): 폴링/대시보드 응답에 `server_time`(Asia/Seoul) 포함, 주기 2000ms(`shared/PollingHook`).
- **페이지네이션**(NFR-BE-P-03): 목록 조회 `page`/`size`(1..100)로 응답 크기 제한.
- **쿼리 효율**(NFR-BE-P-04): 파라미터화 + 인덱스(store_id·session_id·created_at), N+1 회피(대시보드 카드 집계는 세션 스코프 합계/최근 N건 제한).
- **목표**: 단일 매장 정상 규모에서 p95<300ms(NFR-BE-P-02).

---

## 9. Scalability = N/A (확정, 재질문 없음)

- 단일 Uvicorn 워커, 수평 확장/DR/페일오버 없음(NFR-BE-SC-01/02).
- **다중 인스턴스 전환 시 재검토 항목**(문서화): rate limiter 상태(§6)와 세션/카운터를 공유 저장소(예: Redis)로 이전 필요. 현재 인메모리는 단일 워커 전제.

---

## 10. Security Baseline 준수 요약 (NFR Design 단계)

| SECURITY 규칙 | 상태 | 반영 위치 |
|---|---|---|
| 03 로깅 | Compliant | §7 마스킹·보안 이벤트 |
| 04 하드닝 헤더 | 부분(API-only) | §7 적용 가능한 헤더만, CSP N/A |
| 05 입력검증 상한 | Compliant | §6 rate limiter 메모리 bound, §7 본문/필드 상한 |
| 08 인가·IDOR·JWT 매요청 | Compliant | §5 의존성 체인·소유권 재검증 |
| 09 일반화 에러 | Compliant | §4 표준 응답·내부정보 미노출 |
| 11 보안 설계 | Compliant | §4/§5/§6 패턴 |
| 12 bcrypt·rate limit | Compliant | §6 수치·키 스킴 |
| 13 감사 | Compliant | §6 LoginAttempt, §7 보안 이벤트, FD AuditLog |
| 15 fail closed·전역 핸들러 | Compliant | §3 재시도 소진 시 롤백, §4 전역 핸들러 |
| 01/02/06/07 | N/A(로컬) | 클라우드/네트워크 인프라 없음 |

> **블로킹 findings: 없음.** 계약 §3(모델)·§4(클레임) 변경 없음. 실제 코드/설정/lock 파일은 Code Generation에서 생성.
