# Story Generation Plan — 테이블오더 서비스

**Role**: Product Owner
**Purpose**: 요구사항(`requirements.md`)을 사용자 중심 스토리 + 인수 조건으로 변환하기 위한 계획

---

## Part A: Planning Questions (사용자 입력 필요)

> 아래 [Answer]: 태그를 채워 주세요. (인터랙티브로 한 문항씩 여쭤본 뒤, 답변을 이 문서에 기록합니다.)

### Question 1: 스토리 분해 방식 (Breakdown Approach)
스토리를 어떤 기준으로 조직할까요?

A) User Journey-Based — 사용자 워크플로우/여정 흐름을 따라 스토리 구성

B) Feature-Based — 시스템 기능/역량 단위로 스토리 구성

C) Persona-Based — 페르소나(고객/관리자)별로 그룹화

D) Epic-Based (Hybrid) — 페르소나별 에픽 아래 기능 스토리를 계층적으로 구성 (권장)

E) Other (please describe after [Answer]: tag below)

[Answer]: D (Epic-Based / Hybrid — 페르소나별 에픽 아래 기능 스토리 계층 구성)

### Question 2: 페르소나 구성 (Personas)
어떤 페르소나를 정의할까요?

A) 고객(Customer) + 관리자(Admin) 2개 (권장)

B) 고객 + 매장 운영자(사장) + 매장 직원(홀 스태프) 3개로 세분화

C) Other (please describe after [Answer]: tag below)

[Answer]: A (고객 + 관리자 2개 페르소나)

### Question 3: 인수 조건 형식 (Acceptance Criteria Format)
각 스토리의 인수 조건을 어떤 형식으로 작성할까요?

A) Given/When/Then (Gherkin 스타일) — 테스트 자동화/BDD에 유리 (권장)

B) 불릿 체크리스트 형태의 조건 목록

C) Other (please describe after [Answer]: tag below)

[Answer]: A (Given/When/Then, Gherkin 스타일)

### Question 4: 스토리 세분화 수준 (Granularity)
스토리 크기를 어느 수준으로 할까요?

A) 세분화(fine-grained) — 작은 단위로 나눠 각 기능을 독립적으로 (권장, INVEST의 Small)

B) 굵은 단위(coarse) — 기능 묶음 단위의 큰 스토리

C) Other (please describe after [Answer]: tag below)

[Answer]: A (fine-grained — 작은 단위, INVEST Small)

### Question 5: 우선순위 표기 (Prioritization)
스토리에 MVP 우선순위를 표기할까요?

A) 예 — MoSCoW(Must/Should/Could/Won't) 또는 MVP/Post-MVP 태그 부여 (권장)

B) 아니오 — 우선순위 표기 없이 스토리만 작성

C) Other (please describe after [Answer]: tag below)

[Answer]: A (예 — MoSCoW / MVP·Post-MVP 태그 부여)

---

## Part B: Execution Checklist (승인 후 실행)

- [x] 승인된 분해 방식/형식으로 `aidlc-docs/inception/user-stories/personas.md` 생성 (페르소나 아키타입·특성·동기)
- [x] `aidlc-docs/inception/user-stories/stories.md` 생성 — INVEST 기준 준수 사용자 스토리
- [x] 각 스토리에 승인된 형식의 인수 조건 포함
- [x] 고객 스토리: 자동 로그인/세션, 메뉴 조회, 장바구니, 주문 생성, 주문 내역 조회
- [x] 관리자 스토리: 매장 인증, 준실시간 주문 모니터링, 테이블 관리(초기 설정/주문 삭제/이용 완료/과거 내역)
- [x] 세션 라이프사이클/테넌트 격리 관련 엣지 케이스 스토리 포함
- [x] 보안 관련(로그인 시도 제한, 인가) 인수 조건 반영
- [x] 페르소나 ↔ 스토리 매핑 표 작성
- [x] 스토리별 우선순위 태그 부여(선택 시)
- [x] INVEST 준수 여부 검증(Independent, Negotiable, Valuable, Estimable, Small, Testable)

---

## Notes
- 기술 구현/스프린트 계획은 이 단계에서 다루지 않음 (스토리 구조·형식에 집중)
- 스토리는 이후 Application Design / Units Generation의 입력으로 사용됨
