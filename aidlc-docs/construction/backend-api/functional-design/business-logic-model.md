# Business Logic Model — backend-api

> CONSTRUCTION / Unit 1 (backend-api) / Functional Design
> 서비스별 알고리즘·오케스트레이션·트랜잭션 경계를 기술 중립적으로 상세화한다.
> 기준: `services.md`(오케스트레이션), `component-methods.md`(시그니처), `integration-contract.md` v1.0.
> 상태/검증 규칙의 세부는 `business-rules.md` 참조. 엔티티는 `domain-entities.md` 참조.

---

## 1. 공통 실행 컨텍스트

모든 서비스 메서드는 아래 컨텍스트를 전제한다.
- **인증 컨텍스트**: SecurityMiddleware가 JWT 검증 후 `claims`(typ, store_id, table_id?, session_id?) 주입. 서비스는 `store_id`를 필수 인자로 받아 테넌트 격리(SECURITY-08, defense in depth).
- **입력 검증**: Router 계층에서 스키마 검증(타입/길이/형식/본문 크기) 선행(SECURITY-05, business-rules.md BR-VAL-*). 서비스는 검증된 입력을 신뢰하되 의미 검증(총액 등)은 별도 수행.
- **시각**: 모든 시각 생성은 Asia/Seoul(+09:00) 기준(NFR-D-03).
- **에러**: 외부 호출(DB) 실패는 명시적 처리 → 롤백 → GlobalErrorHandler가 일반화 응답(SECURITY-15). 부분 성공 금지(fail closed).

---

## 2. AuthService

### 2.1 authenticate_admin(store_id, username, password) → AdminToken
```
1. RateLimiter.check(key=ADMIN:store_id:username)
     → 잠금 상태면 즉시 429 RATE_LIMITED (자격증명 검증 안 함)
2. admin = StoreRepository.get_admin(store_id, username)
3. ok = (admin exists) AND bcrypt.verify(password, admin.password_hash)
     → 존재 여부와 무관하게 동일 경로/응답(사용자 열거 방지, 일반화 401)
4. LoginAttempt 기록(success=ok); 실패 시 RateLimiter.record_failure(key)
5. if not ok: 401 UNAUTHORIZED(일반화 메시지)
6. claims = {iss:"table-order", sub:f"admin:{username}", typ:"admin",
             store_id, username, iat, exp: iat+16h}
7. token = issue_jwt(claims, ttl=16h)
8. return AdminToken(access_token, expires_at, store={store_id, name})
```
- 비밀번호는 로그·응답 노출 금지(SECURITY-03/12). 성공/실패 보안 이벤트 로깅.

### 2.2 authenticate_table(store_id, table_no, table_password) → TableToken
```
1. RateLimiter.check(key=TABLE:store_id:table_no) → 잠금 시 429
2. table = TableRepository.get_table_by_no(store_id, table_no)
3. ok = table exists AND table.auto_login_enabled AND bcrypt.verify(table_password, table.table_password_hash)
4. LoginAttempt 기록; 실패 시 record_failure; if not ok → 401 UNAUTHORIZED
5. session = TableRepository.get_active_session(store_id, table.table_id)
     → 세션 없음/EXPIRED/COMPLETED → 401 TOKEN_EXPIRED
       (메시지: "관리자 재설정이 필요합니다" — Q7=A)
     → 만료 검사: now >= session.expires_at 이면 세션 EXPIRED 처리 후 401 TOKEN_EXPIRED
6. ttl = session.expires_at - now   # 세션 잔여(≤16h)
7. claims = {iss, sub:f"table:{table.table_id}", typ:"table",
             store_id, table_id, session_id: session.session_id, iat, exp: iat+ttl}
8. return TableToken(access_token, expires_at=session.expires_at, table, session)
```

