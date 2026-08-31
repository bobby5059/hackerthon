# Repository Layer Summary — backend-api

> AI-DLC CONSTRUCTION / Unit 1 (backend-api) / Code Generation / Step 8 산출물 요약
> 근거: domain-entities.md, business-rules.md, nfr-design(logical-components), Security Baseline

## 1. 위치·책임

리포지토리 계층은 SQLAlchemy 2.0(sync) ORM으로 DB 접근을 캡슐화한다. **모든 쿼리는 ORM/파라미터 바인딩**으로만 수행하여 문자열 SQL 삽입을 배제한다(SECURITY-05). 트랜잭션 경계는 상위 서비스 계층이 소유하며, 리포지토리는 세션을 인자로 받아 순수 데이터 연산만 수행한다.

| 파일 | 책임 | 소유 엔티티 |
|---|---|---|
| `store_repo.py` | 매장/관리자 조회 | Store, AdminUser |
| `table_repo.py` | 테이블 upsert, 세션 CRUD, 활성 세션 조회, 테이블 목록 | Table, TableSession |
| `menu_repo.py` | 카테고리·메뉴 조회 | Category, Menu |
| `order_repo.py` | 주문+아이템 삽입, 채번(MAX+1), 상태 변경, soft-delete, 세션별 목록, 총액 합계, 최근 주문, 상태별 카운트 | Order, OrderItem |
| `history_repo.py` | 이력 이관(주문+아이템), 필터 조회(페이지네이션) | OrderHistory, OrderHistoryItem |
| `audit_repo.py` | 감사 로그 기록 헬퍼(actor/action/target/before/after/request_id) | AuditLog |
| `ids.py` | 엔티티 ID 생성(접두사 규칙) | — |

## 2. 핵심 연산 상세

### 2.1 채번 (order_repo)
- `max_order_seq(session, store_id, order_date)` → 해당 매장·영업일의 최대 `order_seq`를 트랜잭션 내에서 조회.
- 서비스가 `MAX+1`로 채번 후 삽입. `UNIQUE(store_id, order_date, order_seq)` 제약이 최종 방어선 — 경합 시 IntegrityError → 상위 retry.
- 영업일(`order_date`)은 Asia/Seoul 기준 `YYYYMMDD`.

### 2.2 총액 재계산 (order_repo)
- `sum_table_total(session, session_id)` → soft-delete되지 않은(`deleted_at IS NULL`) 주문의 `total_amount` 합계.
- 주문 삭제 시 서비스가 재호출하여 테이블 총액을 재계산(스냅샷 기반, 정수 KRW).

### 2.3 Soft-delete (order_repo)
- `soft_delete(session, order, actor)` → `deleted_at`/`deleted_by` 설정(Q3=B). 물리 삭제 없음.
- 모든 목록/집계 쿼리는 `deleted_at IS NULL` 필터를 강제하여 삭제분을 은닉.

### 2.4 활성 세션 (table_repo)
- `get_active_session(session, table_id)` → `status='ACTIVE'` 세션 조회. 재-setup(Q5=C)·주문 컨텍스트 판정에 사용.
- `end_session` → 세션 상태 종료 전이.

## 3. 인덱스·제약 활용
- `Order`: `(store_id, order_date, order_seq)` UNIQUE, `(session_id, deleted_at)` 등 조회 인덱스, status CHECK.
- `TableSession`: `(store_id, table_id, status)` 인덱스로 활성 세션 조회 최적화.
- `AdminUser`: `(store_id, username)` UNIQUE.
- 스냅샷 컬럼(OrderItem.name/unit_price/line_amount)은 메뉴 변경과 독립 — menu_id에 FK 미설정(이력 보존).

## 4. IDOR 방어 (SECURITY-08)
- 조회 계열은 `store_id` 스코프를 항상 인자로 받아 WHERE에 포함. 타 매장 리소스는 결과에서 제외 → 상위에서 404 은닉.
- 단건 조회 후 서비스가 principal의 store_id와 대조하여 불일치 시 NotFound(404).

## 5. 준수 요약
- SECURITY-05 파라미터화 쿼리: **준수**(ORM 전용, raw SQL 없음)
- BR-AUD-01 감사 로깅: audit_repo 헬퍼로 상태변경/삭제/세션종료 기록
- 트랜잭션: 리포지토리는 begin 소유 안 함 — 서비스 계층 단일 tx 경계
