# Application Design — 테이블오더 서비스 (종합)

> 본 문서는 `components.md`, `component-methods.md`, `services.md`, `component-dependency.md`를 통합한 애플리케이션 설계 요약이다.
> 상세 비즈니스 로직·데이터 스키마는 이후 Functional Design(per-unit, CONSTRUCTION)에서 확정한다.

---

## 1. 설계 결정 요약 (Application Design 질문 답변)

| # | 결정 사항 | 선택 |
|---|---|---|
| Q1 | 백엔드 코드 구조 | **계층형** (Router → Service → Repository → Model) |
| Q2 | 프론트엔드 구성 | **독립 2앱 + 공유 라이브러리** (customer-web / admin-web / shared) |
| Q3 | 고객 세션 인증 | **테이블 세션 JWT** (localStorage 저장, 서버측 검증) |
| Q4 | 폴링 방식 | **전체 조회** (~2초 주기, 현재 세션/매장 주문 전체 반환) |
| Q5 | 주문 번호 체계 | **매장별 일자 순번** (예: STORE-20260831-001) |
| Q6 | API 스타일 | **REST + FastAPI 자동 OpenAPI(/docs)** |

---

## 2. 아키텍처 개요

- **5개 논리 구성요소**: customer-web(React+TS), admin-web(React+TS), shared(TS 라이브러리), backend-api(FastAPI), datastore(SQLite)
- **백엔드 계층형**: Router(HTTP) → Service(비즈니스) → Repository(데이터) → Model, 횡단 관심사(Security/Headers/Validation/Logging/ErrorHandler/RateLimiter)
- **통신**: 프론트엔드 → 백엔드 REST/JSON, 각각 JWT 인증; 준실시간은 ~2초 폴링(푸시 없음)
- **멀티테넌시**: 모든 데이터/서비스 메서드는 `store_id`로 스코프(MVP는 단일 매장 시드)

---

## 3. 컴포넌트 요약

- **백엔드 Router**: Auth / Menu / Order / Table / History
- **백엔드 Service**: AuthService, MenuService, OrderService, TableSessionService, HistoryService
- **백엔드 Repository**: Store, Table, Menu, Order, History
- **횡단**: SecurityMiddleware, SecurityHeadersMiddleware, RequestValidation, LoggingComponent, GlobalErrorHandler, RateLimiter
- **customer-web**: AutoLoginGuard, MenuView, MenuDetail, CartPanel, OrderConfirm, OrderHistoryView
- **admin-web**: AdminLogin, AuthSessionGuard, DashboardGrid, OrderDetailModal, OrderStatusControl, OrderDeleteAction, TableSetupForm, SessionCompleteAction, OrderHistoryView(Admin)
- **shared**: ApiClient, Types, UiKit, PricingUtil, PollingHook

*(상세 메서드는 `component-methods.md`, 의존성/데이터 흐름은 `component-dependency.md` 참조)*

---

## 4. 핵심 도메인 개체 (예비 — Functional Design에서 확정)

Store, AdminUser, Table, TableSession, Category, Menu, Order, OrderItem, OrderHistory

---

## 5. Security Baseline 적용성 평가 (Application Design 단계)

> Security Baseline **활성화**. 아래는 이 설계 단계에서의 적용성 평가이며, 구현 준수는 이후 NFR/Code 단계에서 검증된다.

| 규칙 | 상태 | 설계 반영 / 사유 |
|---|---|---|
| SECURITY-01 (암호화 at-rest/transit) | **N/A (이 단계)** | 로컬 SQLite/로컬 배포. 저장 암호화·TLS는 인프라/배포 사안으로 프로덕션 시 재검토(요구사항 4.3 명시) |
| SECURITY-02 (네트워크 중개자 로깅) | **N/A** | 로컬 MVP에 LB/API GW/CDN 없음 |
| SECURITY-03 (앱 로깅) | **반영** | LoggingComponent를 횡단 컴포넌트로 정의, 민감정보 마스킹 |
| SECURITY-04 (보안 HTTP 헤더) | **반영** | SecurityHeadersMiddleware 컴포넌트 정의 |
| SECURITY-05 (입력 검증) | **반영** | RequestValidation(Pydantic)을 모든 Router 공통 의존으로 정의, 파라미터화 SQL |
| SECURITY-06 (최소 권한 IAM) | **N/A** | 클라우드 IAM 없음(로컬) |
| SECURITY-07 (네트워크 구성) | **N/A** | 로컬, VPC/보안그룹 없음 |
| SECURITY-08 (앱 수준 인가) | **반영** | SecurityMiddleware: JWT 서버측 검증, deny-by-default, 매장/객체 소유권 검증(IDOR 방지) |
| SECURITY-09 (하드닝/오설정) | **부분 반영** | GlobalErrorHandler가 일반화 오류 응답; 기타(기본 계정/샘플 제거)는 Code/Build 단계 |
| SECURITY-10 (공급망) | **N/A (이 단계)** | lock 파일·스캔은 Code/Build 단계 |
| SECURITY-11 (보안 설계 원칙) | **반영** | 인증/인가 로직을 AuthService+SecurityMiddleware로 격리; RateLimiter로 로그인 rate limit; 오남용 케이스(IDOR·브루트포스) 고려 |
| SECURITY-12 (인증/자격증명) | **반영** | AuthService: bcrypt 검증, JWT 세션 만료, RateLimiter 브루트포스 방지, 하드코딩 금지 |
| SECURITY-13 (무결성 검증) | **부분 반영** | 주문 삭제/상태변경 감사 로깅 설계; SRI/역직렬화는 Code 단계 |
| SECURITY-14 (알림/모니터링) | **N/A (이 단계)** | 로컬 MVP, 중앙 알림/보존정책 없음(프로덕션 재검토) |
| SECURITY-15 (예외 처리/안전 실패) | **반영** | GlobalErrorHandler, fail closed, 트랜잭션 롤백/리소스 정리 설계 |

**블로킹 보안 findings**: 없음 (이 단계에서 적용 가능한 규칙은 모두 설계에 반영, 나머지는 후속 단계/인프라 사안으로 N/A).

---

## 6. 스토리 커버리지 확인

- 고객: C1(인증/세션), C2(메뉴), C3(장바구니), C4(주문), C5(내역) → 대응 컴포넌트·서비스 정의됨
- 관리자: A1(인증), A2(모니터링), A3(테이블/세션 관리) → 대응 컴포넌트·서비스 정의됨
- Won't(C4-S4 고객 수정): 수정/취소 경로 미제공(설계상 관리자 삭제만 존재)로 반영

---

## 7. 다음 단계

- **Units Generation**: 본 설계를 근거로 작업 단위(backend-api / customer-web / admin-web 등) 분해
- 이후 각 유닛에 대해 Functional Design → NFR → Code Generation 순으로 진행