### 2.3 issue_jwt / verify_jwt
- `issue_jwt(claims, ttl)`: HS256 서명, `iss`/`iat`/`exp` 세팅. 서명키는 환경설정(하드코딩 금지, SECURITY-12). 민감정보 미포함(§4 계약).
- `verify_jwt(token)`: 서명·`exp`·`iss` 서버측 검증(SECURITY-08). 실패 시 401(만료=TOKEN_EXPIRED, 그외=UNAUTHORIZED). typ 불일치 접근은 403(FORBIDDEN).

### 2.4 register_failed_attempt / RateLimiter
- 윈도우 내 실패 횟수 ≥ 임계값 → 잠금(지연/차단). 임계값·윈도우는 NFR Design에서 확정(기본 예: 5회/5분 → 429). 관련 보안 이벤트 로깅(SECURITY-14 지향, 로컬 MVP는 로깅으로 충족).

---

## 3. MenuService

### 3.1 list_menu(store_id) → {categories, menus}
```
1. categories = MenuRepository.list_categories(store_id)  # display_order asc
2. menus = MenuRepository.list_menus(store_id)            # is_available 포함(Q10=B)
3. return {categories, menus}   # 계약 §2.2 GET /api/menu
```
- 매장 범위 스코프. 품절 메뉴도 목록에는 포함하되 `is_available=false`로 표시(클라이언트가 담기 비활성).

### 3.2 get_menu(store_id, menu_id) → Menu | 404
- 매장 범위 조회. 없으면 404 NOT_FOUND(소유권 없어도 404로 은닉, 계약 §1.3).

---

## 4. OrderService

### 4.1 create_order(store_id, table_id, session_id, items) → Order  [C4-S1~S3]
**트랜잭션 경계: 단일 트랜잭션(채번+삽입 원자적, fail closed).**
```
1. 사전검증(business-rules.md):
     - items 비어있음 → 400 ORDER_EMPTY (BR-ORD-01)
     - 입력 상한(SECURITY-05, Q11=보안 최소 상한): items 개수 ≤ MAX_ITEMS_PER_ORDER,
       각 quantity 1..MAX_QTY_PER_ITEM, menu_id 형식 (BR-VAL-02)
2. session = TableSessionService.get_or_start_session(store_id, table_id)
     - session.status != ACTIVE 또는 만료 → 409 SESSION_CLOSED (BR-SESS-02)
     - 토큰 session_id와 실제 활성 session_id 불일치 → 409 SESSION_CLOSED
3. 단가 조회 및 스냅샷 구성:
     for each input item:
        menu = MenuRepository.get_menu(store_id, item.menu_id)
        - menu 없음 → 422 (또는 400 VALIDATION) 유효하지 않은 menu_id (BR-ORD-04)
        - menu.is_available == false → 422 (품절, BR-ORD-05)
        line_amount = menu.price * item.quantity      # 서버 단가 사용
        snapshot(name=menu.name, unit_price=menu.price, quantity, line_amount)
4. total_amount = Σ line_amount                        # 서버 재검증(클라 총액 신뢰 안 함)
     - (클라이언트가 총액을 보냈고) 불일치 → 422 TOTAL_MISMATCH (BR-ORD-03)
       * 계약상 요청 본문에 총액 없음 → 서버 계산값이 항상 정답. 방어적 검사만.
5. order_number 채번: generate_order_number(store_id, today_kst)  # §4.2, 동일 트랜잭션 내
6. OrderRepository.insert_order(order + items)          # status=PENDING
7. commit   (실패 시 rollback → 주문 미생성, SECURITY-15)
8. return Order(order_id, order_number, status=PENDING, total_amount, items, created_at)
```
- **PBT 대상(NFR-T-01)**: `total_amount = Σ(unit_price × quantity)` 및 line_amount 계산 — 순수 계산 로직(property-based-testing §Testable Properties 참조).

