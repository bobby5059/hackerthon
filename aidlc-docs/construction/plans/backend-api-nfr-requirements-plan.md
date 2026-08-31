# NFR Requirements Plan — Unit 1 (backend-api)

> AI-DLC CONSTRUCTION / Unit 1 (backend-api) / NFR Requirements.
> 전제: Functional Design 승인 완료(2026-08-31). 산출물 = `aidlc-docs/construction/backend-api/functional-design/`.
> 적용 확장: **Security Baseline(Yes, 블로킹)**, **PBT(Partial — 순수 계산·직렬화 라운드트립, NFR-T-01)**, Resiliency(No).
> 정합성 기준: `integration-contract.md` v1.0(§1/§4/§5/§8), 요구사항 §2/§4, `shared` NFR/tech-stack 결정(툴체인 정합).
> backend-api는 **실행 서비스(FastAPI + SQLite, 로컬 배포)**이므로 NFR의 핵심은 **기술 스택/툴체인 확정**과 **보안(입력 상한·인증·rate limit)·성능(폴링)·신뢰성(트랜잭션)·테스트(PBT)** 이다.

---

## 1. NFR 실행 체크리스트

- [x] Step 1: Functional Design 분석 (엔티티/로직/규칙 3종 검토 완료)
- [x] Step 2: 본 계획서 작성
- [x] Step 3: 명확화 질문 임베드 (아래 §3)
- [x] Step 4: 계획서 저장 (본 파일)
- [x] Step 5: 답변 수집 및 모호성 분석 (Q1~Q12 전부 추천안 A, 모호성 없음)
- [x] Step 6: 산출물 생성
  - [x] `construction/backend-api/nfr-requirements/nfr-requirements.md`
  - [x] `construction/backend-api/nfr-requirements/tech-stack-decisions.md`
- [x] Step 7: 완료 메시지 제시 (2-옵션)
- [ ] Step 8: 명시적 승인 대기
- [ ] Step 9: 승인 기록(audit.md) + aidlc-state.md 갱신

---

## 2. 사전 도출된 NFR (요구사항/계약/FD에서 상속 — 재확인용)

| 영역 | backend-api 관련 NFR | 근거 |
|---|---|---|
| 성능 | 대시보드/주문 폴링 ~2초 목표, `server_time` 응답 포함 | NFR-P-01, 계약 §5.1 |
| 보안 | JWT 매요청 검증·IDOR·deny-by-default·CORS 명시 | SECURITY-08, 계약 §8 |
| 보안 | bcrypt 해시·로그인 rate limit(429)·서버측 세션 만료 | SECURITY-12, 계약 §8 |
| 보안 | 입력 검증(타입·길이·형식·본문크기)·파라미터화 쿼리 | SECURITY-05, FD BR-VAL-* |
| 보안 | 구조화 로깅(request_id·마스킹)·전역 에러 핸들러·fail closed | SECURITY-03/15, 계약 §1.3 |
| 신뢰성 | 다중 쓰기 원자 트랜잭션(채번/삭제/이용완료), 부분성공 금지 | FD §7, SECURITY-15 |
| 데이터 | 모든 시각 Asia/Seoul(+09:00), 금액 정수 KRW | NFR-D-03, 계약 §1.1 |
| 테스트 | 순수 계산·직렬화 라운드트립 PBT(Partial) | NFR-T-01, FD BLM §8 |

> 위는 이미 확정된 사항. 아래 질문은 **툴체인·구현 NFR·FD에서 유보한 구체 수치**에 집중한다.

---

## 3. 명확화 질문 (`[Answer]:` 태그에 작성)

> **응답 방법**: 각 질문의 `[Answer]:` 뒤에 A/B/C/D 중 하나(또는 자유 서술)를 적어주세요.
> 모든 질문에 **추천안(★)** 을 그대로 쓰려면 "전부 추천안"이라고만 답해도 됩니다.

### 🔧 기술 스택 (Tech Stack)

#### Q1. 웹 프레임워크 / 런타임
요구사항 Q2에서 백엔드는 Python(FastAPI 권장)으로 확정. 구체 스택은?
- A. ★ **FastAPI + Uvicorn + Pydantic v2** (비동기 폴링 엔드포인트·자동 OpenAPI(`/openapi.json`, 계약 SSOT §계약)·검증 통합)
- B. Flask + Gunicorn + 수동 검증
- C. 기타

[Answer]: A

#### Q2. Python 버전
- A. ★ **Python 3.12** (최신 안정, 성능·타이핑 개선)
- B. Python 3.11
- C. 기타

[Answer]: A

#### Q3. SQLite 접근 계층 (Repository 구현 방식)
FD의 다중 트랜잭션 경계(채번 MAX+1, soft-delete+총액재계산, 이용완료 이력이관)와 파라미터화 쿼리(SECURITY-05)를 만족해야 합니다.
- A. ★ **SQLAlchemy 2.0 (Core/ORM) + 세션 기반 트랜잭션** — 트랜잭션·연결 관리·파라미터 바인딩 안전, 테스트 용이
- B. 표준 라이브러리 `sqlite3` + 얇은 Repository (의존성 최소, 수동 트랜잭션/파라미터 바인딩)
- C. SQLModel (SQLAlchemy + Pydantic 통합)
- D. 기타

[Answer]: A

#### Q4. 스키마 관리 / 마이그레이션
MVP는 고정 스키마 + 단일 매장 시드(FD Q8=B). 관리 방식은?
- A. ★ **기동 시 스키마 생성(create tables) + 시드 스크립트** (Alembic 없음, 로컬 MVP 단순)
- B. Alembic 마이그레이션 도입
- C. 수기 `schema.sql` 실행
- D. 기타

