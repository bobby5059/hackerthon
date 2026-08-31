# Functional Design — Business Rules & Constraints — Unit `shared`

> `shared`가 강제/보장하는 **규칙**을 모은다. 도메인 규칙은 backend-api 소유이므로, 여기서는 shared가 책임지는 **계산·통신·표시·보안** 규칙에 한정한다.
> 근거: 계약(`integration-contract.md`), 요구사항 NFR, 확장(Security Baseline, PBT Partial).

---

## 1. 금액 규칙 (PricingUtil)

| ID | 규칙 | 근거 |
|---|---|---|
| BR-P-01 | 모든 금액은 **정수 KRW**. 부동소수 연산·반올림 금지 | 계약 §3.3 |
| BR-P-02 | `lineTotal = unit_price × quantity`, `cartTotal = Σ lineTotal` | 계약 §3.3 |
| BR-P-03 | `unit_price`,`quantity`는 정수 & ≥0. 위반 시 `RangeError` (fail-fast) | Q7=A |
| BR-P-04 | 빈 장바구니의 `cartTotal = 0` | Q7=A |
| BR-P-05 | PricingUtil 결과는 **표시용**. 주문/결제의 정답은 서버 `total_amount` | 계약 §3.3 |
| BR-P-06 | 클라이언트 총액과 서버 총액 불일치 시, 서버 응답(422 `TOTAL_MISMATCH`)을 신뢰하고 사용자에게 재확인 유도 | 계약 §2.3 |

**PBT 속성(P1~P6)**: `business-logic-model.md` §1.4 참조 (NFR-T-01, PBT Partial 적용 대상).

---

## 2. 통신·에러 규칙 (ApiClient)

| ID | 규칙 | 근거 |
|---|---|---|
| BR-A-01 | Base URL `/api`, JSON, UTF-8, `Content-Type: application/json` | 계약 §1.1 |
| BR-A-02 | 보호 엔드포인트는 `Authorization: Bearer <token>` 자동 첨부(토큰 존재 시) | 계약 §1.2, Q3=A |
| BR-A-03 | 모든 4xx/5xx는 정규화된 `ApiError`로 변환하여 throw | Q4=A, 계약 §1.3 |
| BR-A-04 | 네트워크/파싱/timeout 실패는 `ApiError(code:"NETWORK_ERROR", httpStatus:0)` | Q4=A |
| BR-A-05 | 401 또는 `TOKEN_EXPIRED` 수신 시 `onUnauthorized` 콜백 호출 후 throw (fail closed) | 계약 §1.3, SECURITY-08 |
| BR-A-06 | 목록 조회는 `?page&size`(1-base, size 1..100, 기본 20) 쿼리 규약 준수 | 계약 §1.4 |
| BR-A-07 | store_id/table/session은 요청 바디로 보내지 않는다(토큰에서 서버가 도출) | 계약 §2.3 |

---

## 3. 보안 규칙 (Security Baseline — 계약 §8)

| ID | 규칙 | 매핑 |
|---|---|---|
| BR-S-01 | 토큰·비밀번호를 로그/에러 메시지에 노출 금지. 로깅 시 `Authorization`·`password` 마스킹 | SECURITY-03 |
| BR-S-02 | shared는 자격증명을 저장하지 않는다. 토큰 저장/만료 관리는 소비 앱(localStorage) 책임 | SECURITY-08, 계약 §4.2 |
| BR-S-03 | 서버가 준 일반화 오류 메시지만 표시. 내부 상세 추론/노출 금지 | SECURITY-15, 계약 §1.3 |
| BR-S-04 | 자동 생성 타입 스냅샷(`openapi.json`)은 신뢰된 backend 산출물만 사용, 버전 고정(lock) | SECURITY-10 |
| BR-S-05 | UiKit이 렌더하는 문자열(메뉴명·설명 등)은 React 기본 이스케이프에 의존, `dangerouslySetInnerHTML` 금지(XSS 방지) | SECURITY-04 파생 |

> N/A(이 유닛): 암호화 at-rest/TLS(SECURITY-01), IAM(06), 네트워크(07) — 인프라/백엔드 사안, shared 무관.

---

## 4. 폴링 규칙 (PollingHook — 계약 §5)

| ID | 규칙 | 근거 |
|---|---|---|
| BR-PL-01 | 기본 폴링 주기 **2000ms**(NFR-P-01 "2초 이내") | 계약 §5.1 |
| BR-PL-02 | 탭 비활성 시 일시정지, 재활성 시 즉시 1회 fetch 후 재개 | Q5=A |
| BR-PL-03 | 폴링 실패는 **조용히 다음 주기 재시도**, 데이터 유지, UI 미파손 | 계약 §5.1, Q5=A |
| BR-PL-04 | 언마운트/비활성 시 인터벌 정리 + 진행 요청 abort(누수 방지) | Q5=A |
| BR-PL-05 | 응답 `server_time`을 `lastServerTime`으로 노출. 신규 판단은 소비 컴포넌트 | Q6=A, 계약 §5.1 |
| BR-PL-06 | 폴링은 최종 일관성. 서버 최신 스냅샷이 정답 | 계약 §5.2 |

---

## 5. 표시·UX 규칙 (UiKit / Types)

| ID | 규칙 | 근거 |
|---|---|---|
| BR-U-01 | 터치 대상 최소 **44×44px** | NFR-U-02 |
| BR-U-02 | 한국어 UI(MVP). `OrderStatus` 표시 라벨: PENDING=대기중, PREPARING=준비중, COMPLETED=완료 | 계약 §3.1, NFR-U-03 |
| BR-U-03 | 타임스탬프 표시는 **Asia/Seoul**. shared는 ISO8601(+09:00) 문자열을 파싱·포맷하되 타임존 변환하지 않음 | NFR-D-03, 계약 §1.1 |
| BR-U-04 | 금액 표시는 정수 KRW 천단위 구분 포맷(예: `23,000원`) — 순수 포맷 함수, 계산과 분리 | NFR-U-01 |
| BR-U-05 | 인터랙티브 요소에 안정적 `data-testid` 부여(자동화 친화) | code-generation.md 규칙 |

---

## 6. 에지 케이스

| 케이스 | shared 동작 |
|---|---|
| 서버가 계약과 다른 필드 반환 | 생성 타입 기준; 누락 필드는 런타임 방어(옵셔널 체이닝) 후 소비 앱에 위임. 상충은 계약 §9로 에스컬레이션 |
| `total_amount` 없이 items만 존재 | PricingUtil로 표시용 재계산 가능하나, 서버값 우선(BR-P-05) |
| 폴링 중 토큰 만료(401) | ApiClient가 `onUnauthorized` 호출 → 소비 앱이 폴링 `enabled=false` + 재로그인/재설정 유도 |
| 빈 대시보드/빈 내역 | 빈 배열 정상 처리(에러 아님), UiKit 빈 상태 표시 |
| 수량 0 항목 | `lineTotal=0` 정상, cartTotal 불변(BR-P-03/04) |

---

## 7. 스토리 추적
- BR-P-* → C3-S1, C4-S1 / BR-A-*·BR-S-* → 전 서버통신 스토리 / BR-PL-* → C5-S2, A2-S2 / BR-U-* → C2-S3 및 전 UI 스토리
