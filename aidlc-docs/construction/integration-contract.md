# Integration Contract — 테이블오더 서비스

> **목적**: 유닛 간 통합을 위한 **단일 통합 규약**. 모든 팀원(backend-api, shared, customer-web, admin-web)은 본 문서를 기준으로 개발한다.
> **계약 SSOT**: backend-api의 FastAPI OpenAPI(`/docs`, `/openapi.json`)가 런타임 진실 원천이며, 본 문서는 이를 사람이 읽는 형태로 규정한다. 두 문서가 상충하면 **본 문서의 변경 절차(§9)를 거쳐** 동기화한다.
> **버전**: v1.0 (INCEPTION 종료 시점 확정). 변경 이력은 §9.

---

## 1. 공통 규약 (Common Conventions)

### 1.1 기본
| 항목 | 규약 |
|---|---|
| Base URL | `/api` (예: `http://localhost:8000/api`) |
| 프로토콜 | REST over HTTP(S), JSON |
| 문자 인코딩 | UTF-8 |
| 콘텐츠 타입 | `application/json` (요청/응답 본문) |
| 타임존 | 모든 타임스탬프는 **ISO 8601 + Asia/Seoul 오프셋** (`2026-08-31T14:03:00+09:00`) — NFR-D-03 |
| 금액 | **정수 KRW (원)** — 소수점 없음. 필드명 `*_amount`, `price` |
| ID 표기 | 문자열(string) — 내부 자동증가라도 응답에서는 string으로 직렬화 |

### 1.2 인증 헤더
- 모든 보호 엔드포인트: `Authorization: Bearer <JWT>` (SECURITY-08 서버측 검증)
- 관리자 JWT / 테이블 JWT는 §4에 정의된 클레임을 가진다.
- 공개 엔드포인트(로그인 2종)만 인증 불필요.

### 1.3 표준 에러 응답 (SECURITY-15 fail closed / 일반화 메시지)
모든 오류는 아래 형식으로 통일한다. 내부 스택/경로/DB 정보는 노출하지 않는다.

```json
{
  "error": {
    "code": "ORDER_EMPTY",
    "message": "장바구니가 비어 있어 주문을 생성할 수 없습니다.",
    "request_id": "b3f1c2a4-...."
  }
}
```

| HTTP | 사용 상황 |
|---|---|
| 400 Bad Request | 입력 검증 실패(타입/길이/형식) — SECURITY-05 |
| 401 Unauthorized | 토큰 없음/무효/만료 |
| 403 Forbidden | 인가 실패(매장/객체 소유권 위반, IDOR 차단) |
| 404 Not Found | 리소스 없음(또는 소유권 없어 은닉) |
| 409 Conflict | 상태 충돌(예: 종료된 세션에 주문) |
| 422 Unprocessable | 의미 검증 실패(서버 총액 불일치 등) |
| 429 Too Many Requests | 로그인 시도 제한(SECURITY-12) |
| 500 Internal Server Error | 예기치 못한 오류(일반화 메시지) |

**표준 에러 코드(발췌)**: `VALIDATION_ERROR`, `UNAUTHORIZED`, `TOKEN_EXPIRED`, `FORBIDDEN`, `NOT_FOUND`, `ORDER_EMPTY`, `TOTAL_MISMATCH`, `SESSION_CLOSED`, `RATE_LIMITED`, `INTERNAL_ERROR`.

### 1.4 페이지네이션 (목록 조회)
쿼리 파라미터 `?page=<1-base>&size=<1..100>` (기본 page=1, size=20). 응답은 §3의 `PageMeta` 포함.

### 1.5 멀티테넌시
- 모든 데이터 접근은 토큰의 `store_id` 범위로 자동 스코프(테넌트 격리). 클라이언트가 store_id를 임의 지정해도 토큰 범위를 벗어나면 403.

---

## 2. API 인터페이스 (Endpoints)

> 표기: 🔓 공개 · 🔑A 관리자 JWT · 🔑T 테이블 JWT

