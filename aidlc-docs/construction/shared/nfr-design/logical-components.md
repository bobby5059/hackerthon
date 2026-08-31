# Logical Components — Unit `shared`

> NFR을 반영한 **논리 컴포넌트/모듈 경계** 청사진. 구현(Code Generation) 직전 설계. 사용자 답변 Q1~Q8=A.
> 물리 배치는 `../nfr-requirements/tech-stack-decisions.md` §3 참조.

---

## 1. 모듈 맵 & 의존 방향

```
                 ┌──────────────────────────────┐
                 │        openapi.json           │ (backend 계약 스냅샷, 커밋)
                 └───────────────┬──────────────┘
                    gen:types    │  (openapi-typescript, build-time)
                                 ▼
   src/types/generated/schema.ts  ← 자동생성(편집금지)
                                 ▲ re-export
   ┌───────────── src/types (보강 레이어) ─────────────┐
   │  Menu/Order/…, ApiError*코드, ORDER_STATUS_LABELS │  ← React 무의존
   └───────┬───────────────┬───────────────┬──────────┘
           │               │               │
   src/pricing        src/api          src/hooks ──▶ (React)
   (순수 함수)      (createApiClient,   (usePolling)
                     normalizeError)         │ uses api
                                             │
                                        src/ui (React) ──▶ types
```

**의존 규칙**
- `types` ← 모든 계층이 의존(최하위, React 무의존).
- `pricing`은 `types`에만 의존(순수). `api`는 `types`+`normalizeError`. `hooks`는 `api`+`types`. `ui`는 `types`만(로직 무의존, controlled).
- **역방향 금지**: `types`가 다른 계층을 import 하지 않음. 순환 의존 0.
- React 경계: `hooks`/`ui`만 React 의존(peerDep). `types`/`pricing`/`api`는 순수 → Node/테스트/비-React 환경서도 사용 가능.

---

## 2. 컴포넌트 명세

### 2.1 `types` (보강 레이어)
- **책임**: 생성 타입 별칭 재노출 + 프론트 전용 타입(`ApiErrorCode`, envelope) + 런타임 상수(`ORDER_STATUS_LABELS`).
- **입력**: `generated/schema.ts`. **출력**: `@table-order/shared/types`.
- NFR: MP-01(드리프트 게이트), 필드명 snake_case 불변.

### 2.2 `pricing` (PricingUtil — PBT 표적)
- **API**: `lineTotal(unitPrice:number, quantity:number):number`, `cartTotal(items:{unit_price?:number;price?:number;quantity:number}[]):number`.
- **성질**: 정수 KRW, 음수/비정수 quantity 방어(≥1 가정, 위반 시 명세대로 처리), O(n) 단일 reduce.
- **PBT(P1~P6)**: 비음수성, 0-quantity→0, 분배법칙(`lineTotal` 합 = `cartTotal`), 순서 무관, 스칼라 배수, 정수성. (`pricing.pbt.test.ts`)
- NFR: PP-03, NFR-SH-T-01(100% 커버리지 목표).

### 2.3 `api` (createApiClient + normalizeError + ApiError)
- **팩토리(Q4)**: `createApiClient(config: ApiClientConfig): ApiClient`.
  ```ts
  interface ApiClientConfig {
    baseUrl: string;
    getToken?: () => string | null;   // 매 요청 조회(SP-02)
    timeoutMs?: number;               // 기본 10000 (RP-01)
    onError?: (e: ApiError) => void;  // 선택 관측(SP-01)
    onUnauthorized?: () => void;      // 401/TOKEN_EXPIRED (RP-04)
  }
  interface ApiClient {
    request<T>(method, path, opts?: { body?; query?; signal? }): Promise<T>;
    // + 계약 §의 편의 메서드(선택): getMenu, createOrder, listOrders, ...
  }
  ```
