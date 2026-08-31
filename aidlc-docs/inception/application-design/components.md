# Components — 테이블오더 서비스

> 고수준 컴포넌트 식별 및 책임 정의. 상세 비즈니스 로직·스키마는 Functional Design(per-unit)에서 확정.
> 설계 결정 반영: 백엔드 계층형(Q1=A), 프론트엔드 2앱+공유(Q2=A), 테이블 세션 JWT(Q3=A), 폴링 전체 조회(Q4=A), 매장별 일자 순번(Q5=A), REST+OpenAPI(Q6=A).

---

## 1. 시스템 구성요소 개요

| 논리 구성요소 | 기술 | 역할 |
|---|---|---|
| **customer-web** | React + TypeScript | 고객용 태블릿 웹 UI (자동 로그인·메뉴·장바구니·주문·내역) |
| **admin-web** | React + TypeScript | 관리자용 웹 UI (로그인·대시보드·상태변경·테이블/세션 관리·과거 내역) |
| **shared** | TypeScript 라이브러리 | API 클라이언트·공통 타입·공통 UI 컴포넌트 (두 앱 공유) |
| **backend-api** | Python + FastAPI | REST API, 인증/인가, 비즈니스 로직, 데이터 접근 |
| **datastore** | SQLite | 관계형 데이터 저장 (파일 기반) |

---

## 2. 백엔드 컴포넌트 (계층형 — Q1=A)

계층: **Router (HTTP) → Service (비즈니스 로직) → Repository (데이터 접근) → Model (ORM/스키마)**
횡단 관심사: Security Middleware, Logging, Error Handler.

### 2.1 Router 계층 (HTTP 경계)

| 컴포넌트 | 목적 | 주요 책임 | 인터페이스(엔드포인트 그룹) |
|---|---|---|---|
| **AuthRouter** | 인증 엔드포인트 | 관리자 로그인, 테이블 로그인(자동 로그인용 토큰 발급) | `POST /api/admin/login`, `POST /api/table/login` |
| **MenuRouter** | 메뉴 조회 | 카테고리·메뉴 목록/상세 반환 | `GET /api/menu`, `GET /api/menu/{id}` |
| **OrderRouter** | 주문 처리 | 주문 생성, 현재 세션 주문 조회(폴링), 상태 변경, 삭제 | `POST /api/orders`, `GET /api/orders`, `PATCH /api/orders/{id}/status`, `DELETE /api/orders/{id}` |
| **TableRouter** | 테이블/세션 관리 | 테이블 초기 설정, 대시보드 조회(폴링), 이용 완료(세션 종료) | `POST /api/tables/{id}/setup`, `GET /api/tables/dashboard`, `POST /api/tables/{id}/complete` |
| **HistoryRouter** | 과거 이력 조회 | 테이블별 과거 주문(날짜 필터) 조회 | `GET /api/history` |

> 모든 Router는 요청 검증(Pydantic 스키마, SECURITY-05)과 인가 의존성(SECURITY-08)을 적용한다.

### 2.2 Service 계층 (비즈니스 로직 오케스트레이션)

| 컴포넌트 | 목적 | 주요 책임 |
|---|---|---|
| **AuthService** | 인증/토큰 | 관리자 자격증명 검증(bcrypt), 테이블 로그인 검증, JWT 발급/검증, 로그인 시도 제한 |
| **MenuService** | 메뉴 조회 | 매장 범위 메뉴/카테고리 조회 |
| **OrderService** | 주문 로직 | 주문 생성(서버측 총액 재검증), 주문 번호 채번, 세션 주문 조회, 상태 변경, 삭제 후 총액 재계산 |
| **TableSessionService** | 세션 라이프사이클 | 테이블 설정·16시간 세션 생성, 대시보드 집계(테이블별 총액·최신 3건), 이용 완료(이력 이동·리셋) |
| **HistoryService** | 과거 이력 | 세션 종료 시 OrderHistory 기록, 과거 주문 조회·날짜 필터 |

> **보안 로직 격리(SECURITY-11)**: 인증/인가/토큰 로직은 AuthService + Security Middleware에 집중, 다른 서비스에 분산 금지.

### 2.3 Repository 계층 (데이터 접근)

| 컴포넌트 | 목적 | 담당 엔티티 |
|---|---|---|
| **StoreRepository** | 매장 데이터 | Store, AdminUser |
| **TableRepository** | 테이블/세션 데이터 | Table, TableSession |
| **MenuRepository** | 메뉴 데이터 | Category, Menu |
| **OrderRepository** | 주문 데이터 | Order, OrderItem |
| **HistoryRepository** | 과거 이력 데이터 | OrderHistory |

> 모든 쿼리는 파라미터화(SECURITY-05, SQL 인젝션 방지). 모든 조회/변경은 매장 범위(store_id)로 스코프.

### 2.4 횡단 관심사 컴포넌트