### 4.2 generate_order_number(store_id, date) → str  [채번 Q6=A]
**방식 A: 삽입 트랜잭션 내 max+1 (트랜잭션 락으로 직렬화).**
```
1. (create_order 트랜잭션 내에서 호출)
2. max_seq = OrderRepository.max_order_seq(store_id, order_date=date)   # 없으면 0
     # SELECT MAX(order_seq) ... WHERE store_id=? AND order_date=?  (soft-delete 포함해 순번 재사용 방지)
3. next_seq = max_seq + 1
4. order_seq=next_seq, order_number = f"{store_id}-{YYYYMMDD}-{next_seq:03d}"   # 999 초과 시 자릿수 확장
5. return order_number
```
- **동시성**: SQLite 쓰기 트랜잭션은 직렬화(write lock)되므로 동일 매장·일자 순번 충돌 방지. `(store_id, order_date, order_seq)` UNIQUE 제약으로 이중 안전장치 → 위반 시 재시도 또는 실패(fail closed).
- 삭제된 주문의 순번도 재사용하지 않음(MAX 기준, soft-delete 레코드 포함 계산).

### 4.3 list_session_orders(store_id, session_id, page, size) → {items, page_meta, server_time}  [C5-S1, 폴링]
```
1. rows = OrderRepository.list_by_session(store_id, session_id, deleted_at IS NULL)
2. 정렬: created_at 오름차순(계약 §2.3)
3. 페이지네이션(§1.4) → page_meta
4. server_time = now_kst()
5. return {items, page_meta, server_time}
```
- 현재 세션 범위만(이전 세션/이력 제외). soft-delete 주문 제외.

### 4.4 update_status(store_id, order_id, status) → Order  [A2-S4]
```
1. order = OrderRepository.get(store_id, order_id, deleted_at IS NULL)
     - 없음/타 매장 → 404(은닉) / 소유권 위반 → 403 (assert_owns_resource)
2. 상태 전이 규칙(Q1=B 자유 전이): status ∈ {PENDING,PREPARING,COMPLETED}이면
   매장 범위 내 임의 전이 허용(역방향 포함). (BR-ORD-06)
3. OrderRepository.update_status(store_id, order_id, status)
4. AuditLog(action=ORDER_STATUS_CHANGE, before=old_status, after=status, actor)  # SECURITY-13
5. return Order   # 다음 폴링 주기에 고객/대시보드 반영(계약 §5.2)
```

### 4.5 delete_order(store_id, order_id, actor) → DeleteResult  [A3-S2, soft delete Q3=B]
**트랜잭션 경계: 삭제 + 총액 재계산 + 감사 기록 단일 트랜잭션.**
```
1. order = OrderRepository.get(store_id, order_id, deleted_at IS NULL)
     - 없음 → 404 / 소유권 위반 → 403
2. OrderRepository.soft_delete(store_id, order_id, deleted_at=now, deleted_by=actor)  # Q3=B
3. table_total = recalculate_table_total(store_id, order.table_id)  # deleted 제외
4. AuditLog(action=ORDER_DELETE, target=Order:order_id, before=order 스냅샷, actor, request_id)  # SECURITY-13
5. commit (실패 시 rollback)
6. return DeleteResult{deleted_order_id, table_id, table_total_amount=table_total}
```
- 폴링 목록/대시보드에서 즉시 사라짐 + 총액 변동(계약 §5.2 order.deleted).

### 4.6 recalculate_table_total(store_id, table_id) → int
```
return OrderRepository.sum_table_total(store_id, table_id)
       # 현재 활성 세션의 deleted_at IS NULL 주문 Σ total_amount
```
- 반환은 정수 KRW(계약 §1.1). component-methods.md의 Decimal 표기는 정수 KRW로 확정.

---

## 5. TableSessionService

