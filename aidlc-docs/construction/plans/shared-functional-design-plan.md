# Functional Design Plan — Unit `shared`

> AI-DLC CONSTRUCTION / Unit 2 (`shared`) / Functional Design.
> `shared`는 두 프론트엔드(customer-web, admin-web)가 소비하는 **TypeScript 라이브러리**다.
> 계약 SSOT: `aidlc-docs/construction/integration-contract.md` (v1.0).
> 적용 확장: **Security Baseline(Yes)**, **PBT(Partial — PricingUtil 순수함수 NFR-T-01)**, Resiliency(No).

---

## 1. 유닛 컨텍스트 (Step 1 — 완료)

**전달 컴포넌트 (5개)**

| 컴포넌트 | 책임 | 계약 근거 | 관련 스토리 |
|---|---|---|---|
| **Types** | 도메인 TS 타입 (백엔드 Pydantic 미러) + 표준 에러 타입 | §3, §1.3 | 모든 서버통신 |
| **ApiClient** | fetch 래퍼, `Authorization: Bearer` 첨부, 에러 정규화 | §1.3, §7 | 모든 서버통신 |
| **PricingUtil** | `lineTotal`, `cartTotal` — 순수 함수 (PBT 대상) | §3.3, NFR-T-01 | C3-S1, C4-S1 |
| **PollingHook** | `usePolling(fetchFn, intervalMs=2000)` — ~2초 폴링 | §5.1 | C5-S2, A2-S2 |
| **UiKit** | 터치 버튼(≥44×44px)·카드·모달·로딩/에러 | NFR-U-02 | C2-S3, 전 UI |

**경계**: shared → backend-api는 **타입 미러링**(런타임 코드 의존 아님). shared는 앱에 역의존하지 않음.

---

## 2. Functional Design 실행 체크리스트

- [ ] Step 1: 유닛 컨텍스트 분석 (unit-of-work, story-map, integration-contract) — **완료**
- [ ] Step 2: 본 계획서 작성 (체크리스트 + 질문) — **완료(본 파일)**
- [ ] Step 3: 명확화 질문 임베드 (아래 §3) — **완료, 답변 대기**
- [ ] Step 4: 계획서 저장 — **완료**
- [x] Step 5: 답변 수집 및 모호성 분석 (10개 답변 검증 완료 — 블로킹 모호성 없음, Q1=B 함의 반영)
- [x] Step 6: 산출물 생성
  - [x] `construction/shared/functional-design/domain-entities.md` (TS 타입 미러 정의)
  - [x] `construction/shared/functional-design/business-logic-model.md` (PricingUtil·ApiClient·PollingHook 로직/알고리즘)
  - [x] `construction/shared/functional-design/business-rules.md` (금액 규칙·에러 정규화 규칙·폴링 규칙·PBT 속성)
  - [x] `construction/shared/functional-design/frontend-components.md` (UiKit 컴포넌트 계층·props·상태, Hook 시그니처·상태)
- [x] Step 7: 완료 메시지 제시 (2-옵션)
- [ ] Step 8: 명시적 승인 대기
- [ ] Step 9: 승인 기록(audit.md) + aidlc-state.md 갱신

---

## 3. 명확화 질문 (답변을 `[Answer]:` 태그에 작성해 주세요)

> 형식: 각 질문에서 A~E 중 선택하거나 자유 기술. 애매하면 추천안(★)을 선택하세요.
> Functional Design은 기술 중립을 지향하지만, `shared`는 라이브러리 유닛이라 타입·시그니처·컴포넌트 구조 결정이 곧 기능 설계입니다. NFR/빌드 세부는 다음 NFR 단계에서 다룹니다.

### Q1. Types 생성 방식 (도메인 타입 미러링)
계약 §3의 모델을 TS 타입으로 어떻게 확보할까요?
- A. ★ **수동 작성** — 계약 §3 기준으로 `interface`/`type`을 손으로 작성 (Q5=A 타입 미러링 결정과 일치, 의존성 0)
- B. `openapi-typescript`로 backend `/openapi.json`에서 **자동 생성**
- C. 하이브리드 — 자동 생성 + 수동 보정
- D. 기타

[Answer]:B

### Q2. ApiClient HTTP 기반 기술
- A. ★ **네이티브 `fetch`** (브라우저 내장, 의존성 0)
- B. `axios`
- C. 기타

