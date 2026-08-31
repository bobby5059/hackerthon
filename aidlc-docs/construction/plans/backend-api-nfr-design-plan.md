# NFR Design Plan — Unit 1 (backend-api)

> AI-DLC CONSTRUCTION / Unit 1 (backend-api) / NFR Design.
> 전제: Functional Design + NFR Requirements 승인 완료(2026-08-31). 산출물 = `construction/backend-api/functional-design/`, `construction/backend-api/nfr-requirements/`.
> 적용 확장: **Security Baseline(Yes, 블로킹)**, **PBT(Partial — 순수 계산·직렬화 라운드트립)**, Resiliency(No).
> 정합성 기준: `integration-contract.md` v1.0(§1/§4/§5/§8), NFR Requirements(NFR-BE-*), tech-stack-decisions.md(Q1~Q12=A).
> **목적**: 이미 확정된 NFR/툴체인을 **실제 설계 패턴과 논리 컴포넌트**로 구체화한다 — 미들웨어 체인 구성·순서, 전역 에러 핸들러 분류, 트랜잭션/DB 세션 관리, rate limiter 컴포넌트, 인증/인가 의존성 체인, SQLite 쓰기 경합 재시도. 계약 §3(모델)·§4(클레임)는 변경하지 않는다.

---

## 1. NFR Design 실행 체크리스트

- [x] Step 1: NFR Requirements 분석 (성능/신뢰성/보안/유지보수/테스트/데이터 6영역 + tech-stack 검토 완료)
- [x] Step 2: 본 계획서 작성 (설계 패턴·논리 컴포넌트 초점)
- [x] Step 3: 명확화 질문 임베드 (아래 §3 — 5개 카테고리 전수 평가)
- [x] Step 4: 계획서 저장 (본 파일)
- [x] Step 5: 답변 수집 및 모호성 분석 (Q1~Q6 전부 추천안 A — 모호/애매 응답 없음, 후속 질문 불필요)
- [x] Step 6: 산출물 생성
  - [x] `construction/backend-api/nfr-design/nfr-design-patterns.md`
  - [x] `construction/backend-api/nfr-design/logical-components.md`
- [x] Step 7: 완료 메시지 제시 (2-옵션)
- [ ] Step 8: 명시적 승인 대기
- [ ] Step 9: 승인 기록(audit.md) + aidlc-state.md 갱신

---

## 2. 사전 확정된 NFR → 설계 반영 매핑 (재확인용)

> 아래는 NFR Requirements에서 이미 확정된 사항. NFR Design은 이를 **패턴/컴포넌트로 구체화**한다.

| 확정 NFR | 근거 | NFR Design에서 구체화할 패턴/컴포넌트 |
|---|---|---|
| 전역 에러 핸들러 + 일반화 에러(§1.3) | NFR-BE-R-03, SECURITY-15 | 예외 분류 체계(도메인 예외 → HTTP 매핑), `request_id` 포함 표준 응답 |
| 계층 분리 Router/Service/Repository, 트랜잭션 경계=Service | NFR-BE-M-02, FD §7 | DB 세션 수명주기(요청 단위) · 트랜잭션 컨텍스트 패턴 |
| 다중 쓰기 원자 트랜잭션 + fail closed | NFR-BE-R-01/04 | 트랜잭션 데코레이터/컨텍스트, 롤백·리소스 정리 규약 |
| 채번 경합 방지(UNIQUE + 직렬화) | NFR-BE-R-02 | SQLite 쓰기 경합/`SQLITE_BUSY` 재시도 패턴 |
| SQLite WAL + FK + busy_timeout | NFR-BE-R-05 | engine 초기화 · 연결(pool) 설정 · PRAGMA 적용 훅 |
| JWT 매요청 검증 · deny-by-default · IDOR | NFR-BE-S-01 | 인증/인가 FastAPI 의존성 체인(typ/store_id/소유권) |
| 로그인 rate limit 5회/5분→429, cooldown 5분 | NFR-BE-S-03 | 인메모리 슬라이딩 윈도우 컴포넌트(키 스킴·메모리 상한·eviction) |
| 입력 상한 + 본문 ≤1MB | NFR-BE-S-04 | Pydantic 검증 + 본문 크기 제한 미들웨어 |
| CORS 명시 오리진 · 보안 헤더 | NFR-BE-S-06/09 | 미들웨어 체인 구성·순서 |
| 구조화 JSON 로깅 + request_id + 마스킹 | NFR-BE-S-07 | request_id 전파(contextvar) · 로깅 미들웨어 · 마스킹 필터 |
| 성능 p95<300ms, 폴링 2s, 단일 워커 | NFR-BE-P-02, SC-01 | 라우트 실행 모델(sync/async) · 폴링 읽기 동시성(WAL) |

> 위 표의 좌측은 **확정**. 아래 §3 질문은 우측 "패턴/컴포넌트"에서 **설계 선택지가 실재하는 지점**에만 집중한다.

