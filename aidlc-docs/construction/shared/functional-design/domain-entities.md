# Functional Design — Domain Entities (TS Types) — Unit `shared`

> `shared`는 도메인 데이터를 **소유하지 않는다**. 백엔드(Pydantic)가 SSOT이며, 본 유닛은 대응 **TypeScript 타입을 미러링**한다(계약 §3, 유닛 결정 Q5=A).
> **타입 확보 방식 = Q1=B (openapi-typescript 자동 생성)**: backend `/openapi.json` 스냅샷에서 기계 타입을 생성하고, 그 위에 프론트 전용 **보강 레이어**를 손으로 얹는다.
> 본 문서는 소비자(customer-web/admin-web)가 의존할 **논리 타입 계약**을 규정한다. 필드명은 계약과 동일하게 **snake_case**를 유지한다.

---

## 1. 타입 소싱 전략 (Q1=B)

```
backend /openapi.json (SSOT)
        │  openapi-typescript (build-time codegen)
        ▼
  generated/schema.ts     ← 자동 생성(수정 금지, 커밋된 스냅샷 기반)
        │  re-export + 별칭
        ▼
  types/index.ts (보강 레이어, 손으로 작성)
        ├─ 생성 타입을 읽기 쉬운 별칭으로 노출 (Menu, Order, …)
        ├─ OpenAPI에 없는 프론트 전용 타입 (ApiError, 표시 라벨 등)
        └─ 런타임 상수 (ORDER_STATUS_LABELS 등)
```

**규칙**
- `generated/schema.ts`는 **자동 생성 산출물** — 직접 편집 금지, `openapi.json` 스냅샷 갱신 시 재생성.
- 스냅샷 출처: backend-api 팀이 제공하는 커밋된 `openapi.json`(계약 §9 변경 절차와 동기). 백엔드 미가동 상태에서도 shared 개발 가능하도록 스냅샷을 리포에 보관.
- 소비자는 **항상 보강 레이어(`@table-order/shared/types`)만 import**한다. `generated/`를 직접 참조하지 않는다(별칭 안정성).

---

## 2. 열거형 (Enums)

```ts
// 계약 §3.1
type OrderStatus = "PENDING" | "PREPARING" | "COMPLETED";

// 프론트 전용 표시 라벨(OpenAPI에 없음 → 보강 레이어에서 정의)
const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  PENDING:    "대기중",
  PREPARING:  "준비중",
  COMPLETED:  "완료",
};
```

---

## 3. 도메인 모델 (계약 §3.2 미러)

> 아래는 **논리 계약**이다. 실제 필드 타입/옵셔널 여부는 생성된 `schema.ts`가 권위를 가지며, 상충 시 계약 §9 절차로 동기화한다.

```ts
interface Category {
  category_id: string;
  name: string;
  display_order: number;   // int
}

interface Menu {
  menu_id: string;
  category_id: string;
  name: string;
  price: number;           // int, KRW
  description: string;
  image_url: string | null;
}

interface OrderItemInput {  // 주문 생성 요청 항목
  menu_id: string;
  quantity: number;        // >= 1
}

interface OrderItem {       // 주문 응답 항목(스냅샷)
  menu_id: string;
  name: string;            // 주문 시점 스냅샷
  unit_price: number;      // 주문 시점 스냅샷, int
  quantity: number;
  line_amount: number;     // unit_price * quantity, int
}

interface Order {
  order_id: string;
  order_number: string;    // "store-001-20260831-001"
  table_id: string;
  session_id: string;
  status: OrderStatus;
  items: OrderItem[];
  total_amount: number;    // Σ line_amount, int (서버 재검증값이 정답)
  created_at: string;      // ISO8601 +09:00
}

interface OrderPreview {
  order_id: string;
  order_number: string;
  created_at: string;
  item_summary: string;    // "김치찌개 외 2건"
  total_amount: number;
}

interface TableCard {
  table_id: string;
  table_no: string;
  total_amount: number;
  recent_orders: OrderPreview[];   // 최신 3건
  has_new: boolean;
}

interface HistoryEntry {
  order_id: string;
  order_number: string;
  table_id: string;
  items: OrderItem[];
  total_amount: number;
  created_at: string;
  completed_at: string;    // 이용 완료 시각
}

interface PageMeta {
  page: number;
  size: number;
  total: number;
}
```

