# Unit of Work — 테이블오더 서비스

> 시스템을 개발 작업 단위로 분해한 정의 문서. 각 유닛은 per-unit 루프(Functional Design → NFR → Code)의 대상이 된다.
> 분해 결정: **4개 유닛(Q1=B — 사용자 요청으로 shared를 독립 유닛으로 분리)**, 단일 모노레포(Q2=A), 구현 순서 backend→shared→customer→admin(Q3 파생), OpenAPI 계약 SSOT(Q4=A), 백엔드 소유 도메인 타입(Q5=A).

---

## 1. 유닛 개요

| 유닛 | 유형 | 기술 | 책임 |
|---|---|---|---|
| **backend-api** | 독립 실행 서비스 | Python + FastAPI + SQLite | 인증/인가, 메뉴/주문/테이블·세션/이력 REST API, 비즈니스 로직, 데이터 저장·시드, 보안 미들웨어 |
| **shared** | 공유 라이브러리 (독립 유닛) | TypeScript | ApiClient, 도메인 TS 타입(백엔드 Pydantic 미러), UiKit, PricingUtil, PollingHook — 두 프론트엔드가 소비 |
| **customer-web** | 프론트엔드 앱 | React + TypeScript | 고객 태블릿 UI: 자동 로그인, 메뉴, 장바구니, 주문, 현재 세션 내역 |
| **admin-web** | 프론트엔드 앱 | React + TypeScript | 관리자 UI: 로그인, 대시보드/폴링, 상태변경/삭제, 테이블·세션 관리, 과거 내역 |

> `shared`는 **독립 개발 유닛**으로, 자체 per-unit 루프(Functional Design → NFR → Code)를 거쳐 개발된다. backend-api 계약 확정 후, 두 프론트엔드 유닛 이전에 개발된다.

---

## 2. 유닛별 상세

### 2.1 backend-api
- **목적**: 시스템의 단일 백엔드. 모든 데이터·비즈니스 규칙·보안의 권위 있는 원천.
- **포함 모듈(계층형)**: Router(Auth/Menu/Order/Table/History) · Service(Auth/Menu/Order/TableSession/History) · Repository(Store/Table/Menu/Order/History) · Model(Pydantic + SQLite 스키마) · 횡단(Security/Headers/Validation/Logging/ErrorHandler/RateLimiter)
- **담당 스토리**: 모든 고객·관리자 스토리의 서버측(C1-S1/S2, C4-S1~S3, C5-S1, A1-S1~S3, A2-S2/S4, A3-S1~S4)
- **인터페이스 계약**: FastAPI OpenAPI(/docs) = 계약 SSOT (Q4=A)
- **데이터 소유**: Store, AdminUser, Table, TableSession, Category, Menu, Order, OrderItem, OrderHistory (도메인 타입 소유처, Q5=A)

### 2.2 customer-web
- **목적**: 고객 태블릿 웹 UI.
- **포함 컴포넌트**: AutoLoginGuard, MenuView, MenuDetail, CartPanel, OrderConfirm, OrderHistoryView
- **담당 스토리**: C1~C5 (고객 전 스토리)
- **의존**: backend-api(REST, 테이블 JWT), shared

### 2.3 admin-web
- **목적**: 관리자 웹 UI.
- **포함 컴포넌트**: AdminLogin, AuthSessionGuard, DashboardGrid, OrderDetailModal, OrderStatusControl, OrderDeleteAction, TableSetupForm, SessionCompleteAction, OrderHistoryView(Admin)
- **담당 스토리**: A1~A3 (관리자 전 스토리)
- **의존**: backend-api(REST, 관리자 JWT), shared

### 2.4 shared (독립 유닛)
- **목적**: 두 프론트엔드가 공유하는 라이브러리. 독립 유닛으로 별도 개발.
- **포함**: ApiClient, Types(도메인 TS 타입 — 백엔드 Pydantic 미러, Q5=A), UiKit(터치 버튼 ≥44x44px 등), PricingUtil(금액 계산 순수함수 — PBT 대상 NFR-T-01), PollingHook(~2초)
- **담당 스토리(횡단 지원)**: PricingUtil→C3-S1/C4-S1, UiKit→C2-S3 등 UI 전반, PollingHook→C5-S2/A2-S2, ApiClient/Types→모든 서버 통신
- **의존**: backend-api(계약/타입 참조, 코드 의존은 아님 — 타입 미러링)
- **소비처**: customer-web, admin-web

---

## 3. 코드 조직 전략 (Greenfield — 단일 모노레포, Q2=A)

**애플리케이션 코드는 워크스페이스 루트에 위치** (문서는 `aidlc-docs/`에만). 제안 디렉터리 구조:

```
table-order/                      # 워크스페이스 루트 (애플리케이션 코드)
├── backend/                      # 유닛: backend-api
│   ├── app/
│   │   ├── routers/              # Auth/Menu/Order/Table/History
│   │   ├── services/             # 비즈니스 로직
│   │   ├── repositories/         # SQLite 데이터 접근
│   │   ├── models/               # Pydantic 스키마 + ORM/테이블 정의
│   │   ├── core/                 # security, config, logging, errors, middleware
│   │   └── main.py               # FastAPI 엔트리포인트
│   ├── seed/                     # 단일 매장 시드 데이터(매장·테이블·메뉴·관리자)
│   ├── tests/                    # 단위/통합/PBT
│   ├── requirements.txt / lock   # 의존성 고정(SECURITY-10)
│   └── table_order.db            # SQLite 파일(런타임 생성)
│
├── frontend/
│   ├── shared/                   # 지원 라이브러리: ApiClient/Types/UiKit/PricingUtil/PollingHook
│   ├── customer/                 # 유닛: customer-web
│   │   ├── src/
│   │   └── package.json
│   └── admin/                    # 유닛: admin-web
│       ├── src/
│       └── package.json
│
├── aidlc-docs/                   # 문서 전용
└── README.md
```

> 구체 구조는 Code Generation 단계에서 각 유닛에 맞게 확정. 위는 지침적 골격.

---

## 4. 구현 순서 (4개 유닛)

```
1) backend-api    — API 계약(OpenAPI) 및 데이터/보안 확정
2) shared         — 공유 라이브러리(ApiClient/Types/UiKit/PricingUtil/PollingHook), 백엔드 계약 기반 TS 타입 확정
3) customer-web   — 고객 앱 (shared 소비)
4) admin-web      — 관리자 앱 (shared 재사용)
```

각 유닛은 per-unit 루프(Functional Design → NFR Requirements → NFR Design → [Infrastructure Design=SKIP] → Code Generation)를 완료한 뒤 다음 유닛으로 이동한다. shared는 backend-api 계약 확정 후, 프론트엔드 유닛 이전에 개발된다.

---

## 5. 유닛 경계 검증

- **단방향 의존**: 프론트엔드 유닛 → backend-api (역방향 없음). shared는 프론트엔드에 소비되되 앱에 의존하지 않음. shared → backend-api는 타입 미러링(런타임 코드 의존 아님).
- **독립 배포성**: backend-api는 독립 실행. shared는 독립 빌드 라이브러리(npm 워크스페이스 패키지). 프론트엔드 앱은 각각 독립 빌드/서브.
- **계약 안정성**: backend-api 먼저 구현으로 OpenAPI 계약 확정 → shared에서 TS 타입 확정 → 프론트엔드가 소비 → 재작업 최소화.
- **스토리 완전 배정**: 모든 스토리가 유닛에 배정됨(§ unit-of-work-story-map.md 참조).
