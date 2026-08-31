# Functional Design Plan — backend-api

> CONSTRUCTION Phase / Unit 1 (backend-api) / Functional Design
> 목적: backend-api의 **상세 비즈니스 로직·도메인 모델·비즈니스 규칙**을 기술 중립적으로 확정한다.
> 기준 문서: `integration-contract.md`(v1.0, 계약 SSOT), `unit-of-work.md`, `services.md`, `component-methods.md`, `requirements.md`, `stories.md`.
> 활성 확장: **Security Baseline(Enabled)**, **Property-Based Testing(Partial — 순수함수/직렬화 라운드트립)**.

---

## 1. 실행 체크리스트 (Functional Design Steps)

- [ ] 유닛 컨텍스트 분석 (완료: unit-of-work / story-map / services / component-methods / integration-contract 로드)
- [ ] 본 계획 + 명확화 질문 작성 (진행 중 — 본 파일)
- [ ] 사용자 답변 수집 및 모호성 분석 (필요 시 follow-up 질문 파일 생성)
- [ ] `functional-design/domain-entities.md` 생성 — 엔티티, 속성, 관계, SQLite 스키마 매핑, 스냅샷 규칙
- [ ] `functional-design/business-logic-model.md` 생성 — 서비스별 알고리즘/오케스트레이션 상세(주문 생성, 대시보드 집계, 이용 완료 트랜잭션, 채번, 인증/토큰 발급·검증)
- [ ] `functional-design/business-rules.md` 생성 — 검증 규칙, 상태 전이, 인가/IDOR, 총액 재검증, 에러 매핑, 감사 규칙(SECURITY 매핑 포함)
- [ ] Security Baseline 적용성 평가 및 준수 요약 작성
- [ ] 완료 메시지 제시 및 승인 대기

> 참고: backend-api는 UI가 없는 API 서비스이므로 `frontend-components.md`는 **N/A**(생성하지 않음).

---

## 2. 이번 단계에서 확정할 범위 (초안)

- **도메인 엔티티**: Store, AdminUser, Table, TableSession, Category, Menu, Order, OrderItem, OrderHistory (+ 채번/감사 관련 보조 구조)
- **핵심 로직**: 주문 생성(서버측 총액 재검증), 주문번호 채번, 세션 라이프사이클, 대시보드 집계, 이용 완료(원자적 트랜잭션), 인증/JWT 발급·검증, 로그인 시도 제한
- **비즈니스 규칙**: 상태 전이, 멀티테넌시 스코프, IDOR 방지, 입력 검증 상한, 스냅샷 일관성, fail-closed 에러 처리, 감사 로깅
- **계약 정합성**: 위 모든 산출물은 `integration-contract.md`의 엔드포인트/모델/에러/토큰/폴링 규약과 일치해야 함(불일치 시 §9 변경 절차)

---

## 3. 명확화 질문 (Clarification Questions)

아래 질문에 각 `[Answer]:` 태그 뒤에 **선택지 문자(A/B/C…)** 를 채워 주세요. 보기와 다르면 마지막 `Other`를 고르고 뒤에 설명을 적어 주세요. 다 마치면 알려 주시면 답변을 반영해 산출물을 생성합니다.

### Question 1 — 주문 상태 전이 규칙
`integration-contract.md` §5.3는 역방향 전이 허용 여부를 Functional Design에서 확정하도록 남겨 두었습니다. 주문 상태(대기중 PENDING → 준비중 PREPARING → 완료 COMPLETED) 전이 규칙은?

A) 단방향만 허용 — 역방향(예: COMPLETED→PENDING) 금지, 순서 건너뛰기 불가

B) 관리자 자유 전이 — 매장 범위 내에서 임의 상태로 변경 가능(MVP 단순화)

C) 역방향 1단계까지만 허용 — 실수 정정 목적(예: PREPARING→PENDING 가능, COMPLETED에서 되돌리기까지 허용)

X) Other (please describe after [Answer]: tag below)

[Answer]: 

### Question 2 — 이용 완료 시 미완료 주문 처리
`POST /api/tables/{id}/complete`(A3-S3) 시점에 아직 PENDING/PREPARING 상태인 주문이 남아 있을 수 있습니다. 이 주문들의 처리 방식은?

A) 상태와 무관하게 전부 OrderHistory로 이동(현장에서 처리 완료로 간주)

B) 미완료 주문이 있으면 완료를 차단하고 409/경고 반환(먼저 상태 정리 요구)

C) 미완료 주문을 자동으로 COMPLETED 처리한 뒤 이력으로 이동

X) Other (please describe after [Answer]: tag below)

[Answer]: 

### Question 3 — 주문 삭제 방식 및 감사 레코드
`DELETE /api/orders/{id}`(A3-S2, 감사 로깅 SECURITY-13) 의 삭제 방식은?

