# Code Generation Plan — Unit `shared`

> AI-DLC CONSTRUCTION / Unit 2 (`shared`) / Code Generation (per-unit loop 마지막 단계).
> **이 계획서가 Code Generation의 단일 진실원본(SSOT)이다.** Part 2는 이 순서를 정확히 따른다.
> 입력: `construction/shared/{functional-design,nfr-requirements,nfr-design}/*`, `integration-contract.md` v1.0.
> 확장: Security Baseline(enforced), PBT(Partial — PricingUtil).

---

## 0. 유닛 컨텍스트

### 0.1 코드 위치 (Critical Rules)
- **Application code**: 워크스페이스 루트의 **`frontend/shared/`** (npm workspace, `@table-order/shared`).
  - aidlc-state.md의 논리 Workspace Root(`~/aidlc-workshop/table-order`)에 대응하는 실제 리포 루트 = 본 저장소 루트.
- **Documentation(요약)**: `aidlc-docs/construction/shared/code/*.md` (마크다운만).
- **금지**: 애플리케이션 코드를 `aidlc-docs/`에 두지 않는다.

### 0.2 유닛 성격 & 계층 적용성
`shared`는 **프론트엔드 TS 라이브러리**(런타임 의존성 0, ESM). 표준 계층 중:
| 표준 계층 | 적용 | 매핑 |
|---|---|---|
| Business Logic | ✅ | `pricing`(PricingUtil), `api`(normalizeError/ApiError) |
| API Layer | ✅ | `api`(createApiClient), `hooks`(usePolling) |
| Repository Layer | ❌ N/A | 데이터 소유 없음(백엔드 SSOT) |
| Frontend Components | ✅ | `ui`(UiKit) |
| Database Migration | ❌ N/A | DB 없음 |
| Deployment Artifacts | ⚠️ 축소 | 라이브러리 = 빌드 설정(tsup/package exports)로 대체, IaC 없음 |

### 0.3 스토리 추적 (간접 지원)
`shared`는 UI 스토리를 직접 소유하지 않고 소비 유닛을 **지원**한다:
- 서버통신·타입: C1~C5(customer), A1~A3(admin) 전반
- 폴링: C5(주문상태 폴링), A2(주문 대시보드 폴링)
- 가격계산: C3~C4(장바구니/합계)
- 상태 라벨: C5-S2, A2-S4

### 0.4 의존/인터페이스
- **상위 의존**: backend-api OpenAPI(`openapi.json` 커밋 스냅샷) → 타입 생성.
- **하위 소비자**: customer-web, admin-web (서브경로 import).
- **계약 경계**: Integration Contract v1.0. 변경은 §9 절차.

---

## 1. 실행 체크리스트 (Part 1: Planning)

- [x] Step 1: 유닛 컨텍스트 분석 (§0)
- [x] Step 2: 상세 코드 생성 계획 (§3 단계들)
- [x] Step 3: 유닛 생성 컨텍스트 포함 (§0.3, §0.4)
- [x] Step 4: 계획 문서 저장 (본 파일)
- [x] Step 5: 사용자에게 요약 (완료 메시지)
- [x] Step 6: 승인 프롬프트 audit 기록
- [x] Step 7: 명시적 승인 대기 — **승인됨(2026-08-31, "승인. 진행")**
- [x] Step 8: 승인 응답 기록
- [x] Step 9: aidlc-state.md Part 1 완료 표시

## 2. 실행 체크리스트 (Part 2: Generation) — 승인 후

각 단계는 완료 즉시 [x] 표시.

- [x] Step 10: 계획 로드
- [x] Step 11~12: G1~G8 실행 + 체크박스 갱신 (아래 §3)
- [x] Step 13: 전 단계 완료
- [x] Step 14: 완료 메시지 제시
- [x] Step 15: 명시적 승인 대기 — **승인됨(2026-08-31, "commit 및 push")**
- [x] Step 16: 승인 기록 + aidlc-state 완료 표시

**로컬 검증(2026-08-31)**: `typecheck` ✅ · `lint` ✅ · `test` 43/43 ✅ · `build` ✅ · codegen drift 0 ✅.

---

## 3. 생성 단계 (번호순 — Part 2에서 실행)

### Step G1 — 프로젝트 구조 & 툴체인 셋업 (greenfield)
- [x] `frontend/shared/` 생성. 파일:
  - `package.json` (name `@table-order/shared`, `type:module`, `sideEffects:false`, exports 맵[types/pricing/api/hooks/ui], peerDeps react/react-dom ^18, scripts: gen:types/build/test/typecheck/lint)
  - `tsconfig.json` (strict, noUncheckedIndexedAccess, exactOptionalPropertyTypes, moduleResolution bundler)
  - `tsup.config.ts` (ESM, dts, 멀티 엔트리 per 서브경로)
  - `vitest.config.ts` (환경: node for pure/api, jsdom for hooks/ui)
  - `.eslintrc.cjs` + `.prettierrc`
  - `scripts/gen-types.*` (openapi-typescript 래퍼)
  - `README.md` (사용법/서브경로/개발 스크립트)
- [x] devDependencies 나열(버전 고정, SECURITY-10). *네트워크 설치는 Build & Test 단계 책임 — 여기선 파일만 생성.*