### 2.1 인증 (AuthRouter)

#### 🔓 `POST /api/admin/login`  — 관리자 로그인 (A1-S1)
Request:
```json
{ "store_id": "store-001", "username": "manager", "password": "••••••••" }
```
Response 200:
```json
{ "access_token": "<JWT>", "token_type": "bearer", "expires_at": "2026-09-01T06:00:00+09:00",
  "store": { "store_id": "store-001", "name": "샘플 매장" } }
```
- 실패: 401 `UNAUTHORIZED`(일반화). 반복 실패 시 429 `RATE_LIMITED`(SECURITY-12).
- 비밀번호는 bcrypt 검증, 평문/로그 노출 금지.

#### 🔓 `POST /api/table/login`  — 테이블 자동 로그인 토큰 발급 (C1-S1)
Request:
```json
{ "store_id": "store-001", "table_no": "5", "table_password": "••••" }
```
Response 200:
```json
{ "access_token": "<JWT>", "token_type": "bearer", "expires_at": "2026-09-01T06:00:00+09:00",
  "table": { "table_id": "tbl-5", "table_no": "5" },
  "session": { "session_id": "sess-abc", "started_at": "2026-08-31T14:00:00+09:00" } }
```
- 세션 만료(16h)/이용완료 시: 401 `TOKEN_EXPIRED` 또는 로그인 실패 — 관리자 재설정 필요 안내.

### 2.2 메뉴 (MenuRouter)

#### 🔑T/🔑A `GET /api/menu`  — 카테고리+메뉴 목록 (C2-S1)
Response 200: `{ "categories": [Category], "menus": [Menu] }` (모델 §3)

#### 🔑T/🔑A `GET /api/menu/{menu_id}`  — 메뉴 상세 (C2-S2)
Response 200: `Menu` · 404 `NOT_FOUND`

### 2.3 주문 (OrderRouter)

#### 🔑T `POST /api/orders`  — 주문 생성 (C4-S1~S3)
Request:
```json
{ "items": [ { "menu_id": "m-101", "quantity": 2 }, { "menu_id": "m-205", "quantity": 1 } ] }
```
- store/table/session은 **토큰에서 도출**(요청 본문으로 받지 않음).
- 서버가 단가 조회 후 `total_amount = Σ(price × quantity)` 재검증. 클라이언트 총액 신뢰 안 함.
Response 201:
```json
{ "order_id": "o-9001", "order_number": "store-001-20260831-001",
  "status": "PENDING", "total_amount": 23000,
  "created_at": "2026-08-31T14:03:00+09:00", "items": [OrderItem] }
```
- 빈 장바구니: 400 `ORDER_EMPTY` · 총액 불일치: 422 `TOTAL_MISMATCH` · 종료 세션: 409 `SESSION_CLOSED`.
- 실패 시 주문 미생성(fail closed).

#### 🔑T `GET /api/orders`  — 현재 세션 주문 내역 (폴링, C5-S1/S2)
- 토큰의 session_id 범위. 쿼리: 페이지네이션(§1.4).
Response 200: `{ "items": [Order], "page_meta": PageMeta, "server_time": "…+09:00" }`
- **폴링 방식**: 전체 조회(§5). 정렬: `created_at` 오름차순(시간순).

#### 🔑A `PATCH /api/orders/{order_id}/status`  — 주문 상태 변경 (A2-S4)
Request: `{ "status": "PREPARING" }`  (허용: `PENDING|PREPARING|COMPLETED`)
Response 200: `Order` · 매장/객체 소유권 위반: 403.

#### 🔑A `DELETE /api/orders/{order_id}`  — 주문 직권 삭제 (A3-S2)
Response 200:
```json
{ "deleted_order_id": "o-9001", "table_id": "tbl-5", "table_total_amount": 12000 }
```
- 삭제 후 테이블 총액 재계산 반환. 감사 로깅(누가/언제/무엇, SECURITY-13).

### 2.4 테이블/세션 (TableRouter)

