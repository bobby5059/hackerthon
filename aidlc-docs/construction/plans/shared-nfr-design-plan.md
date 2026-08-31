# NFR Design Plan — Unit `shared`

> AI-DLC CONSTRUCTION / Unit 2 (`shared`) / NFR Design.
> 전제: NFR Requirements 승인 완료(PR #2). 입력 = `construction/shared/nfr-requirements/*`, `functional-design/*`, `integration-contract.md` v1.0.
> 최신 main 반영: backend-api가 shared/계약에 맞춰 정합화 완료(Menu는 `is_available` 없음, 409=SESSION_CLOSED, TableCard.has_new 항상 false). 계약 §9 변경 없음 → shared 재작업 없음.
> 목적: NFR을 **설계 패턴 + 논리 컴포넌트**로 구체화(구현 전 청사진). 확장: Security Baseline(Yes), PBT(Partial).

---

## 1. NFR Design 실행 체크리스트

- [ ] Step 1: NFR Requirements 분석 — **완료**
- [ ] Step 2: 본 계획서 작성 — **완료(본 파일)**
- [ ] Step 3: 명확화 질문 임베드 (아래 §3) — **완료, 답변 대기**
- [ ] Step 4: 계획서 저장 — **완료**
- [x] Step 5: 답변 수집 및 모호성 분석 (전부 추천안 A — 모호성 없음)
- [x] Step 6: 산출물 생성
  - [x] `construction/shared/nfr-design/nfr-design-patterns.md`
  - [x] `construction/shared/nfr-design/logical-components.md`
- [x] Step 7: 완료 메시지 제시 (2-옵션)
- [x] Step 8: 명시적 승인 대기 — **승인됨(2026-08-31, "승인 후 push")**
- [x] Step 9: 승인 기록(audit.md) + aidlc-state.md 갱신

---

## 2. NFR 카테고리 적용성 (라이브러리 관점)

| 카테고리 | 적용성 | 메모 |
|---|---|---|
| Resilience Patterns | **적용** | ApiClient 타임아웃/abort, 에러 정규화, 폴링 조용한 재시도 |
| Performance Patterns | **적용** | 순수/React 계층 분리, 서브경로 트리셰이킹, 폴링 가시성 정지, 훅 안정 참조 |
| Security Patterns | **적용** | 토큰 마스킹, 자격증명 미저장, XSS-safe 렌더 |
| Logical Components | **적용** | 모듈 경계(types/pricing/api/hooks/ui), OpenAPI codegen 파이프라인, 테스트 하니스 |
| Scalability Patterns | **대부분 N/A** | 라이브러리는 스케일 대상 아님. 소비 앱이 담당 |

---

## 3. 명확화 질문 (`[Answer]:` 태그에 작성 — 애매하면 추천안 ★)

> **사용자 선택: 전부 추천안(★) = A** (2026-08-31). Q1~Q8 = A.

### Q1. ApiClient 요청 타임아웃 (Resilience)
개별 HTTP 요청의 타임아웃 정책은?
- A. ★ **기본 10초 타임아웃**(`AbortController` 기반) + 호출측 `signal` 병합. 초과 시 `ApiError(NETWORK_ERROR)`
- B. 타임아웃 없음(브라우저 기본에 위임)
- C. 기타(값 지정)

[Answer]:

### Q2. 비폴링 요청의 자동 재시도 (Resilience)
주문 생성 등 mutation/일반 요청에 shared가 자동 재시도를 넣을까요?
- A. ★ **자동 재시도 없음** — mutation은 멱등성 미보장(중복 주문 위험). 재시도는 소비 앱/폴링만. GET도 shared 자동재시도 없음(폴링 훅이 주기 재시도 담당)
- B. GET만 1~2회 재시도
- C. 기타

[Answer]:

### Q3. shared 내부 로깅 정책 (Security/Observability)
라이브러리가 콘솔/로그를 남길까요?
- A. ★ **기본 무로깅** — 라이브러리는 console에 쓰지 않음. 선택적 `onError(err)` 콜백만 노출(소비 앱이 로깅). 로깅 시 토큰/비밀번호 마스킹은 소비 앱 책임이나, shared가 넘기는 err에는 민감정보 미포함(BR-S-01)
- B. 개발 모드 콘솔 경고 허용
- C. 기타

[Answer]:

### Q4. ApiClient 구성 패턴 (Logical Components)
- A. ★ **팩토리 함수 `createApiClient(config)`** + 내부 요청 파이프라인(헤더 주입 → fetch → 응답/에러 정규화). 클로저로 config 캡슐화(클래스 대비 단순, 트리셰이킹 우수)
- B. `class ApiClient`
- C. 기타

[Answer]:

### Q5. 훅 성능/안정성 패턴 (Performance)
usePolling의 리렌더/참조 안정성 전략은?
- A. ★ **`useRef`로 최신 fetchFn 보관 + `useCallback`으로 `refetch` 안정화 + 상태는 단일 reducer/객체**로 불필요 리렌더 최소화. `fetchFn` 아이덴티티 변화에 폴링이 재시작되지 않도록 ref 패턴
- B. 매 렌더 새 인터벌(단순, 비효율 감수)
- C. 기타

[Answer]:

### Q6. OpenAPI codegen 드리프트 방지 (Logical Components / Maintainability)
커밋된 `openapi.json` 스냅샷과 생성 타입의 정합을 어떻게 보장할까요?
- A. ★ **CI 드리프트 체크** — `gen:types` 재실행 후 `git diff --exit-code`로 생성물 변경 없음 검증(스냅샷↔생성타입 동기 강제). 스냅샷 갱신은 계약 §9 절차로 PR
- B. 수동 관리(CI 체크 없음)
- C. 기타

[Answer]:

### Q7. 에러 매핑 컴포넌트 (Resilience/Security)
HTTP 상태·계약 envelope → `ApiError` 변환 로직의 위치는?
- A. ★ **단일 `normalizeError` 내부 모듈** — 상태코드/`{error:{code,message,request_id}}`/네트워크실패/파싱실패를 한 곳에서 `ApiError`로 매핑. ApiClient가 이 모듈만 사용(테스트 용이, 일관성)
- B. ApiClient.request 내 인라인 처리
- C. 기타

[Answer]:

### Q8. UiKit 상태/접근성 패턴 (Performance/Usability)
- A. ★ **무상태 controlled 컴포넌트** 원칙(부모가 상태 소유), Modal은 focus-trap·ESC·오버레이 닫기 접근성 포함, 모든 인터랙티브 요소 `data-testid` 부여
- B. 컴포넌트 내부 상태 허용
- C. 기타

[Answer]:

---

## 4. 다음 단계
답변 작성 후 알려주시면, 모호성 점검 후 `nfr-design-patterns.md`·`logical-components.md`를 생성하고 2-옵션 완료 메시지로 승인을 요청합니다. ("전부 추천안(★)"도 가능)