### 5.1 setup_table(store_id, table_no, password) → Table+Session  [A3-S1]
**트랜잭션 경계: 테이블 upsert + 세션 생성 단일 트랜잭션.**
```
1. 입력 검증: table_no(1~20자), password = 4~6자리 숫자 PIN(Q4=A, BR-VAL-03)
2. active = TableRepository.get_active_session(store_id, by table_no)
     - 활성 세션 존재 → 409 (Q5=C, BR-SESS-03: 먼저 이용 완료 요구)  ← 재-setup 거부
3. table = TableRepository.upsert_table(store_id, table_no,
              table_password_hash=bcrypt(password), auto_login_enabled=true)
4. session = TableRepository.create_session(store_id, table.table_id,
              status=ACTIVE, started_at=now, expires_at=now+16h)
5. AuditLog(action=TABLE_SETUP, target=Table, actor)  # SECURITY-13
6. commit
7. return {table_id, table_no, auto_login_enabled:true, session{session_id, started_at, expires_at}}
```

### 5.2 get_or_start_session(store_id, table_id) → TableSession
```
1. session = TableRepository.get_active_session(store_id, table_id)
2. if session exists:
     - if now >= session.expires_at → status=EXPIRED 처리, 세션 없음으로 취급(Q7=A)
     - else return session (ACTIVE)
3. if no active session:
     - 주문 흐름(create_order)에서 호출된 경우: 첫 주문 → 새 ACTIVE 세션 시작
       (started_at=now, expires_at=now+16h). 단, 토큰 session_id가 지정돼 있고
       그 세션이 EXPIRED/COMPLETED면 새 세션 시작하지 않고 409 SESSION_CLOSED
       (토큰-세션 불일치 방지, BR-SESS-02).
```
- **주의(Q7=A)**: 만료된 세션은 자동 연장/자동 재시작하지 않는다. 테이블 토큰은 특정 session_id에 묶여 있으므로, 만료 후 재사용은 401 TOKEN_EXPIRED → 관리자 재-setup 필요.

### 5.3 get_dashboard(store_id, table_filter=None) → {tables, server_time}  [A2-S1/S2/S5, 폴링]
```
1. tables = TableRepository.list_tables(store_id) [table_filter 적용 시 해당 테이블만]
2. for each table with ACTIVE session:
     total = OrderRepository.sum_table_total(store_id, table_id)   # deleted 제외
     recent = OrderRepository.recent_orders(store_id, session_id, limit=3, deleted 제외)
              → OrderPreview[] (order_number, created_at, item_summary, total_amount)
     card = TableCard{table_id, table_no, total_amount:total, recent_orders:recent,
                      has_new:false}   # Q9=A: 서버 미계산(클라가 server_time/created_at 비교)
3. server_time = now_kst()
4. return {tables:[TableCard], server_time}
```
- `item_summary` 축약 규칙: 대표 메뉴명 + 외 N건(예: "김치찌개 외 2건") — business-rules.md BR-DASH-01.
- **has_new(Q9=A)**: 서버는 계산하지 않음(항상 false 또는 생략). 클라이언트가 `created_at > 직전 폴링 server_time`으로 신규 판단(계약 §5.1).

### 5.4 complete_session(store_id, table_id) → CompleteResult  [A3-S3]
**트랜잭션 경계: 이력 이관 + 세션 종료 + 총액 리셋 단일 원자 트랜잭션(fail closed).**
```
1. session = TableRepository.get_active_session(store_id, table_id)
     - 없음 → 404 / 이미 종료 → 409
2. 미완료 주문 검사(Q2=B):
     pending = OrderRepository.count_by_status(store_id, session_id,
                 status in {PENDING,PREPARING}, deleted 제외)
     - if pending > 0 → 409 (BR-SESS-04: 먼저 상태 정리 요구, 완료 차단)
3. HistoryService.archive_session(store_id, session_id, completed_at=now)
     → 유효 주문(deleted 제외)을 OrderHistory(+Item)로 스냅샷 이관
4. TableRepository.end_session(session_id, status=COMPLETED, completed_at=now)
5. (현재 세션 주문은 이력 이관 완료 → 대시보드 집계 대상에서 제외됨: 세션 COMPLETED)
6. AuditLog(action=SESSION_COMPLETE, target=TableSession, actor, archived_count)
7. commit (실패 시 rollback → 세션/이력 변경 없음)
8. return {table_id, archived_order_count, completed_at, table_total_amount:0}
```
- **Q2=B**: PENDING/PREPARING 주문이 남아 있으면 완료를 차단(409). 관리자가 상태를 COMPLETED로 정리하거나 삭제 후 재시도.

