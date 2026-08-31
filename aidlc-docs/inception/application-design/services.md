# Services — 테이블오더 서비스

> 서비스 계층 정의, 책임, 오케스트레이션 패턴. 서비스는 Router의 요청을 받아 Repository를 조율하며 비즈니스 규칙을 적용한다.

---

## 1. 서비스 목록 및 책임

| 서비스 | 책임 | 의존 Repository | 관련 스토리 |
|---|---|---|---|
| **AuthService** | 관리자/테이블 인증, JWT 발급·검증, 로그인 시도 제한 | Store, Table | A1-S1~S3, C1-S1 |
| **MenuService** | 매장 범위 메뉴/카테고리 조회 | Menu | C2-S1, C2-S2 |
| **OrderService** | 주문 생성·조회·상태변경·삭제, 총액 재검증/재계산, 주문번호 채번 | Order, Table | C4-S1~S3, C5-S1, A2-S2/S4, A3-S2 |
| **TableSessionService** | 테이블 설정, 세션 라이프사이클, 대시보드 집계, 이용 완료 | Table, Order, History | C1-S1/S2, A2-S1, A3-S1/S3 |
| **HistoryService** | 세션 종료 시 이력 기록, 과거 주문 조회 | History, Order | A3-S3/S4 |

> **보안 격리(SECURITY-11)**: AuthService 및 SecurityMiddleware가 인증/인가를 전담. 타 서비스는 이미 인가된 요청을 신뢰하되 매장 범위 스코프는 항상 적용(defense in depth).

---

## 2. 핵심 오케스트레이션 시나리오

### 2.1 주문 생성 (C4-S1)
```
OrderRouter.create
  → SecurityMiddleware.require_table (JWT 검증, 세션·매장 확인)
  → RequestValidation (items 타입/길이 검증)
  → OrderService.create_order
       → TableSessionService.get_or_start_session (첫 주문 시 세션 시작)
       → MenuRepository (단가 조회 → 서버측 총액 재검증)
       → OrderService.generate_order_number (매장별 일자 순번)
       → OrderRepository.insert_order (+ OrderItem)
  → 응답: 주문번호·총액
```

### 2.2 관리자 대시보드 폴링 (A2-S1/S2)
```
TableRouter.dashboard (~2초 폴링)
  → SecurityMiddleware.require_admin
  → TableSessionService.get_dashboard
       → OrderRepository.list/aggregate (테이블별 총액 + 최신 3건)
  → 응답: TableCard[] (전체 조회, Q4=A)
```

### 2.3 주문 상태 변경 (A2-S4 → C5-S2 반영)
```
OrderRouter.update_status
  → SecurityMiddleware.require_admin + assert_owns_resource (매장 범위)
  → OrderService.update_status
       → OrderRepository.update_status
  → 다음 폴링 주기에 고객·관리자 화면 반영
```

### 2.4 주문 삭제 (A3-S2)
```
OrderRouter.delete
  → SecurityMiddleware.require_admin + assert_owns_resource
  → OrderService.delete_order
       → OrderRepository.delete
       → OrderService.recalculate_table_total
       → LoggingComponent.log_event (감사: 누가/언제/무엇, SECURITY-13)
  → 응답: 재계산된 총액
```

### 2.5 이용 완료 / 세션 종료 (A3-S3)
```
TableRouter.complete
  → SecurityMiddleware.require_admin
  → TableSessionService.complete_session
       → HistoryService.archive_session (주문 → OrderHistory, 완료 시각 기록)
       → OrderRepository (현재 세션 주문 정리)
       → TableRepository.end_session (현재 주문/총액 0 리셋)
  → 이후 새 고객 첫 주문 시 새 세션 ID 시작
```

### 2.6 테이블 자동 로그인 (C1-S1)
```
AuthRouter.table_login
  → RequestValidation
  → AuthService.authenticate_table (매장·테이블·비밀번호 검증)
       → 유효 세션 확인/연결
       → AuthService.issue_jwt (매장·테이블·세션 클레임, TTL=세션 잔여)
  → 응답: TableToken (클라이언트 localStorage 저장)
```

---

## 3. 서비스 설계 원칙

- **트랜잭션 경계**: 다중 쓰기(예: 이용 완료 = 이력 이동 + 리셋)는 단일 트랜잭션으로 원자성 보장, 실패 시 롤백(fail closed, SECURITY-15).
- **총액 신뢰 경계**: 클라이언트 총액은 신뢰하지 않고 서버(OrderService)에서 Σ(단가×수량) 재검증.
- **매장 범위 스코프**: 모든 서비스 메서드는 `store_id`를 필수 인자로 받아 테넌트 격리.
- **타임존**: 모든 시각은 Asia/Seoul 기준 기록·표시(NFR-D-03).
- **로깅**: 상태 변경·삭제·인증 실패 등 보안/감사 이벤트는 구조화 로깅(SECURITY-03/13).
