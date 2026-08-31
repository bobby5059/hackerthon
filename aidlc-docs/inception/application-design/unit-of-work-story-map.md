# Unit of Work ↔ Story Map — 테이블오더 서비스

> 사용자 스토리를 유닛에 매핑. 프론트엔드 스토리는 대응하는 backend-api 서버측 기능을 함께 필요로 하므로, "주 유닛(UI)"과 "backend-api 지원"을 함께 표기한다.

---

## 1. 고객 스토리 (customer-web + backend-api)

| 스토리 | 우선순위 | 주 유닛 | backend-api 지원 |
|---|---|---|---|
| C1-S1 태블릿 자동 로그인 | Must | customer-web | `POST /api/table/login`, JWT 발급, 세션 검증 |
| C1-S2 현재 세션 컨텍스트 유지 | Must | customer-web | 세션 스코프 처리, 신규 세션 시작 |
| C2-S1 카테고리별 메뉴 조회 | Must | customer-web | `GET /api/menu` |
| C2-S2 메뉴 상세 확인 | Should | customer-web | `GET /api/menu/{id}` |
| C2-S3 터치 친화적 UI | Should | customer-web (shared UiKit) | — |
| C3-S1 장바구니 담기/수량 | Must | customer-web (shared PricingUtil) | — (클라이언트 로컬) |
| C3-S2 장바구니 로컬 유지 | Must | customer-web | — (localStorage) |
| C3-S3 장바구니 비우기 | Should | customer-web | — |
| C4-S1 주문 확정 | Must | customer-web | `POST /api/orders` (총액 재검증) |
| C4-S2 주문 성공 플로우 | Must | customer-web | 주문번호 반환 |
| C4-S3 주문 실패 처리 | Must | customer-web | fail closed 응답 |
| C4-S4 주문 수정/취소 불가 | Won't | (설계상 미제공) | 고객 수정 엔드포인트 없음 |
| C5-S1 현재 세션 주문 내역 | Must | customer-web | `GET /api/orders` (세션 스코프) |
| C5-S2 주문 상태 준실시간 갱신 | Should | customer-web | 폴링 응답(상태 포함) |

## 2. 관리자 스토리 (admin-web + backend-api)

| 스토리 | 우선순위 | 주 유닛 | backend-api 지원 |
|---|---|---|---|
| A1-S1 매장 로그인 | Must | admin-web | `POST /api/admin/login`, bcrypt 검증, JWT |
| A1-S2 16시간 세션/자동 로그아웃 | Must | admin-web | JWT 만료·서버측 검증 |
| A1-S3 로그인 시도 제한 | Should | admin-web | RateLimiter, 보안 이벤트 로깅 |
| A2-S1 테이블별 그리드 대시보드 | Must | admin-web | `GET /api/tables/dashboard` (집계) |
| A2-S2 폴링 기반 준실시간 갱신 | Must | admin-web (shared PollingHook) | 대시보드 폴링 응답 |
| A2-S3 주문 상세 보기 | Should | admin-web | 주문 상세 조회 |
| A2-S4 주문 상태 변경 | Must | admin-web | `PATCH /api/orders/{id}/status` |
| A2-S5 테이블별 필터링 | Could | admin-web | dashboard `table_filter` 파라미터 |
| A3-S1 테이블 태블릿 초기 설정 | Must | admin-web | `POST /api/tables/{id}/setup`, 세션 생성 |
| A3-S2 주문 삭제(직권) | Must | admin-web | `DELETE /api/orders/{id}`, 총액 재계산, 감사 로깅 |
| A3-S3 이용 완료(세션 종료) | Must | admin-web | `POST /api/tables/{id}/complete`, 이력 이동·리셋 |
| A3-S4 과거 주문 내역 조회 | Should | admin-web | `GET /api/history` (날짜 필터) |

## 3. shared 유닛 기여 스토리 (독립 유닛)

| shared 컴포넌트 | 관련 스토리 |
|---|---|
| PricingUtil (금액 계산, PBT NFR-T-01) | C3-S1, C4-S1 |
| UiKit (터치 버튼 ≥44x44px) | C2-S3, 전 UI 스토리 |
| PollingHook (~2초) | C5-S2, A2-S2 |
| ApiClient / Types | 모든 서버 통신 스토리 |

> shared는 위 컴포넌트를 통해 여러 스토리를 **횡단 지원**한다. 스토리의 "주 유닛"은 UI를 소유한 customer-web/admin-web이며, shared는 이들이 소비하는 공통 기능을 제공한다.

---

## 4. 배정 완전성 확인

- **고객 스토리 14개** (C4-S4 Won't 포함) → 전부 customer-web(+backend-api, +shared) 배정 ✔
- **관리자 스토리 12개** → 전부 admin-web(+backend-api, +shared) 배정 ✔
- **미배정 스토리 없음.** 모든 서버측 기능은 backend-api에, 프론트엔드 공통 기능은 shared에 집약.

## 5. 유닛별 스토리 카운트 요약 (4개 유닛)

| 유닛 | 주 담당 스토리 수 | 비고 |
|---|---|---|
| backend-api | (전 스토리 서버측 지원) | 계약·로직·보안 |
| shared | (횡단 지원) | 프론트엔드 공통 컴포넌트/유틸 — 독립 유닛 |
| customer-web | 14 (C1~C5) | Won't 1건 포함 |
| admin-web | 12 (A1~A3) | — |