#### 🔑A `POST /api/tables/{table_id}/setup`  — 테이블 초기 설정 (A3-S1)
Request: `{ "table_no": "5", "table_password": "••••" }`
Response 200:
```json
{ "table_id": "tbl-5", "table_no": "5", "auto_login_enabled": true,
  "session": { "session_id": "sess-abc", "started_at": "…", "expires_at": "…(+16h)" } }
```

#### 🔑A `GET /api/tables/dashboard`  — 테이블별 대시보드 (폴링, A2-S1/S2/S5)
- 쿼리: `?table_id=<옵션 필터>`
Response 200:
```json
{ "tables": [ TableCard ], "server_time": "2026-08-31T14:03:05+09:00" }
```
`TableCard`(§3): 테이블별 `total_amount` + `recent_orders`(최신 3건 미리보기).

#### 🔑A `POST /api/tables/{table_id}/complete`  — 이용 완료/세션 종료 (A3-S3)
Response 200:
```json
{ "table_id": "tbl-5", "archived_order_count": 4,
  "completed_at": "2026-08-31T16:20:00+09:00", "table_total_amount": 0 }
```
- 세션 주문 → OrderHistory 이동, 현재 총액 0 리셋. 원자적 트랜잭션(fail closed).

### 2.5 과거 이력 (HistoryRouter)

#### 🔑A `GET /api/history`  — 과거 주문 내역 (A3-S4)
- 쿼리: `?table_id=&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` + 페이지네이션
Response 200: `{ "items": [HistoryEntry], "page_meta": PageMeta }` — 정렬: `completed_at` 역순.

### 2.6 엔드포인트 요약표

| Method | Path | 인증 | 스토리 |
|---|---|---|---|
| POST | /api/admin/login | 🔓 | A1-S1 |
| POST | /api/table/login | 🔓 | C1-S1 |
| GET | /api/menu | 🔑T/A | C2-S1 |
| GET | /api/menu/{id} | 🔑T/A | C2-S2 |
| POST | /api/orders | 🔑T | C4-S1 |
| GET | /api/orders | 🔑T | C5-S1 |
| PATCH | /api/orders/{id}/status | 🔑A | A2-S4 |
| DELETE | /api/orders/{id} | 🔑A | A3-S2 |
| POST | /api/tables/{id}/setup | 🔑A | A3-S1 |
| GET | /api/tables/dashboard | 🔑A | A2-S1 |
| POST | /api/tables/{id}/complete | 🔑A | A3-S3 |
| GET | /api/history | 🔑A | A3-S4 |

---

## 3. 공유 데이터 모델 (Shared Data Models)

> 백엔드 Pydantic이 소유(SSOT), `shared` 유닛이 대응 TypeScript 타입을 미러링(Q5=A).
> 표기는 언어 중립. TS/Pydantic 구현 시 필드명 동일 유지(snake_case).

### 3.1 열거형 (Enums)
```
OrderStatus = "PENDING" | "PREPARING" | "COMPLETED"      # 표시: 대기중 | 준비중 | 완료
```

### 3.2 도메인 모델
```
Category {
  category_id: string
  name: string
  display_order: int
}

Menu {
  menu_id: string
  category_id: string
  name: string
  price: int              # KRW 정수
  description: string
  image_url: string | null
}

OrderItemInput {           # 주문 생성 요청 항목
  menu_id: string
  quantity: int            # >= 1
}

OrderItem {                # 주문 응답 항목 (스냅샷)
  menu_id: string
  name: string             # 주문 시점 메뉴명 스냅샷
  unit_price: int          # 주문 시점 단가 스냅샷
  quantity: int
  line_amount: int         # unit_price * quantity
}

Order {
  order_id: string
  order_number: string     # "store-001-20260831-001" (§6)
  table_id: string
  session_id: string
  status: OrderStatus
  items: OrderItem[]
  total_amount: int        # Σ line_amount (서버 재검증)
  created_at: string       # ISO8601 +09:00
}

TableCard {                # 대시보드 카드
  table_id: string
  table_no: string
  total_amount: int
  recent_orders: OrderPreview[]   # 최신 3건
  has_new: boolean                # 신규 주문 강조용(옵션)
}

OrderPreview {
  order_id: string
  order_number: string
  created_at: string
  item_summary: string     # 축약 (예: "김치찌개 외 2건")
  total_amount: int
}

HistoryEntry {
  order_id: string
  order_number: string
  table_id: string
  items: OrderItem[]
  total_amount: int
  created_at: string
  completed_at: string     # 이용 완료 시각
}

PageMeta {
  page: int
  size: int
  total: int
}
```