- **요청 파이프라인**: `getToken → Authorization 헤더 주입 → AbortController(timeoutMs, 호출 signal 병합) → fetch → 상태 검사 → normalizeError | JSON 파싱 → T`.
- **`normalizeError(input): ApiError`(Q7)**: 단일 진입점. HTTP 4xx/5xx envelope(`{error:{code,message,request_id}}`) / 네트워크 실패(TypeError) / 타임아웃(Abort) / JSON 파싱 실패 → `ApiError`.
- **`ApiError`**: `class ApiError extends Error { code: ApiErrorCode; httpStatus: number; requestId?: string }`. 민감정보 미포함(SP-01).
- NFR: RP-01/02/04, MP-02, SP-01/02.

### 2.4 `hooks` (usePolling)
- **시그니처**: `usePolling<T>(fetchFn:(signal)=>Promise<T>, opts?:{intervalMs?=2000; enabled?=true; onError?}): { data:T|null; error:ApiError|null; loading:boolean; refetch:()=>void; lastServerTime:string|null }`.
- **내부(Q5)**: `fetchFn`을 `useRef`에 보관(아이덴티티 변화가 인터벌 재시작 안 함), `refetch`는 `useCallback`, 상태는 `useReducer` 단일 객체.
- **동작**: mount 즉시 1회 → `intervalMs` 주기. `document.visibilitychange`로 비활성 정지·재활성 즉시 재개(PP-04/RP-03). 실패 시 데이터 보존·조용한 재시도. 언마운트 시 clearInterval + abort.
- NFR: PP-02/04, RP-03, NFR-SH-P-01.

### 2.5 `ui` (UiKit — Button/Card/Modal/Spinner/ErrorBanner)
- **무상태 controlled(Q8)**: 상태를 부모가 소유. 각 컴포넌트 CSS Module.
- Modal: `role=dialog`, focus-trap, ESC/오버레이 닫기, 스크롤 락. ErrorBanner: `role=alert`. 모든 인터랙티브 요소 `data-testid`.
- 렌더 안전(SP-03): `dangerouslySetInnerHTML` 미사용, 이미지 URL 스킴 검증.
- NFR: MP-03, NFR-SH-U-*, SECURITY-04.

---

## 3. OpenAPI Codegen 파이프라인 (Q6)

```
[개발/빌드]  openapi.json ──gen:types──▶ src/types/generated/schema.ts
[CI 게이트]  gen:types 재실행 → git diff --exit-code src/types/generated
             └─ diff 발생 시 실패(스냅샷↔생성물 불일치 = 미커밋 재생성)
[스냅샷 갱신] backend 계약 변경 → §9 절차 PR로 openapi.json 교체 + 재생성 커밋
```
- shared는 백엔드 미가동 상태서도 독립 개발/CI 가능(커밋 스냅샷).
- NFR: MP-01, NFR-SH-M-01.

---

## 4. 테스트 하니스 (NFR-SH-T)

| 계층 | 유형 | 도구 |
|---|---|---|
| pricing | **PBT**(P1~P6) + 예제 | Vitest + fast-check |
| api | 단위(normalizeError 매핑, 타임아웃, 토큰 주입) | Vitest + fetch mock |
| hooks | 훅 테스트(주기/가시성/정리/에러보존) | Vitest + Testing Library + fake timers |
| ui | 렌더/접근성(focus-trap, role, data-testid) | Vitest + Testing Library |
| types | typecheck(`tsc --noEmit`) + 드리프트 게이트 | tsc + CI diff |

CI 게이트: `lint` + `typecheck` + `test` + codegen 드리프트(MP-01). 전역 커버리지 게이트 없음(pricing만 100% 목표).

---

## 5. NFR ↔ 컴포넌트 추적

| NFR/패턴 | 컴포넌트 |
|---|---|
| RP-01/02/04, MP-02(normalizeError) | `api` |
| RP-03, PP-02/04 | `hooks` |
| PP-03, PBT | `pricing` |
| SP-03, MP-03 | `ui` |
| MP-01(드리프트) | `types` + CI |
| SP-01/02 | `api`(config 콜백) |

---

## 6. 다음 단계
본 청사진을 기준으로 **Code Generation(shared)** 에서 각 모듈의 실제 소스·설정(package.json/tsup/vitest/eslint)·테스트를 생성한다. (Infrastructure Design은 라이브러리 특성상 SKIP.)