### Step G2 — Types 계층 (Business Logic 지원)  → C/A 전반
- [x] `openapi.json` — backend 계약 스냅샷 커밋(현 계약 v1.0 기반 최소 스펙). 없으면 계약 §3/§2에서 파생한 플레이스홀더 스펙 생성 + 주석으로 §9 갱신 절차 명시.
- [x] `src/types/generated/schema.ts` — codegen 산출물(스냅샷 기반). *자동 생성물 표식.*
- [x] `src/types/index.ts` — 보강 레이어: 별칭(Menu/Order/…), `OrderStatus`, `ORDER_STATUS_LABELS`, `ApiErrorCode`, `ApiErrorEnvelope`, 요청/응답 래퍼 타입 (domain-entities.md §2~4 그대로).

### Step G3 — Pricing 계층 (Business Logic)  → C3~C4
- [x] `src/pricing/index.ts` — `lineTotal(unitPrice, quantity)`, `cartTotal(items)`. 정수 KRW, O(n) reduce (PP-03, business-logic-model.md).

### Step G3T — Pricing 단위 테스트 (**PBT**)  → NFR-SH-T-01
- [x] `src/pricing/pricing.pbt.test.ts` — fast-check 성질 P1~P6(비음수/0-quantity/분배/순서무관/스칼라배수/정수성) + 예제 테스트. 목표 커버리지 100%.

### Step G4 — API 계층 (API Layer)  → C/A 전반
- [x] `src/api/errors.ts` — `ApiError` 클래스 + `normalizeError(input): ApiError` (MP-02: 상태/envelope/네트워크/파싱/타임아웃 매핑).
- [x] `src/api/client.ts` — `createApiClient(config)` 팩토리(Q4): getToken 헤더 주입 → 10s AbortController+signal 병합(RP-01) → fetch → normalizeError → `request<T>`; 401/TOKEN_EXPIRED→onUnauthorized(RP-04); onError 콜백(SP-01); 무재시도(RP-02). 편의 메서드는 계약 §2 엔드포인트 기준(선택 최소).
- [x] `src/api/index.ts` — 공개 export.

### Step G4T — API 계층 단위 테스트
- [x] `src/api/api.test.ts` — normalizeError 매핑 케이스, 토큰 주입, 타임아웃(fake timers), onUnauthorized/onError 트리거 (fetch mock).

### Step G5 — Hooks 계층 (API Layer)  → C5, A2
- [x] `src/hooks/usePolling.ts` — 시그니처/내부 ref·useCallback·useReducer(PP-02), 2s 기본, visibility pause/resume(PP-04/RP-03), 조용한 재시도, cleanup(clearInterval+abort), `lastServerTime`.
- [x] `src/hooks/index.ts` — export.

### Step G5T — Hooks 단위 테스트
- [x] `src/hooks/usePolling.test.tsx` — 주기 호출, visibility 정지/재개, 실패 시 데이터 보존, 언마운트 정리 (Testing Library + fake timers, jsdom).

### Step G6 — UI 계층 (Frontend Components)  → 전 화면 공통
- [x] `src/ui/` — Button, Card, Modal(focus-trap/ESC/overlay, role=dialog), Spinner, ErrorBanner(role=alert). 무상태 controlled(MP-03), CSS Module, 모든 인터랙티브 `data-testid`(자동화 규칙), 이미지 URL 스킴 검증(SP-03).
- [x] `src/ui/index.ts` — export.

### Step G6T — UI 단위 테스트
- [x] `src/ui/ui.test.tsx` — 렌더/접근성(Modal focus-trap·ESC, ErrorBanner role, data-testid 존재) (Testing Library, jsdom).

### Step G7 — 문서 요약 (aidlc-docs, 마크다운)
- [x] `aidlc-docs/construction/shared/code/code-summary.md` — 생성 파일 목록/구조, 서브경로 export, 소비자 사용 예, NFR/보안 준수 매핑, 테스트 목록.
- [x] `frontend/shared/README.md`는 G1에서 생성(사용법).

### Step G8 — 배포/빌드 아티팩트 (라이브러리 축소판)
- [x] tsup/package exports가 배포 산출물 정의(별도 IaC 없음 = 라이브러리). CI 스텁 노트: lint+typecheck+test+codegen drift(MP-01)는 Build & Test 단계에서 구성. *본 단계는 설정 파일 존재로 충족, 실제 CI YAML은 Build & Test.*

### N/A 단계
- Repository Layer / Repository Tests — **N/A** (데이터 미소유)
- Database Migration — **N/A** (DB 없음)

---

## 4. 범위 요약
- **총 생성 단계**: G1~G8 (테스트 서브스텝 포함). Repository/DB = N/A.
- **주요 산출물**: 5개 서브경로 모듈(types/pricing/api/hooks/ui) + 툴체인 설정 + 4개 테스트 파일(PBT 1 + 단위 3) + openapi 스냅샷 + 문서 요약.
- **테스트 실행은 Build & Test 단계**에서 수행(본 단계는 코드/테스트 파일 생성까지).
- **보안(enforced)**: SECURITY-03(무로깅)/04(XSS-safe)/08(자격증명 미저장)/10(의존성 고정) 코드에 반영.
- **PBT(Partial)**: PricingUtil P1~P6.

## 5. 다음 단계
본 계획 승인 시 Part 2(생성)를 G1부터 순서대로 실행하고 각 단계 [x] 표시 후 완료 메시지를 제시한다.
