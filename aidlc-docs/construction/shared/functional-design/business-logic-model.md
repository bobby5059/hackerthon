# Functional Design — Business Logic Model — Unit `shared`

> `shared`의 로직은 **횡단 유틸리티**다: 순수 금액 계산(PricingUtil), HTTP 통신·에러 정규화(ApiClient), 폴링 라이프사이클(PollingHook).
> 도메인 비즈니스 규칙(주문 생성·세션 종료 등)은 backend-api 소유이며 shared에는 없다.
> 계층 분리(Q9=A): **순수 TS 계층**(Types/PricingUtil/ApiClient) + **React 계층**(PollingHook/UiKit, React=peerDependency).

---

## 1. PricingUtil (순수 함수 — PBT 대상, Q7=A / NFR-T-01)

### 1.1 시그니처
```ts
function lineTotal(unitPrice: number, quantity: number): number;
function cartTotal(items: Array<{ unit_price: number; quantity: number }>): number;
```

### 1.2 알고리즘
- `lineTotal(p, q)  = p * q`
- `cartTotal(items) = items.reduce((sum, it) => sum + lineTotal(it.unit_price, it.quantity), 0)`
- 빈 배열 → `0`.

### 1.3 입력 계약 (경계 검증, Q7=A)
- `unit_price`, `quantity`는 **정수** & **≥ 0**(quantity는 실무상 ≥1이나 0 허용 시 결과 0). 위반 시 `RangeError` throw(방어적, fail-fast).
- 반환은 항상 **비음의 정수**.
- 부동소수·`NaN`·`Infinity` 입력은 유효하지 않은 입력으로 거부.

### 1.4 불변식 (PBT 속성 — 다음 NFR/테스트 단계에서 property test로 구현)
| # | 속성 | 진술 |
|---|---|---|
| P1 | 정의 | `lineTotal(p,q) === p*q` (유효 입력) |
| P2 | 합산 일치 | `cartTotal(items) === Σ lineTotal(itemᵢ)` |
| P3 | 항등원 | `cartTotal([]) === 0` |
| P4 | 순서 무관(교환) | `cartTotal(items) === cartTotal(shuffle(items))` |
| P5 | 비음/정수 | 유효 입력에 대해 결과 ≥ 0 이고 `Number.isInteger` |
| P6 | 단조 | 항목 추가 시 합계는 감소하지 않음 |

> **역할 경계**: PricingUtil은 **표시용 계산**이다. 서버 `total_amount`가 최종 정답(계약 §3.3). 두 값 불일치는 서버 응답(422 `TOTAL_MISMATCH`)이 우선.

---

## 2. ApiClient (fetch 래퍼 — Q2=A, Q3=A, Q4=A)

### 2.1 생성/구성
```ts
interface ApiClientConfig {
  baseUrl: string;                       // 예: "http://localhost:8000/api" (계약 §1.1)
  getToken?: () => string | null;        // Q3=A: 토큰 프로바이더 콜백
  onUnauthorized?: () => void;           // 401/TOKEN_EXPIRED 시 훅(로그아웃/재설정 안내)
}
function createApiClient(config: ApiClientConfig): ApiClient;
```

### 2.2 핵심 메서드
```ts
interface ApiClient {
  request<T>(method: HttpMethod, path: string, body?: unknown, opts?: RequestOpts): Promise<T>;
  get<T>(path, opts?): Promise<T>;
  post<T>(path, body?, opts?): Promise<T>;
  patch<T>(path, body?, opts?): Promise<T>;
  delete<T>(path, opts?): Promise<T>;
}
interface RequestOpts { query?: Record<string,string|number>; signal?: AbortSignal; }
```

### 2.3 요청 처리 흐름
```
1. URL 조립: baseUrl + path + (?query)         # 페이지네이션 등 §1.4
2. 헤더: Content-Type: application/json (본문 존재 시)
         Authorization: Bearer <getToken()>    # 토큰 있으면 자동 첨부 (Q3=A)
3. fetch(url, { method, headers, body: JSON.stringify(body), signal })
4. 응답 파싱 → 성공/에러 분기 (§2.4)
```