---

## 3. 명확화 질문 (`[Answer]:` 태그에 작성)

> **응답 방법**: 각 질문의 `[Answer]:` 뒤에 A/B/C 중 하나(또는 자유 서술)를 적어주세요.
> 모든 질문에 **추천안(★)** 을 그대로 쓰려면 "전부 추천안"이라고만 답해도 됩니다.
> (5개 필수 카테고리 — Resilience / Scalability / Performance / Security / Logical Components — 를 전수 평가. Scalability는 로컬 단일 워커로 이미 N/A 확정이라 별도 질문 없이 §4에 명시.)

### ⚙️ 라우트 실행 · DB 세션 (Performance / Logical Components)

#### Q1. 라우트 실행 모델 + DB 세션 수명주기
FastAPI는 async/sync 라우트를 모두 지원하고, tech-stack은 **동기** SQLAlchemy 2.0(Q3=A)로 확정되었습니다. 폴링(다중 읽기)과 쓰기 트랜잭션이 공존합니다. 실행 모델과 세션 관리 패턴은?
- A. ★ **동기 `def` 라우트 + Starlette 스레드풀 오프로딩 + 요청 단위 세션(FastAPI `Depends`로 세션 주입, 요청 종료 시 close)**. 동기 SQLAlchemy와 자연 정합, 트랜잭션은 Service 계층에서 `with session.begin()`. SQLite는 쓰기 직렬화되므로 스레드풀 동시성으로 폴링 읽기 처리 충분.
- B. `async def` 라우트 + `run_in_threadpool`로 동기 DB 호출 래핑(비동기 표면, 내부 동기)
- C. 기타(직접 기술)

[Answer]: A

#### Q2. DB 엔진 / 커넥션 풀 구성 (SQLite + WAL, Logical Components)
단일 워커·다중 스레드(스레드풀) 환경에서 SQLite 연결 관리 방식은? (WAL은 다중 읽기 동시성 허용)
- A. ★ **단일 엔진 + QueuePool(기본, `check_same_thread=False`) + 연결 시 PRAGMA(WAL/foreign_keys/busy_timeout) 자동 적용(`connect` 이벤트 훅)**. 읽기 병행·쓰기 직렬화, `busy_timeout`으로 잠금 대기.
- B. `StaticPool`(단일 공유 연결) — 직렬화 강함, 폴링 동시성 저하 가능
- C. 기타(직접 기술)

[Answer]: A

### 🛡️ 신뢰성 / 경합 (Resilience)

#### Q3. 쓰기 경합 · `SQLITE_BUSY` 재시도 패턴
FD §4.2: 채번 MAX+1은 쓰기 트랜잭션 직렬화로 보호하고 `(store_id, order_date, order_seq)` UNIQUE로 이중 안전. 락 경합/UNIQUE 위반 시 처리는? (Resiliency 확장은 No지만, 로컬 SQLite 경합은 실존)
- A. ★ **트랜잭션 단위 제한적 재시도**: `SQLITE_BUSY`/UNIQUE 위반 시 최대 **3회** 재시도(짧은 지수 백오프, 예 10/20/40ms) → 그래도 실패면 fail closed(500 `INTERNAL_ERROR`, 롤백). 재시도는 채번·삽입 등 **멱등 재실행 가능한** 쓰기에 한정.
- B. 재시도 없음 — 최초 실패 즉시 fail closed(단순, 로컬 부하 낮음 전제)
- C. 기타(재시도 횟수/백오프/대상 직접 기술)

[Answer]: A

#### Q4. 전역 에러 핸들러 — 예외 분류 → HTTP 매핑 구조
NFR-BE-R-03/계약 §1.3: 모든 예외를 `{error:{code,message,request_id}}`로 정규화하고 내부 정보 미노출. 예외 체계는?
- A. ★ **도메인 예외 계층 정의**(`AppError` 기반: `ValidationError`/`AuthError`/`ForbiddenError`/`NotFoundError`/`ConflictError`/`RateLimitedError` 등) → 각 예외가 `(http_status, error_code)` 보유 → 전역 핸들러가 표준 응답 변환. 미분류/예상외 예외는 500 `INTERNAL_ERROR`(스택 미노출, 서버 로그에만 상세). Pydantic 검증 오류 핸들러는 400 `VALIDATION_ERROR`로 매핑.
- B. 예외 계층 없이 라우트/서비스에서 직접 `HTTPException` 발생 + 단일 핸들러로 형식만 통일
- C. 기타(직접 기술)

[Answer]: A

### 🔐 보안 패턴 (Security)

