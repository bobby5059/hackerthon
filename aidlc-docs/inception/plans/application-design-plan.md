# Application Design Plan — 테이블오더 서비스

본 계획은 애플리케이션 설계 단계에서 수행할 작업과, 설계 결정을 위해 사용자 입력이 필요한 질문을 정리한다.
**아래 [Answer]: 태그에 직접 답변을 채워주세요.** 모든 질문에 답변이 완료되면 승인을 요청드립니다.

> 설계 범위: **고수준 컴포넌트 식별 + 서비스 계층 + 컴포넌트 의존성/통신 패턴**
> (상세 비즈니스 로직·데이터 스키마는 이후 Functional Design(per-unit, CONSTRUCTION)에서 정의)

---

## Part A: 설계 결정 질문 (사용자 입력 필요)

### Question 1 — 백엔드 코드 구조
FastAPI 백엔드의 내부 계층 구조를 어떻게 조직할까요?

A) 계층형 (routers → services → repositories → models) — 라우터는 HTTP 처리, 서비스는 비즈니스 로직, 리포지토리는 SQLite 접근으로 분리 *(권장 — 보안-11 관심사 분리에 부합)*

B) 기능/도메인별 모듈 (auth/, menu/, order/, table/ 각각에 router+service+repo 응집)

C) 단순 2계층 (routers → 직접 DB 접근) — MVP 최소 구조

D) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 2 — 프론트엔드 앱 구성
고객용/관리자용 두 React+TS 앱을 어떻게 구성할까요?

A) 두 개의 독립 앱 + 공유 라이브러리 (customer-web / admin-web / shared: API 클라이언트·타입·공통 UI) *(권장 — 타입·API 호출 재사용, 관심사 분리)*

B) 완전히 독립된 두 앱 (공유 코드 없음, 각자 타입·API 클라이언트 중복 허용) — 가장 단순

C) 단일 앱에서 라우팅으로 고객/관리자 화면 분리 (하나의 빌드)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 3 — 고객(테이블) 세션 인증 방식
고객 태블릿의 자동 로그인 후, 이후 API 요청에서 테이블 세션을 어떻게 인증/식별할까요?

A) 테이블 세션 토큰(JWT) 발급 — 최초 로그인 시 서버가 매장·테이블·세션 ID를 담은 토큰 발급, 클라이언트 localStorage 저장, 이후 요청 헤더로 전송, 서버측 검증 *(권장 — 관리자 JWT와 일관, SECURITY-08 서버측 검증)*

B) 불투명 세션 토큰 + 서버측 세션 저장소 조회 (DB의 Session 테이블에서 유효성 확인)

C) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 4 — 주문 폴링 API 방식
고객 주문 내역 및 관리자 대시보드의 폴링(~2초) 조회 방식은?

A) 전체 조회 — 매 폴링마다 현재 세션/매장의 주문 목록 전체를 반환 *(권장 — 구현 단순, MVP 데이터 규모에 충분)*

B) 델타 조회 — `since`(타임스탬프/버전) 파라미터로 변경분만 반환하여 트래픽 최소화

C) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 5 — 주문 번호 체계
고객·관리자에게 표시되는 "주문 번호"의 생성 규칙은?

A) 매장별 일자 기준 순번 (예: 매장A-20260831-001) — 사람이 읽기 쉬움 *(권장)*

B) 매장별 전체 통합 순번 (예: 1, 2, 3 …) — 매장 내 단조 증가

C) 서버 내부 ID(자동증가/UUID)를 그대로 노출

D) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 6 — API 스타일 및 문서화
백엔드 API 스타일과 문서화 수준은?

A) REST + FastAPI 자동 OpenAPI(/docs) 문서 *(권장 — FastAPI 기본 제공)*

B) REST만 사용, 자동 문서화(/docs)는 비활성화

C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Part B: 설계 산출물 생성 계획 (승인 후 실행)

**질문 답변 및 승인 완료 후** 아래 산출물을 생성한다:

- [x] `application-design/components.md` — 컴포넌트 정의, 목적, 책임, 인터페이스
  - [x] 백엔드 컴포넌트 (Auth, Menu, Order, Table/Session, OrderHistory, 데이터 접근, 보안 미들웨어 등)
  - [x] 고객 프론트엔드 컴포넌트 (자동 로그인, 메뉴, 장바구니, 주문, 주문 내역)
  - [x] 관리자 프론트엔드 컴포넌트 (로그인, 대시보드/폴링, 주문 상세/상태, 테이블·세션 관리, 과거 내역)
- [x] `application-design/component-methods.md` — 컴포넌트별 메서드 시그니처(입출력 타입, 고수준 목적; 상세 규칙은 Functional Design)
- [x] `application-design/services.md` — 서비스 정의, 책임, 오케스트레이션 패턴 (AuthService, OrderService, TableSessionService, MenuService 등)
- [x] `application-design/component-dependency.md` — 의존성 매트릭스, 통신 패턴, 데이터 흐름 다이어그램 (Mermaid + 텍스트 대안)
- [x] `application-design/application-design.md` — 위 문서를 통합한 종합 설계 문서
- [x] 설계 완전성·일관성 검증
- [x] Security Baseline 적용성 평가 (SECURITY-08 인가 경계, SECURITY-11 보안 로직 모듈 분리, SECURITY-05 입력 검증 배치 등)
- [x] `aidlc-state.md` 갱신 및 완료 메시지 제시

---

## Part C: 잠정 설계 방향 (요구사항 기반, 질문 답변으로 확정)

- **논리 구성요소**: 고객 웹(React+TS) · 관리자 웹(React+TS) · FastAPI 백엔드 · SQLite
- **핵심 도메인**: Store, Table, TableSession, Menu/Category, Order/OrderItem, OrderHistory, AdminUser
- **보안 관심사 격리(SECURITY-11)**: 인증/인가 로직을 전용 모듈(Auth/Security 미들웨어)로 분리
- **인가 경계(SECURITY-08)**: 모든 보호 엔드포인트는 매장 범위(테넌트) + 객체 소유권 검증(테이블/주문/세션)
- **타임존(NFR-D-03)**: 모든 타임스탬프 Asia/Seoul 기록·표시
