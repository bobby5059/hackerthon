# Business Logic Summary — backend-api

> AI-DLC CONSTRUCTION / Unit 1 (backend-api) / Code Generation / Step 9 산출물 요약
> 근거: business-logic-model.md, business-rules.md, 클래리피케이션 Q1~Q10, FD §2~§6

## 1. 서비스 계층 개요

서비스 계층이 **트랜잭션 경계**와 비즈니스 규칙을 소유한다. 각 상태 변경 유스케이스는 단일 트랜잭션(`with db.begin()`)으로 원자적으로 수행되며, 실패 시 fail-closed(롤백 + 표준 에러).

| 파일 | 유스케이스 | 핵심 규칙 |
|---|---|---|
| `auth_service.py` | 관리자/테이블 인증 | RateLimiter → bcrypt 검증 → LoginAttempt 기록 → JWT 발급, 일반화 401 |
| `menu_service.py` | 메뉴 목록/상세 | store 스코프 조회, 가용성 필드 없음(Q10=A) |
| `order_service.py` | 주문 생성/목록/상태변경/삭제 | 채번·스냅샷·총액 재검증·자유 전이·soft-delete |
| `session_service.py` | setup / get_or_start / dashboard / complete | 재-setup 409·만료 검사·집계·완료 차단 |
| `history_service.py` | 세션 아카이브 / 이력 조회 | 주문+아이템 이관, 페이지네이션 |
| `pricing.py` / `order_number.py` | 순수 계산 함수(PBT 대상) | line/total 계산, 채번 포맷 |

## 2. 주문 생성 (order_service.create_order) — FD §4

`@retry_on_write_conflict` + 단일 트랜잭션:
1. `get_or_start_session` 호출(호출자 tx 내부 실행, 자체 begin 없음) — 활성 세션 확보 또는 신규 생성.
2. 각 아이템의 메뉴를 store 스코프로 조회 → 미존재 시 `VALIDATION_ERROR`(422).
3. **스냅샷 가격 고정**: 조회 시점의 `name`/`unit_price`를 OrderItem에 복사, `line_amount = unit_price * quantity`(순수 함수 `pricing`).
4. **채번**: `max_order_seq + 1`, `order_number = {store_id}-{YYYYMMDD}-{NNN}`(Asia/Seoul).
5. **서버 총액 재계산**: `total_amount = Σ line_amount` — 클라이언트 값 신뢰 안 함.
6. UNIQUE 충돌 시 retry(최대 3회, 10/20/40ms), 소진 시 fail-closed 500.

## 3. 주문 상태·삭제 — Q1=B, Q3=B, A2-S4/A3-S2

- **상태 변경**: PENDING↔COMPLETED 자유 전이(Q1=B, 순서·역방향 제약 없음). 잘못된 enum 값은 스키마 검증 400. 변경 시 감사 로그.
- **삭제**: soft-delete(Q3=B, `deleted_at`/`deleted_by`). 삭제 후 테이블 총액 재계산, 목록에서 은닉, 감사 로그.

## 4. 세션 라이프사이클 (session_service) — FD §5

- **setup_table** (A3-S1, Q5=C): 활성 세션이 있는 테이블 재-setup 시도 → `SESSION_CLOSED`(409). PIN 4~6 숫자 검증(Q4=A, BR-VAL-03). `@retry_on_write_conflict`.
- **get_or_start_session** (C1-S2, Q7=A): 요청 시점 만료 검사(auto-renew 없음). 만료/부재 시 신규 세션 생성. 호출자 트랜잭션 내부에서 동작.
- **get_dashboard** (A2-S1/S2/S5): 테이블 카드 집계(총액·최근 주문). `has_new`는 항상 `false`이되 **항상 포함**(Q9=A). `server_time` 포함(폴링용).
- **complete_session** (A3-S3, Q2=B): 미완료(PENDING) 주문 존재 시 완료 차단 → `SESSION_CLOSED`(409). 전부 COMPLETED면 history_service로 이력 이관 후 세션 종료·테이블 리셋(총액 0). 단일 tx.

## 5. 인증 (auth_service) — FD §2, SECURITY-12

1. RateLimiter 확인 → 잠금 시 `RATE_LIMITED`(429) + 쿨다운.
2. 사용자/테이블 조회 → bcrypt 검증. **존재 여부·비밀번호 오류를 동일한 401로 일반화**(사용자 열거 방지).
3. LoginAttempt 기록(성공/실패).
4. 성공 시 JWT 발급: `typ`(A/T), `store_id`, exp(관리자 16h), iss. 테이블 토큰은 table_id/session_id 포함.

## 6. 순수 함수 (PBT 대상, NFR-T-01)
- `pricing.line_amount(unit_price, qty)` / `total_amount(items)` — 비음수, 순서 무관 합.
- `order_number.format/parse` — `{store}-{YYYYMMDD}-{NNN}` 라운드트립.

## 7. 준수 요약
- Q1~Q10 설계 결정 전부 코드 반영.
- 총액·채번은 서버 권위(클라이언트 미신뢰), fail-closed 트랜잭션.
- 감사 로깅(BR-AUD): 상태변경·삭제·세션 종료·로그인 시도.