[Answer]: A

### Q3. ApiClient 토큰 주입 방식
JWT를 요청에 어떻게 첨부할까요? (customer=테이블 JWT, admin=관리자 JWT, localStorage 저장)
- A. ★ **토큰 프로바이더 주입** — 생성 시 `getToken: () => string | null` 콜백을 받아 매 요청 자동 첨부
- B. 호출마다 `token` 인자 명시 전달 (`request(method, path, body?, token?)`)
- C. 둘 다 지원 (프로바이더 기본 + 호출별 오버라이드)
- D. 기타

[Answer]: A

### Q4. 에러 정규화 모델 (계약 §1.3)
서버 오류/네트워크 오류를 어떤 형태로 소비자에게 던질까요?
- A. ★ **정규화된 `ApiError` 클래스** — `{ code, message, requestId, httpStatus }` 필드 + `instanceof` 판별. 네트워크 실패도 `code:"NETWORK_ERROR"`로 래핑
- B. 계약 JSON 원형(`{error:{...}}`)을 그대로 throw
- C. 기타

[Answer]: A

### Q5. PollingHook 동작 정책 (계약 §5.1)
~2초 폴링 훅의 기본 동작은?
- A. ★ **탭 비활성 시 일시정지 + 재활성 시 즉시 1회 fetch + 에러는 조용히 다음 주기 재시도**(계약 §5.1 "조용히 재시도"와 일치)
- B. 항상 고정 주기 폴링(가시성 무시)
- C. 에러 시 지수 백오프 적용
- D. 기타

[Answer]: A

### Q6. PollingHook 신규 감지(server_time) 책임 위치
계약 §5.1은 `server_time` 기반 신규 판단을 언급합니다. 이 로직을 어디에 둘까요?
- A. ★ **PollingHook가 직전 `server_time`을 노출**(`lastServerTime`)하고, 신규 강조 판단은 소비 컴포넌트(admin-web)가 수행 — shared는 메커니즘만 제공
- B. PollingHook가 신규 항목까지 계산해 반환
- C. 기타

[Answer]: A

### Q7. PricingUtil 금액 규칙 (계약 §3.3, PBT NFR-T-01)
금액은 정수 KRW입니다. 순수 함수의 입력 검증/경계 규칙은?
- A. ★ **비정수·음수 수량/단가는 유효하지 않은 입력으로 간주(예외 throw 또는 명시적 거부)**, 결과는 항상 비음의 정수. PBT 속성: `cartTotal = Σ lineTotal`, `lineTotal(p,q)=p*q`, 빈 배열=0, 순서 무관(교환)
- B. 방어 없이 산술만 수행(호출측 검증 신뢰)
- C. 기타

[Answer]: A

### Q8. UiKit 스타일링 방식 & MVP 컴포넌트 범위
공용 UI의 스타일링 접근과 초기 컴포넌트 세트는?
- A. ★ **CSS Modules + 디자인 토큰(색/간격/최소 터치 44px)**, MVP 세트: `Button`, `Card`, `Modal`, `Spinner/Loading`, `ErrorBanner`
- B. Tailwind CSS 유틸리티
- C. 인라인 스타일/CSS-in-JS(styled-components 등)
- D. 기타(범위 조정 포함)

[Answer]: A

### Q9. React 결합도 (PollingHook·UiKit)
`shared`가 React에 의존하는 범위는? (customer/admin 모두 React+TS)
- A. ★ **React를 peerDependency로** — Hook·UiKit은 React 사용, PricingUtil·Types·ApiClient는 **프레임워크 무관 순수 TS**(계층 분리)
- B. 전체를 React 결합
- C. 기타

[Answer]: A

### Q10. 패키지 구성 (모노레포 npm 워크스페이스)
`frontend/shared/`의 export 구성은?
- A. ★ **단일 패키지, 서브경로 export** (`@table-order/shared/types`, `/api`, `/pricing`, `/hooks`, `/ui`) — 트리셰이킹 용이
- B. 단일 배럴 export(`index.ts` 하나)
- C. 기타

[Answer]: A

---

## 4. 다음 단계
답변(`[Answer]:`) 작성 후 알려주시면, 모호성을 점검하고(필요 시 후속 질문) §2 Step 6 산출물 4종을 생성한 뒤 2-옵션 완료 메시지로 승인을 요청합니다.