### 2.4 응답·에러 정규화 (Q4=A / 계약 §1.3 / SECURITY-15)
```
- 2xx  → JSON 파싱하여 T 반환 (204/빈 본문 → undefined)
- 4xx/5xx → 본문의 {error:{code,message,request_id}} 파싱 → ApiError throw
- 파싱 불가/네트워크 실패/timeout → ApiError(code:"NETWORK_ERROR") throw
- 401 또는 code=="TOKEN_EXPIRED" → onUnauthorized?.() 호출 후 throw (fail closed)
```
```ts
class ApiError extends Error {
  readonly code: ApiErrorCode | string;
  readonly httpStatus: number;      // 네트워크 오류는 0
  readonly requestId?: string;
  constructor(...) { super(message); this.name = "ApiError"; }
}
// 소비자: try { ... } catch (e) { if (e instanceof ApiError) { e.code, e.message ... } }
```

### 2.5 보안 규칙 (SECURITY 계약 §8)
- **토큰/비밀번호를 로깅하지 않는다**(SECURITY-03). 에러 로깅 시 `Authorization` 헤더·요청 바디의 password 필드 마스킹.
- 서버 에러 `message`는 **일반화된 사용자 메시지**를 그대로 노출(내부 스택 없음 — 서버가 보장, 계약 §1.3).
- `getToken()`은 소비 앱이 localStorage에서 제공(계약 §4.2). shared는 저장소를 직접 만지지 않는다(관심사 분리).

---

## 3. PollingHook (React — Q5=A, Q6=A / 계약 §5.1)

### 3.1 시그니처
```ts
interface UsePollingOptions {
  intervalMs?: number;     // 기본 2000 (계약 §5.1)
  enabled?: boolean;       // 기본 true (로그인 전/언마운트 대비)
  immediate?: boolean;     // 기본 true (마운트 즉시 1회)
}
interface UsePollingResult<T> {
  data: T | null;
  error: ApiError | null;  // 조용한 재시도이므로 마지막 오류만 노출
  isLoading: boolean;      // 최초 로드 여부
  lastServerTime: string | null;  // Q6=A: 응답의 server_time 노출
  refetch: () => void;     // 수동 트리거
}
function usePolling<T extends { server_time?: string }>(
  fetchFn: (signal: AbortSignal) => Promise<T>,
  options?: UsePollingOptions
): UsePollingResult<T>;
```

### 3.2 라이프사이클 (Q5=A)
```
mount → (immediate ? fetch now : wait) → setInterval(intervalMs)
tick  → fetchFn(signal); 성공: data 갱신 + lastServerTime = data.server_time
                          실패: error 저장, 데이터 유지, 다음 주기 재시도(조용히)
visibilitychange:
   hidden  → clearInterval (일시정지)                    # 불필요 폴링/배터리 절감
   visible → 즉시 1회 fetch + interval 재개
enabled=false → 폴링 중단
unmount → clearInterval + AbortController.abort()        # 누수 방지
```

### 3.3 신규 감지 책임 (Q6=A)
- PollingHook는 **`lastServerTime`만 노출**. "신규 주문 강조"(A2-S2)나 상태 변화 판단은 **소비 컴포넌트**가 `created_at > 직전 server_time` 비교로 수행. shared는 메커니즘만 제공(정책 미포함).

### 3.4 신뢰성 (계약 §5.2)
- 최종 일관성: 각 폴링 결과가 현재 진실. 낙관적 업데이트 후 폴링으로 정정 가능(소비 앱 책임).
- 폴링 실패는 UI를 깨지 않고 조용히 재시도(계약 §5.1). 지속 실패 시 소비 앱이 `error`로 배너 표시 가능(UiKit `ErrorBanner`).

---

## 4. 데이터 흐름 요약
```
customer-web / admin-web
   │ import { createApiClient } from "@table-order/shared/api"
   │ import { usePolling }      from "@table-order/shared/hooks"
   │ import { cartTotal }       from "@table-order/shared/pricing"
   ▼
ApiClient.request<OrderListResponse>("GET","/orders",…)  ──HTTP──▶ backend-api
   ▲ ApiError(정규화) on failure
usePolling(() => api.get("/tables/dashboard"))  ──2s tick──▶ DashboardResponse
```

---

## 5. 스토리 추적
- PricingUtil → C3-S1(장바구니 총액), C4-S1(주문 확정 표시)
- ApiClient/Types → 전 서버통신 스토리(C1~C5, A1~A3)
- PollingHook → C5-S2(주문 상태 준실시간), A2-S2(대시보드 준실시간)