### 3.3 필드 규칙
- 모든 `*_amount`, `price`, `unit_price`, `line_amount`: **정수 KRW**.
- `OrderItem`은 주문 시점 **스냅샷**(메뉴명·단가)을 보존하여 이후 메뉴 변경과 무관하게 이력 일관성 유지.
- `total_amount`는 항상 서버 계산값이 정답(클라이언트는 표시용으로만 자체 계산 — `shared/PricingUtil`, PBT 대상 NFR-T-01).

---

## 4. 인증 토큰 규약 (JWT Claims)

공통 검증: 서명(HS256 등), `exp`(만료), `iss`(발급자) 서버측 검증(SECURITY-08). 민감정보 미포함.

### 4.1 관리자 토큰 (admin JWT, TTL 16h)
```json
{ "iss": "table-order", "sub": "admin:manager", "typ": "admin",
  "store_id": "store-001", "username": "manager",
  "iat": 1735600000, "exp": 1735657600 }
```

### 4.2 테이블 세션 토큰 (table JWT, TTL = 세션 잔여(≤16h))
```json
{ "iss": "table-order", "sub": "table:tbl-5", "typ": "table",
  "store_id": "store-001", "table_id": "tbl-5", "session_id": "sess-abc",
  "iat": 1735600000, "exp": 1735657600 }
```
- 서버는 요청 처리 시 `typ`으로 엔드포인트 접근 권한 구분(테이블 토큰으로 관리자 API 접근 → 403).
- 클라이언트는 localStorage 저장(customer-web 자동 로그인). 로그아웃/이용완료 시 서버측 세션 무효화로 fail closed.

---

## 5. 이벤트 / 준실시간 규약 (Event & Polling Conventions)

> 본 시스템은 **폴링 기반**(WebSocket/SSE 없음, Q4=A). "이벤트"는 폴링으로 감지되는 **논리적 상태 변화**를 의미하며, 아래 규약으로 표준화한다.

### 5.1 폴링 규약
| 소비자 | 엔드포인트 | 주기 | 방식 |
|---|---|---|---|
| customer-web (OrderHistoryView) | `GET /api/orders` | ~2000ms | 전체 조회 |
| admin-web (DashboardGrid) | `GET /api/tables/dashboard` | ~2000ms | 전체 조회 |

- 폴링 주기 기본값 **2000ms**(NFR-P-01 "2초 이내 표시" 목표). `shared/PollingHook`가 표준 구현.
- 각 응답은 `server_time`(Asia/Seoul)을 포함하여 클라이언트가 신규/변경 판단(예: `created_at > 직전 폴링 server_time` → 신규 강조).
- 폴링 실패(네트워크/5xx)는 조용히 재시도(다음 주기), 사용자에게 일반화 오류만 필요 시 표시.

### 5.2 논리 도메인 이벤트 (폴링으로 관찰되는 상태 전이)
| 이벤트 | 트리거 | 관찰 방법 | 소비 화면 반응 |
|---|---|---|---|
| `order.created` | 고객 주문 생성 | 대시보드 폴링에 신규 order 등장 | 관리자 카드에 신규 주문 강조(A2-S2) |
| `order.status_changed` | 관리자 상태 변경 | 고객/관리자 폴링에 status 변경 | 고객 내역 상태 갱신(C5-S2), 대시보드 반영 |
| `order.deleted` | 관리자 직권 삭제 | 폴링 목록에서 사라짐 + 총액 변동 | 카드 총액 재계산 표시(A3-S2) |
| `session.completed` | 관리자 이용 완료 | 대시보드에서 테이블 총액 0/주문 비움 | 카드 리셋, 과거 이력으로 이동(A3-S3) |