---

## 6. HistoryService

### 6.1 archive_session(store_id, session_id, completed_at) → int
```
1. orders = OrderRepository.list_by_session(store_id, session_id, deleted 제외)
2. for each order: HistoryRepository.insert_history(order 스냅샷 + items 스냅샷, completed_at)
3. return count
```
- complete_session 트랜잭션 내에서 호출(원자성). 스냅샷 복사(원본 불변, domain-entities §2.9/2.10).

### 6.2 list_history(store_id, table_id?, date_from?, date_to?, page, size) → {items, page_meta}  [A3-S4]
```
1. rows = HistoryRepository.query(store_id, filters{table_id, date_from, date_to})
     - date 필터는 completed_at 기준(Asia/Seoul)
2. 정렬: completed_at 역순(계약 §2.5)
3. 페이지네이션 → page_meta
4. return {items:[HistoryEntry], page_meta}
```

---

## 7. 트랜잭션 경계 요약

| 작업 | 트랜잭션 범위 | 실패 시 |
|---|---|---|
| 주문 생성 | 채번(max+1) + order/items insert | 전체 롤백, 주문 미생성(ORDER_EMPTY/TOTAL_MISMATCH/SESSION_CLOSED는 사전 차단) |
| 주문 삭제 | soft-delete + 총액 재계산 + 감사 | 전체 롤백 |
| 상태 변경 | update + 감사 | 롤백 |
| 테이블 설정 | table upsert + session create + 감사 | 롤백(활성 세션 있으면 사전 409) |
| 이용 완료 | 이력 이관(N건) + 세션 종료 + 감사 | 전체 롤백(부분 이관 금지) |

- 모든 다중 쓰기는 **원자적**. 부분 성공 없음(SECURITY-15 fail closed).

---

## 8. Testable Properties (PBT-01, Partial 모드)

> Partial 모드: PBT-02/03/07/08/09 블로킹. backend-api의 순수 계산·직렬화 라운드트립에 한정 적용(NFR-T-01).

| 컴포넌트/함수 | 속성 | 카테고리 | 근거 |
|---|---|---|---|
| `line_amount = unit_price × quantity` (OrderService) | 임의 (price≥0, qty≥1)에서 line_amount ≥ 0, = price*qty | Invariant | PBT-03 |
| `total_amount = Σ line_amount` (OrderService) | 항목 순서와 무관하게 합 동일(교환·결합) / 빈 목록 검증은 별도 차단 | Invariant + Commutativity | PBT-03 |
| 주문번호 포맷 `{store_id}-{YYYYMMDD}-{NNN}` 생성↔파싱 | format(store, date, seq) → parse → (store, date, seq) 라운드트립 | Round-trip | PBT-02 |
| 도메인 모델 직렬화(Pydantic ↔ JSON) | serialize → deserialize = identity(스냅샷 필드 보존) | Round-trip | PBT-02 |
| `recalculate_table_total` | soft-delete 제외 합 = 개별 유효주문 합(오라클 대비 가능) | Invariant | PBT-03 |

- **생성기(PBT-07)**: 도메인 제약 준수(price≥0 정수, qty 1..상한, store_id/date 형식). 원시 타입 단독 사용 금지.
- **재현성(PBT-08)**: seed 로깅, shrinking 활성. CI 포함.
- **프레임워크(PBT-09)**: Python → **Hypothesis**(NFR Requirements 단계에서 tech stack에 고정, requirements.txt 등록).
- 상태 기반(PBT-06)·오라클(PBT-05)은 Partial 모드에서 비블로킹(advisory). 세션/주문 상태 머신은 참고용으로만 언급.