#### Q5. 인증 / 인가 의존성 체인 (deny-by-default · typ · IDOR)
NFR-BE-S-01, FD §1/§2.3: JWT 매요청 검증, typ 불일치 403, 매장·객체 소유권(IDOR) 검증. FastAPI 의존성으로 어떻게 구성?
- A. ★ **재사용 의존성 체인**: `get_claims`(Bearer 파싱·서명/exp/iss 검증·실패 401) → `require_admin`/`require_table`(typ 검사·불일치 403) → `get_store_scope`(store_id 주입) → Service 계층 `assert_owns_resource`(객체 조회 후 store_id 소유권 재검증·위반 시 404 은닉 또는 403, defense in depth). 보호 라우트는 의존성 미지정 불가(deny-by-default) — 공개 라우트(로그인 2종)만 명시적 예외.
- B. 단일 통합 의존성(`current_principal`)에서 typ·스코프까지 일괄 처리(라우트별 파라미터로 요구 typ 전달)
- C. 기타(직접 기술)

[Answer]: A

#### Q6. 로그인 Rate Limiter — 인메모리 컴포넌트 설계 (Security / Logical Components)
NFR-BE-S-03: 인메모리 슬라이딩 윈도우 5회/5분→429, cooldown 5분. 무한 메모리 증가는 SECURITY-05 위반이므로 **메모리 상한/정리**가 필요합니다. 컴포넌트 설계는?
- A. ★ **키 = `{scope}:{store_id}:{identifier}`(ADMIN:store:username / TABLE:store:table_no), 값 = 실패 타임스탬프 deque + cooldown_until.** 접근 시 윈도우 밖 항목 lazy 제거 + **주기적 sweep**(만료 키 정리) + **키 수 상한(cap, 초과 시 가장 오래된 키 eviction)** 으로 메모리 bound. 단일 워커 인메모리(재기동 시 초기화 허용), `LoginAttempt` 테이블은 별도 감사 기록. 스레드 안전(lock) 보장.
- B. 고정 윈도우 카운터(윈도우 경계마다 리셋) — 단순하나 경계 버스트 허용
- C. 기타(직접 기술)

[Answer]: A

---

## 4. 질문 없이 확정하는 설계 (NFR/계약에서 이미 결정 — 재질문 안 함)

- **미들웨어 체인 순서**(아우터→이너): ① 에러 핸들러(예외 캐치·표준화) → ② request_id 생성/전파(contextvar) → ③ 구조화 JSON 로깅(요청/응답, 민감정보 마스킹) → ④ CORS(명시 오리진) → ⑤ 본문 크기 제한(≤1MB, 초과 시 413/400) → ⑥ 보안 헤더(`X-Content-Type-Options: nosniff` 등) → 라우팅. (NFR-BE-S-06/07/09, R-03)
- **Scalability = N/A**: 단일 Uvicorn 워커, 수평 확장/DR/페일오버 없음(NFR-BE-SC-01/02). 다중 인스턴스 전환 시 rate limiter·세션 상태를 공유 저장소로 이전 필요(재검토 항목으로 문서화).
- **request_id 전파**: `contextvar` 기반으로 미들웨어에서 설정 → 로깅 포맷터·에러 응답에서 참조(스레드풀 오프로딩 시 전파 방식 명시).
- **입력 검증**: Pydantic v2 스키마가 1차(타입/길이/형식, 입력 상한 Q9), 본문 크기는 미들웨어가 방어. 파라미터화 쿼리는 SQLAlchemy 바인딩으로 보장(NFR-BE-S-05).
- **로깅 마스킹**: password/token/PIN 필드는 포맷터 단계에서 마스킹, 보안 이벤트(로그인 성공/실패·rate limit·인가 거부)는 별도 기록(NFR-BE-S-07).

> 위 항목에 이견이 있으면 §3의 해당 질문에 "기타"로, 또는 본 문단을 지목해 코멘트로 남겨주세요.

---

## 5. 산출물 (Step 6에서 생성)

- **`nfr-design-patterns.md`** — 미들웨어 체인(구성·순서), 전역 에러 핸들러/예외 분류, 트랜잭션·세션 수명주기, 쓰기 경합 재시도, 인증/인가 의존성 체인, rate limit 패턴, 로깅/request_id 전파, 성능(라우트 실행 모델·폴링 동시성) 패턴. 각 패턴에 근거 NFR·SECURITY 매핑.
- **`logical-components.md`** — 논리 컴포넌트 목록(ErrorHandler / RequestIdMiddleware / LoggingMiddleware / CORSMiddleware / BodySizeLimitMiddleware / SecurityHeadersMiddleware / AuthDependencies / RateLimiter / DbEngine+SessionProvider / TransactionManager)과 상호작용·책임·설정 파라미터(env 연동). 텍스트 기반 컴포넌트/흐름 다이어그램 포함.

> **주의**: 본 단계는 계약 §3(공유 모델)·§4(클레임)를 변경하지 않는다. 구현 패턴·논리 컴포넌트만 확정하며, 실제 코드/설정은 Code Generation에서 생성.