### 3.1 인증/응답 래퍼 타입 (계약 §2)

```ts
interface StoreBrief { store_id: string; name: string; }
interface TableBrief { table_id: string; table_no: string; }
interface SessionBrief { session_id: string; started_at: string; expires_at?: string; }

interface AdminLoginResponse {
  access_token: string; token_type: "bearer"; expires_at: string; store: StoreBrief;
}
interface TableLoginResponse {
  access_token: string; token_type: "bearer"; expires_at: string;
  table: TableBrief; session: SessionBrief;
}

interface MenuListResponse { categories: Category[]; menus: Menu[]; }

interface OrderListResponse {                 // GET /api/orders (폴링)
  items: Order[]; page_meta: PageMeta; server_time: string;
}
interface DashboardResponse {                 // GET /api/tables/dashboard (폴링)
  tables: TableCard[]; server_time: string;
}
interface HistoryListResponse {
  items: HistoryEntry[]; page_meta: PageMeta;
}

interface DeleteOrderResponse {
  deleted_order_id: string; table_id: string; table_total_amount: number;
}
interface CompleteSessionResponse {
  table_id: string; archived_order_count: number; completed_at: string; table_total_amount: number;
}
```

### 3.2 요청 바디 타입

```ts
interface AdminLoginRequest  { store_id: string; username: string; password: string; }
interface TableLoginRequest  { store_id: string; table_no: string; table_password: string; }
interface CreateOrderRequest { items: OrderItemInput[]; }   // store/table/session은 토큰에서 도출
interface UpdateStatusRequest{ status: OrderStatus; }
interface TableSetupRequest  { table_no: string; table_password: string; }
```

---

## 4. 에러 타입 (계약 §1.3 — 보강 레이어, Q4=A)

```ts
// 서버 에러 코드(계약 §1.3 발췌) — 확장 가능
type ApiErrorCode =
  | "VALIDATION_ERROR" | "UNAUTHORIZED" | "TOKEN_EXPIRED" | "FORBIDDEN"
  | "NOT_FOUND" | "ORDER_EMPTY" | "TOTAL_MISMATCH" | "SESSION_CLOSED"
  | "RATE_LIMITED" | "INTERNAL_ERROR"
  | "NETWORK_ERROR";   // shared 전용: 네트워크/파싱 실패 래핑

// 서버 원형(계약 §1.3)
interface ApiErrorEnvelope {
  error: { code: string; message: string; request_id: string; };
}
```
> `ApiError` **클래스**의 상세 형태·동작은 `business-logic-model.md` §ApiClient 참조.

---

## 5. 타입 무결성 규칙

- **필드명 불변**: 계약과 동일 snake_case. 프론트에서 camelCase 변환하지 않는다(미러 일관성).
- **금액 필드**(`price`,`unit_price`,`line_amount`,`total_amount`,`table_total_amount`)는 모두 **정수 KRW**(계약 §3.3). 부동소수 금지.
- **스냅샷 보존**: `OrderItem.name/unit_price`는 주문 시점 값 — shared는 이를 표시용으로만 사용, 재계산으로 덮어쓰지 않는다.
- **ID는 string**(계약 §1.1).
- 생성 타입과 본 논리 계약이 상충하면 **계약 §9 변경 절차**로 backend/openapi/shared 순 동기화.

---

## 6. 스토리 추적
- 전 서버통신 스토리(C1~C5, A1~A3)의 데이터 타입 기반 제공. `OrderStatus`/라벨 → C5-S2·A2-S4 상태 표시.
