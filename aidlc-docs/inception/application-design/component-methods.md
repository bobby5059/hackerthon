# Component Methods — 테이블오더 서비스

> 메서드 시그니처와 고수준 목적, 입출력 타입. **상세 비즈니스 규칙·검증 로직·엣지 케이스는 Functional Design(per-unit, CONSTRUCTION)에서 정의.**
> 시그니처는 설계 의도 전달용 의사표기(Python/TS 혼용)이며 구현 시 조정될 수 있다.

---

## 1. 백엔드 Service 계층 메서드

### AuthService
| 메서드 | 목적 | 입력 → 출력 |
|---|---|---|
| `authenticate_admin(store_id, username, password)` | 관리자 자격증명 검증 후 JWT 발급 | (str, str, str) → `AdminToken` \| 인증 실패 |
| `authenticate_table(store_id, table_no, table_password)` | 테이블 로그인 검증 후 테이블 세션 JWT 발급 | (str, str, str) → `TableToken` \| 실패 |
| `issue_jwt(claims, ttl)` | JWT 생성(서명·만료·발급자) | (dict, timedelta) → str |
| `verify_jwt(token)` | JWT 서버측 검증(서명·만료·발급자) | str → `TokenClaims` \| 예외 |
| `register_failed_attempt(store_id, username)` | 로그인 실패 기록·잠금 판단(SECURITY-12) | (str, str) → `LockStatus` |

### MenuService
| 메서드 | 목적 | 입력 → 출력 |
|---|---|---|
| `list_menu(store_id)` | 매장 범위 카테고리+메뉴 조회 | str → `list[Category]` |
| `get_menu(store_id, menu_id)` | 메뉴 상세 조회 | (str, str) → `Menu` \| None |

### OrderService
| 메서드 | 목적 | 입력 → 출력 |
|---|---|---|
| `create_order(store_id, table_id, session_id, items)` | 주문 생성, 서버측 총액 재검증, 주문번호 채번 | (…, list[OrderItemInput]) → `Order` |
| `generate_order_number(store_id, date)` | 매장별 일자 순번 채번(Q5=A) | (str, date) → str |
| `list_session_orders(store_id, session_id)` | 현재 세션 주문 전체 조회(폴링, Q4=A) | (str, str) → `list[Order]` |
| `update_status(store_id, order_id, status)` | 주문 상태 변경(대기중/준비중/완료) | (str, str, OrderStatus) → `Order` |
| `delete_order(store_id, order_id, actor)` | 주문 직권 삭제 + 감사 로깅 | (str, str, str) → `DeleteResult` |
| `recalculate_table_total(store_id, table_id)` | 테이블 현재 총 주문액 재계산 | (str, str) → Decimal |

### TableSessionService
| 메서드 | 목적 | 입력 → 출력 |
|---|---|---|
| `setup_table(store_id, table_no, password)` | 테이블 초기 설정 + 16시간 세션 생성 + 자동로그인 활성화 | (str, str, str) → `Table` |
| `get_or_start_session(store_id, table_id)` | 유효 세션 반환 또는 첫 주문 시 새 세션 시작 | (str, str) → `TableSession` |
| `get_dashboard(store_id, table_filter=None)` | 테이블별 총액+최신 3건 집계(폴링, Q4=A) | (str, str?) → `list[TableCard]` |
| `complete_session(store_id, table_id)` | 이용 완료: 이력 이동·현재주문/총액 리셋 | (str, str) → `CompleteResult` |

### HistoryService
| 메서드 | 목적 | 입력 → 출력 |
|---|---|---|
| `archive_session(store_id, session_id, completed_at)` | 세션 주문을 OrderHistory로 이동 | (str, str, datetime) → int |
| `list_history(store_id, table_id=None, date_from=None, date_to=None)` | 과거 주문 조회(시간 역순, 날짜 필터) | (…) → `list[HistoryEntry]` |

---

## 2. 백엔드 Repository 계층 메서드 (대표)