- **전달 보장**: 폴링 특성상 최종 일관성(eventual). 각 폴링은 현재 서버 상태의 스냅샷이 정답.
- **순서**: 상태는 항상 서버 최신값 기준. 클라이언트는 낙관적 업데이트 후 폴링 결과로 정정 가능.

### 5.3 상태 전이 규칙
```
PENDING ──(관리자)──> PREPARING ──(관리자)──> COMPLETED
```
- 역방향 전이 허용 여부는 Functional Design(backend-api)에서 확정. 기본: 관리자는 임의 상태 지정 가능(MVP), 단 인가된 매장 범위 내에서만.

---

## 6. 주문 번호 채번 규약 (Order Number)
- 형식: `{store_id}-{YYYYMMDD}-{NNN}` (예: `store-001-20260831-001`)
- `NNN`: 해당 매장·해당 일자(Asia/Seoul) 기준 001부터 증가하는 3자리(초과 시 자릿수 확장).
- 채번은 backend-api(OrderService)가 원자적으로 수행. 클라이언트는 응답의 `order_number`를 그대로 표시.

---

## 7. 유닛별 계약 책임 (Responsibility Map)

| 유닛 | 계약상 책임 |
|---|---|
| **backend-api** | 본 계약의 **제공자/SSOT**. 엔드포인트·모델·에러·토큰·채번 구현. OpenAPI가 본 문서와 일치하도록 유지 |
| **shared** | §3 모델의 TS 타입 미러, §1.3 에러 타입, `ApiClient`(인증 헤더·에러 정규화), `PollingHook`(§5.1), `PricingUtil`(총액 표시 계산) |
| **customer-web** | 🔑T 엔드포인트 소비, 테이블 JWT 저장/첨부, 주문/내역 폴링 규약 준수 |
| **admin-web** | 🔑A 엔드포인트 소비, 관리자 JWT 저장/만료 처리, 대시보드 폴링 규약 준수 |

---

## 8. 보안 계약 요건 (Security Contract — SECURITY Baseline)
- **SECURITY-05**: 모든 요청 본문/쿼리는 서버에서 스키마 검증(타입·길이·형식). 본문 크기 제한.
- **SECURITY-08**: 모든 보호 엔드포인트 deny-by-default + 토큰 `typ`/`store_id`/객체 소유권 검증(IDOR 방지). CORS는 허용 오리진 명시(고객/관리자 앱 도메인).
- **SECURITY-04**: HTML 제공 응답에 보안 헤더(CSP 등). API-only 응답은 해당 시 적용.
- **SECURITY-12**: bcrypt 해시, 로그인 rate limit(429), 세션 서버측 만료·무효화.
- **SECURITY-03/15**: 구조화 로깅(request_id 포함, 민감정보 마스킹), 전역 에러 핸들러(§1.3), fail closed.

---

## 9. 변경 관리 (Contract Change Process)
- 본 계약은 **하위 호환 우선**. 필드 추가는 minor, 필드 제거/의미 변경은 major.
- 변경 시: ① 본 문서 갱신 → ② backend-api OpenAPI 반영 → ③ `shared` 타입 동기화 → ④ 프론트엔드 반영.
- 변경 이력을 아래 표에 기록.

| 버전 | 날짜 | 변경 내용 |
|---|---|---|
| v1.0 | 2026-08-31 | 최초 확정 (INCEPTION 종료 시점) |

---

## 10. 참조
- 요구사항: `aidlc-docs/inception/requirements/requirements.md`
- 스토리: `aidlc-docs/inception/user-stories/stories.md`
- 애플리케이션 설계: `aidlc-docs/inception/application-design/*`
- 유닛 분해: `aidlc-docs/inception/application-design/unit-of-work*.md`