[Answer]: A

#### Q5. SQLite 동시성/무결성 PRAGMA 설정
FD는 쓰기 트랜잭션 직렬화로 채번 안전성 확보(§4.2). 연결 설정은?
- A. ★ **WAL 모드 + `PRAGMA foreign_keys=ON` + `busy_timeout`(예: 5000ms)** (동시 읽기 향상·FK 강제·잠금 대기)
- B. 기본 설정(rollback journal) + `foreign_keys=ON`
- C. 기타

[Answer]: A

### 🔐 인증 / 보안 툴체인

#### Q6. JWT 라이브러리 / 알고리즘
FD §2.3: HS256 서명, 서명키 환경설정(BR-AUTH-06), 클레임은 계약 §4 한정.
- A. ★ **PyJWT + HS256, 서명키 env(`JWT_SECRET`)**, 관리자 16h / 테이블 세션 잔여 TTL(≤16h)
- B. python-jose + HS256
- C. RS256(비대칭) 채택
- D. 기타

[Answer]: A

#### Q7. 비밀번호/PIN 해싱 라이브러리
bcrypt 필수(BR-AUTH-01). 관리자 8자↑, 테이블 PIN 4~6자리(Q4=A 예외).
- A. ★ **passlib[bcrypt]** (검증/해시 표준 래퍼, cost factor 설정)
- B. `bcrypt` 패키지 직접 사용
- C. 기타

[Answer]: A

#### Q8. 로그인 Rate Limit — 구현 방식 + 구체 임계값
FD BR-AUTH-03에서 임계/윈도우를 NFR 단계로 유보. 로컬 단일 인스턴스 MVP 기준.
- A. ★ **인메모리 슬라이딩 윈도우** + `LoginAttempt` 테이블은 감사용 기록. 임계값 **5회 실패 / 5분 → 429**, 잠금(cooldown) 5분
- B. 인메모리 + 다른 수치(자유 지정: 실패 횟수/윈도우/잠금시간을 적어주세요)
- C. SQLite `LoginAttempt` 쿼리 기반 계산(재기동에도 유지)
- D. 기타

[Answer]: A

#### Q9. SECURITY-05 입력 검증 구체 상한 (FD BR-VAL-02/05에서 유보)
"보안 최소 상한 적용" 확정에 따른 구체 수치입니다. 정상 사용을 방해하지 않는 넉넉한 방어 상한.
- A. ★ **items 배열 ≤ 100, quantity 1..999, 문자열 필드 = 각 도메인 정의 길이(table_no≤20, name≤100, description≤500 등), 요청 본문 크기 ≤ 1MB**
- B. 다른 수치(자유 지정: 각 상한을 적어주세요)
- C. 기타

[Answer]: A

#### Q10. CORS 허용 오리진 (SECURITY-08, 계약 §8)
customer-web / admin-web 개발 오리진만 명시 허용(와일드카드 금지).
- A. ★ **env(`CORS_ORIGINS`)로 주입**, 기본값 = customer-web `http://localhost:5173`, admin-web `http://localhost:5174` (Vite 기본 포트 가정)
- B. 다른 포트/오리진(자유 지정)
- C. 기타

[Answer]: A

### 📈 성능 / 신뢰성 / 테스트 / 운영

#### Q11. 성능 · 확장성 목표
로컬 MVP·단일 매장 기준.
- A. ★ **단일 Uvicorn 워커, 수평 확장 없음. 로컬 응답시간 목표 p95 < 300ms(폴링/조회), 폴링 주기 2s(`shared/PollingHook` 정합)** — 가용성/DR은 N/A(로컬)
- B. 다른 목표(자유 지정)
- C. 기타

[Answer]: A

#### Q12. 테스트 · 로깅 · 커버리지
`shared`(Vitest+fast-check, CI: lint+typecheck+test, 전역 커버리지 게이트 없음)와 정합.
- A. ★ **pytest + Hypothesis(PBT Partial, FD §8 속성) + httpx(TestClient) 통합테스트**. 순수 계산/직렬화 라운드트립 PBT, 인증·주문·세션 핵심 경로 단위/통합 테스트. **구조화 JSON 로깅 + request_id 미들웨어**(stdlib logging + JSON formatter). API 보안 헤더 미들웨어(X-Content-Type-Options 등). CI: lint(ruff)+typecheck(mypy)+test, 전역 커버리지 정량 게이트 미설정
- B. 다른 구성(자유 지정: 테스트/로깅/린트/CI 중 변경점)
- C. 기타

[Answer]: A

---

## 4. 다음 단계

답변 작성 후 알려주시면(또는 "전부 추천안"), 모호성을 점검한 뒤 다음 산출물을 생성하고 2-옵션 완료 메시지로 승인을 요청합니다.
- `construction/backend-api/nfr-requirements/nfr-requirements.md` — 성능/보안/신뢰성/유지보수/테스트 NFR 확정(FD 유보 수치 반영)
- `construction/backend-api/nfr-requirements/tech-stack-decisions.md` — 프레임워크·DB 접근·인증·rate limit·테스트·로깅 스택 + 의존성(버전 고정, SECURITY-10)

> **주의**: 본 단계는 계약 §3(공유 모델)·§4(클레임)를 변경하지 않습니다. 툴체인·구현 NFR·유보 수치만 확정합니다.