| 컴포넌트 | 목적 | 주요 책임 | 관련 보안 규칙 |
|---|---|---|---|
| **SecurityMiddleware** | 인가 게이트웨이 | JWT 서버측 검증(서명·만료·발급자), deny-by-default, 매장/객체 소유권 검증(IDOR 방지) | SECURITY-08 |
| **SecurityHeadersMiddleware** | 보안 HTTP 헤더 | CSP·X-Content-Type-Options·X-Frame-Options·Referrer-Policy·HSTS 설정 | SECURITY-04 |
| **RequestValidation (Pydantic)** | 입력 검증 | 타입·길이·형식 검증, 요청 본문 크기 제한 | SECURITY-05 |
| **LoggingComponent** | 구조화 로깅 | 타임스탬프·요청 ID·레벨·메시지, 민감정보 마스킹 | SECURITY-03 |
| **GlobalErrorHandler** | 전역 예외 처리 | 안전 실패(fail closed), 일반화 오류 응답, 리소스 정리 | SECURITY-15 |
| **RateLimiter** | 로그인 시도 제한 | 반복 로그인 실패 잠금/지연 | SECURITY-11, SECURITY-12 |

---

## 3. 고객 프론트엔드 컴포넌트 (customer-web)

| 컴포넌트 | 목적 | 주요 책임 |
|---|---|---|
| **AutoLoginGuard** | 자동 로그인 | localStorage의 테이블 설정/토큰 확인, 유효 시 메뉴로 진입, 무효 시 재설정 안내 |
| **MenuView** | 메뉴 화면(기본) | 카테고리별 카드형 메뉴 표시, 카테고리 이동 |
| **MenuDetail** | 메뉴 상세 | 메뉴명·가격·설명·이미지(플레이스홀더 폴백) |
| **CartPanel** | 장바구니 | 담기/수량 증감/비우기, 실시간 총액, localStorage 유지 |
| **OrderConfirm** | 주문 확정 | 주문 내역 확인, 확정 요청, 성공(주문번호·5초 후 리다이렉트)/실패(장바구니 유지) 처리 |
| **OrderHistoryView** | 현재 세션 주문 내역 | 시간순 목록, 상태 표시, ~2초 폴링 갱신, 페이지네이션/무한스크롤 |
| **CustomerApiClient** (shared 사용) | 서버 통신 | 테이블 JWT 첨부, 주문/조회 API 호출 |

---

## 4. 관리자 프론트엔드 컴포넌트 (admin-web)

| 컴포넌트 | 목적 | 주요 책임 |
|---|---|---|
| **AdminLogin** | 매장 로그인 | 매장식별자·사용자명·비밀번호 입력, JWT 저장, 오류 처리 |
| **AuthSessionGuard** | 세션 유지 | JWT 보관·만료(16시간) 감지·자동 로그아웃, 새로고침 유지 |
| **DashboardGrid** | 테이블별 대시보드 | 테이블 카드 그리드(총액·최신 3건), ~2초 폴링, 신규 주문 강조, 테이블 필터 |
| **OrderDetailModal** | 주문 상세 | 카드 클릭 시 전체 메뉴 목록·상세 표시 |
| **OrderStatusControl** | 상태 변경 | 대기중/준비중/완료 전환 요청 |
| **OrderDeleteAction** | 주문 삭제 | 확인 팝업 → 삭제 → 총액 재계산 피드백 |
| **TableSetupForm** | 테이블 초기 설정 | 테이블 번호·비밀번호 설정, 세션 생성·자동 로그인 활성화 |
| **SessionCompleteAction** | 이용 완료 | 확인 팝업 → 세션 종료(이력 이동·리셋) |
| **OrderHistoryView (Admin)** | 과거 내역 | 테이블별 과거 주문(시간 역순), 날짜 필터 |
| **AdminApiClient** (shared 사용) | 서버 통신 | 관리자 JWT 첨부, 관리 API 호출 |

---

## 5. 공유 라이브러리 컴포넌트 (shared)

| 컴포넌트 | 목적 | 주요 책임 |
|---|---|---|
| **ApiClient** | HTTP 클라이언트 | 공통 fetch 래퍼, 토큰 첨부, 오류 정규화 |
| **Types** | 공통 타입 | Menu/Order/OrderItem/Table/Session/Status DTO 타입 정의 |
| **UiKit** | 공통 UI | 터치 친화 버튼(≥44x44px), 카드, 모달, 로딩/에러 표시 |
| **PricingUtil** | 금액 계산 | 장바구니/주문 총액 계산(순수 함수, PBT 대상 NFR-T-01) |
| **PollingHook** | 폴링 훅 | ~2초 주기 조회 훅(useOrderPolling 등) |

---

## 6. 컴포넌트 인터페이스 요약 (경계)

- **customer-web ↔ backend-api**: REST/HTTPS, 테이블 세션 JWT (Q3=A)
- **admin-web ↔ backend-api**: REST/HTTPS, 관리자 JWT (16시간)
- **backend-api ↔ datastore**: Repository 계층 통한 파라미터화 SQL (SQLite)
- **문서화**: FastAPI 자동 OpenAPI `/docs` (Q6=A)