A) Hard delete + 별도 감사 기록(전용 audit 로그/테이블에 누가·언제·무엇·before 값 보존)

B) Soft delete(`deleted_at`/`deleted_by` 플래그) — 대시보드·총액 집계에서 제외하되 레코드는 보존

X) Other (please describe after [Answer]: tag below)

[Answer]: 

### Question 4 — 테이블 비밀번호 정책 (SECURITY-12 예외 여부)
SECURITY-12는 비밀번호 최소 8자를 요구하지만, 테이블 자동 로그인 비밀번호(`table_password`)는 태블릿 현장 편의상 짧은 PIN이 자연스럽습니다. 정책은?

A) 테이블 비번은 4~6자리 숫자 PIN 허용(현장 편의) + 관리자 비번만 8자↑ 정책 적용 — 예외를 설계 문서에 명시

B) 테이블 비번도 8자 이상 강제(SECURITY-12 일괄 적용)

X) Other (please describe after [Answer]: tag below)

[Answer]: 

### Question 5 — 활성 세션이 있는 테이블에 재-setup 호출 시
`POST /api/tables/{id}/setup`(A3-S1) 을 이미 활성 세션이 있는 테이블에 다시 호출하면?

A) 기존 세션 종료(이력 이동) 후 새 세션 시작 — 강제 리셋

B) 기존 세션은 유지하고 테이블 번호/비밀번호 등 설정만 갱신

C) 활성 세션이 있으면 거부(409) — 먼저 이용 완료를 요구

X) Other (please describe after [Answer]: tag below)

[Answer]: 

### Question 6 — 주문번호 순번(NNN) 채번 방식
`{store_id}-{YYYYMMDD}-{NNN}`(§6)의 일자별 순번을 채번하는 방식은? (SQLite, 동시성 고려)

A) 삽입 트랜잭션 내에서 매장·일자 기준 기존 최대 순번 조회 후 +1 (트랜잭션 락으로 직렬화)

B) 전용 시퀀스 테이블(store_id, date, last_seq)을 원자적으로 증가

X) Other (please describe after [Answer]: tag below)

[Answer]: 

### Question 7 — 테이블 세션 만료(16h) 도달 시 동작
테이블 세션 TTL(≤16h) 만료 후 해당 테이블에서 요청이 오면?

A) 서버가 요청마다 세션 만료 검사 → 만료 시 401 `TOKEN_EXPIRED` 반환, 관리자 재설정(재-setup) 필요

B) 만료 시 서버가 자동으로 새 세션을 시작해 계속 사용(관리자 개입 불필요)

X) Other (please describe after [Answer]: tag below)

[Answer]: 

### Question 8 — 시드 데이터 범위 (MVP/데모)
초기 시드 데이터(단일 매장 전제, Q-inception)의 규모는?

A) 매장 1 + 관리자 1 + 테이블 10 + 카테고리 3~4 + 메뉴 15~20 (데모에 충분한 볼륨)

B) 최소 세트 — 매장 1 + 관리자 1 + 테이블 2~3 + 메뉴 5 (스모크 테스트용)

X) Other (please describe after [Answer]: tag below — 구체 수치 명시)

[Answer]: 

### Question 9 — 대시보드 신규 주문 강조(`has_new`) 계산 주체
`TableCard.has_new`(신규 주문 강조)를 누가 계산하나요?

A) 서버는 계산하지 않음 — 클라이언트가 `server_time`/`created_at` 비교로 판단(계약 §5.1 정신에 부합, 서버는 `has_new` 생략 또는 항상 false)

B) 서버가 직전 폴링 이후 신규 주문 여부를 계산해 `has_new`를 세팅(서버가 마지막 조회 시각 추적 필요)

X) Other (please describe after [Answer]: tag below)

[Answer]: 

### Question 10 — 메뉴 가용성(품절) 개념 포함 여부
메뉴에 품절/비활성 개념을 MVP에 포함하나요?

A) 포함하지 않음 — 모든 메뉴는 항상 주문 가능(MVP 범위 밖)

B) 포함 — `Menu.is_available` 토글, 품절 메뉴 주문 시 422/거부

X) Other (please describe after [Answer]: tag below)

[Answer]: 

### Question 11 — 입력 검증 상한 기본값 (SECURITY-05)
주문 생성 등의 입력 상한(길이/크기 경계)은?

A) 합리적 기본값 설정 — 주문당 최대 항목 수(예: 50), 항목당 수량 상한(예: 99), 문자열 필드 max length, 요청 본문 크기 제한

B) 타입 검증만 수행하고 별도 수치 상한은 두지 않음

X) Other (please describe after [Answer]: tag below — 원하는 상한 값 명시)

[Answer]: 
