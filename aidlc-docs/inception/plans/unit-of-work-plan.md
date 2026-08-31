# Unit of Work Plan — 테이블오더 서비스

본 계획은 시스템을 개발 작업 단위(Unit of Work)로 분해하기 위한 계획과, 분해 결정을 위해 사용자 입력이 필요한 질문을 정리한다.
**아래 [Answer]: 태그에 직접 답변을 채워주세요.** 답변 완료 후 승인을 요청드립니다.

> 근거: `application-design/*` (백엔드 계층형, 프론트엔드 2앱 + shared, 5개 논리 구성요소)

---

## Part 1-A: 분해 결정 질문 (사용자 입력 필요)

### Question 1 — 유닛 분해 단위
시스템을 어떤 단위로 분해할까요?

A) **3개 유닛**: `backend-api`(FastAPI+SQLite), `customer-web`(고객 앱), `admin-web`(관리자 앱) — `shared`는 프론트엔드가 공유하는 지원 라이브러리 *(권장 — 애플리케이션 설계와 1:1 정합)*

B) **4개 유닛**: 위 3개 + `shared`를 독립 유닛으로 분리

C) **2개 유닛**: `backend-api` + `frontend`(고객/관리자 통합)

D) Other (please describe after [Answer]: tag below)

[Answer]: B  <!-- 최초 A로 답변했으나, 이후 사용자 요청("unit 4개로 나누자")에 따라 B(shared 독립 유닛)로 변경 -->

### Question 2 — 코드 저장소/배포 모델 (Greenfield)
코드 조직 및 저장소 구조는?

A) **단일 모노레포** — 하나의 리포지토리 아래 `backend/`, `frontend/customer/`, `frontend/admin/`, `frontend/shared/` 서브디렉터리 *(권장 — 로컬 MVP, 통합 개발 용이)*

B) 유닛별 개별 리포지토리 (multi-repo)

C) Other (please describe after [Answer]: tag below)

[Answer]:A

### Question 3 — 유닛 구현/개발 순서
per-unit 루프(Functional Design → NFR → Code)를 어떤 순서로 진행할까요?

A) **backend-api → customer-web → admin-web** — API 계약을 먼저 확정 후 프론트엔드 구현 *(권장 — 프론트엔드가 API에 의존)*

B) backend-api → admin-web → customer-web

C) 프론트엔드 먼저(계약 우선 설계) → backend-api

D) Other (please describe after [Answer]: tag below)

[Answer]:A

### Question 4 — 유닛 간 통신/계약 관리
유닛 간(프론트엔드 ↔ 백엔드) 인터페이스 계약을 어떻게 관리할까요?

A) **FastAPI OpenAPI 스키마를 단일 진실 원천(SSOT)** — shared의 TypeScript 타입을 이에 맞춰 정의/동기화 *(권장 — Q6=A 자동 문서화 활용)*

B) 별도 공유 스키마 문서를 수기로 관리

C) Other (please describe after [Answer]: tag below)

[Answer]:A

### Question 5 — 공통 데이터 정의(도메인 타입) 위치
매장/테이블/주문 등 도메인 타입 정의의 소유 위치는?

A) **백엔드가 소유(Pydantic 모델) + 프론트엔드 shared에 대응 TS 타입 미러링** *(권장)*

B) shared를 단일 소유처로 두고 백엔드도 이를 참조

C) 각 유닛이 독립적으로 정의(중복 허용)

D) Other (please describe after [Answer]: tag below)

[Answer]:A

---

## Part 1-B: 유닛 산출물 생성 계획 (승인 후 실행)

**질문 답변 및 승인 완료 후** 아래 산출물을 생성한다:

- [x] `application-design/unit-of-work.md` — 유닛 정의·책임 + (Greenfield) 코드 조직 전략/디렉터리 구조
- [x] `application-design/unit-of-work-dependency.md` — 유닛 의존성 매트릭스·통신 패턴·구현 순서
- [x] `application-design/unit-of-work-story-map.md` — 사용자 스토리 ↔ 유닛 매핑 (모든 스토리 배정 확인)
- [x] 유닛 경계·의존성 검증
- [x] 모든 스토리가 유닛에 배정되었는지 확인
- [x] `aidlc-state.md` 갱신 및 완료 메시지 제시

---

## Part 1-C: 잠정 분해 방향 (질문 답변으로 확정)

- **backend-api**: 인증/메뉴/주문/테이블·세션/이력 API, 계층형(Router/Service/Repository/Model), 보안 미들웨어, SQLite, 시드 데이터
- **customer-web**: 자동 로그인, 메뉴/장바구니/주문/현재 세션 내역 (고객 스토리 C1~C5)
- **admin-web**: 로그인, 대시보드/폴링, 상태변경/삭제, 테이블·세션 관리, 과거 내역 (관리자 스토리 A1~A3)
- **shared** (지원 라이브러리): ApiClient, Types, UiKit, PricingUtil, PollingHook