| 컴포넌트 | 대표 메서드 |
|---|---|
| **StoreRepository** | `get_store(store_id)`, `get_admin(store_id, username)` |
| **TableRepository** | `get_table(store_id, table_id)`, `upsert_table(...)`, `create_session(...)`, `get_active_session(store_id, table_id)`, `end_session(session_id, completed_at)` |
| **MenuRepository** | `list_categories(store_id)`, `list_menus(store_id)`, `get_menu(store_id, menu_id)` |
| **OrderRepository** | `insert_order(...)`, `list_by_session(store_id, session_id)`, `update_status(store_id, order_id, status)`, `delete(store_id, order_id)`, `sum_table_total(store_id, table_id)` |
| **HistoryRepository** | `insert_history(...)`, `query(store_id, filters)` |

> 모든 메서드는 `store_id`로 스코프(테넌트 격리) + 파라미터화 쿼리(SECURITY-05).

---

## 3. 횡단 관심사 메서드

| 컴포넌트 | 메서드 | 목적 |
|---|---|---|
| **SecurityMiddleware** | `require_admin(request)` / `require_table(request)` | JWT 검증 + deny-by-default 인가 의존성 |
| | `assert_owns_resource(claims, store_id, resource)` | 객체 소유권 검증(IDOR 방지, SECURITY-08) |
| **SecurityHeadersMiddleware** | `apply_headers(response)` | 보안 HTTP 헤더 설정(SECURITY-04) |
| **LoggingComponent** | `get_logger(name)`, `log_event(level, msg, ctx)` | 구조화 로깅·민감정보 마스킹(SECURITY-03) |
| **GlobalErrorHandler** | `handle(exc)` | fail closed + 일반화 응답(SECURITY-15) |
| **RateLimiter** | `check(key)`, `record_failure(key)` | 로그인 브루트포스 방지 |

---

## 4. 고객 프론트엔드 메서드 (대표)

| 컴포넌트 | 메서드 | 목적 |
|---|---|---|
| **AutoLoginGuard** | `resolveSession(): SessionState` | 저장된 테이블 토큰 유효성 확인 후 라우팅 |
| **CartPanel** | `addItem(menu)`, `changeQty(itemId, delta)`, `clear()`, `total(): number` | 장바구니 조작·총액(PricingUtil 사용) |
| **OrderConfirm** | `submitOrder(cart): Promise<OrderResult>` | 주문 확정 요청·성공/실패 처리 |
| **OrderHistoryView** | `usePolling(sessionId)` | ~2초 폴링으로 주문/상태 갱신 |

## 5. 관리자 프론트엔드 메서드 (대표)

| 컴포넌트 | 메서드 | 목적 |
|---|---|---|
| **AdminLogin** | `login(storeId, username, password)` | 로그인·JWT 저장 |
| **AuthSessionGuard** | `isExpired(): boolean`, `logout()` | 16시간 만료 감지·자동 로그아웃 |
| **DashboardGrid** | `usePolling(filter)` | ~2초 대시보드 갱신, 신규 주문 강조 |
| **OrderStatusControl** | `changeStatus(orderId, status)` | 상태 변경 |
| **OrderDeleteAction** | `confirmAndDelete(orderId)` | 확인 팝업 후 삭제 |
| **TableSetupForm** | `setupTable(tableNo, password)` | 테이블 초기 설정 |
| **SessionCompleteAction** | `confirmAndComplete(tableId)` | 이용 완료 처리 |

## 6. 공유 라이브러리 메서드

| 컴포넌트 | 메서드 | 목적 |
|---|---|---|
| **ApiClient** | `request<T>(method, path, body?, token?)` | 공통 HTTP 호출·오류 정규화 |
| **PricingUtil** | `lineTotal(price, qty)`, `cartTotal(items)` | 금액 계산(순수 함수, PBT 대상 NFR-T-01) |
| **PollingHook** | `usePolling(fetchFn, intervalMs=2000)` | 폴링 공통 훅 |
