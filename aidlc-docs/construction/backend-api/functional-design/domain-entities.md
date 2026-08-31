# Domain Entities — backend-api

> CONSTRUCTION / Unit 1 (backend-api) / Functional Design
> 기술 중립 도메인 모델 + SQLite 스키마 매핑 + 스냅샷/감사 규칙.
> 계약 정합성 기준: `integration-contract.md` v1.0 §3(공유 모델). 응답 직렬화 필드명·타입은 계약을 따른다.
> 확정 답변 반영: Q1=B(자유 전이), Q2=B(미완료 차단), Q3=B(soft delete), Q4=A(테이블 PIN 예외), Q5=C(활성 세션 재-setup 거부), Q6=A(트랜잭션 내 max+1 채번), Q7=A(요청 시 만료검사), Q8=B(최소 시드), Q9=A(has_new 서버 미계산), Q10=B(메뉴 가용성), Q11=보안 최소 상한.

---

## 1. 엔티티 개요 (ERD 개념)

```
Store 1───* AdminUser
Store 1───* Table
Store 1───* Category 1───* Menu
Table 1───* TableSession
TableSession 1───* Order 1───* OrderItem
TableSession 1───* OrderHistory 1───* OrderHistoryItem   (세션 종료 시 스냅샷 이관)
(횡단) AuditLog, LoginAttempt
```

- 모든 업무 엔티티는 `store_id`에 소속되어 멀티테넌시 격리(계약 §1.5, SECURITY-08).
- 응답에서 모든 ID는 문자열로 직렬화(계약 §1.1). 내부 저장 PK 형태는 구현 자유(문자열 권장).
- 모든 시각은 저장·표시 모두 **Asia/Seoul(+09:00) ISO 8601**(NFR-D-03).
- 금액 필드는 모두 **정수 KRW**(계약 §1.1, §3.3).

---

## 2. 엔티티 상세

### 2.1 Store (매장)
| 속성 | 타입 | 제약 | 설명 |
|---|---|---|---|
| store_id | string | PK | 매장 식별자 (예: `store-001`) |
| name | string | not null, 1~100자 | 매장명 |
| created_at | datetime(+09:00) | not null | 생성 시각 |

- MVP는 단일 매장 시드(Q8=B). 다중 매장 등록 UI는 범위 외.

### 2.2 AdminUser (관리자)
| 속성 | 타입 | 제약 | 설명 |
|---|---|---|---|
| admin_id | string | PK | 관리자 식별자 |
| store_id | string | FK→Store, not null | 소속 매장 |
| username | string | not null, 1~50자, (store_id, username) UNIQUE | 로그인 ID |
| password_hash | string | not null | **bcrypt 해시**(SECURITY-12). 평문/로그 노출 금지 |
| created_at | datetime | not null | |

- `password_hash`는 응답·로그에 절대 포함하지 않음(SECURITY-03/12).
- 관리자 비밀번호 정책: **최소 8자**(SECURITY-12) — 시드/설정 시 강제.

### 2.3 Table (테이블)
| 속성 | 타입 | 제약 | 설명 |
|---|---|---|---|
| table_id | string | PK | 테이블 식별자 (예: `tbl-5`) |
| store_id | string | FK→Store, not null | 소속 매장 |
| table_no | string | not null, 1~20자, (store_id, table_no) UNIQUE | 테이블 번호(표시용) |
| table_password_hash | string | nullable | **bcrypt 해시**. setup 전에는 null |
| auto_login_enabled | boolean | default false | setup 완료 시 true |
| created_at | datetime | not null | |

- **테이블 비밀번호 정책(Q4=A, SECURITY-12 문서화 예외)**: 태블릿 현장 편의를 위해 **4~6자리 숫자 PIN** 허용. 관리자 비밀번호(§2.2)는 8자↑ 정책 유지. 저장은 반드시 bcrypt 해시(평문 금지). 본 예외는 §5 및 business-rules.md에 명시.

### 2.4 TableSession (테이블 세션)
| 속성 | 타입 | 제약 | 설명 |
|---|---|---|---|
| session_id | string | PK | 세션 식별자 (예: `sess-abc`) |
| store_id | string | FK→Store, not null | |
| table_id | string | FK→Table, not null | |
| status | enum(ACTIVE, COMPLETED, EXPIRED) | not null, default ACTIVE | 세션 상태 |
| started_at | datetime | not null | 세션 시작 시각 |
| expires_at | datetime | not null | `started_at + 16h`(TTL) |
| completed_at | datetime | nullable | 이용 완료/종료 시각 |

- 인덱스: `(store_id, table_id, status)` — 활성 세션 조회 최적화.
- **활성 세션 유일성 규칙**: 한 테이블에 `status=ACTIVE` 세션은 **최대 1개**(business-rules.md BR-SESS-01).
- 세션 라이프사이클: `setup`(A3-S1) 또는 첫 주문 시 ACTIVE 생성 → 16h 경과 시 EXPIRED(Q7=A, 요청 시 검사) → 관리자 `complete`(A3-S3) 시 COMPLETED.

### 2.5 Category (카테고리)
| 속성 | 타입 | 제약 | 설명 |
|---|---|---|---|
| category_id | string | PK | |
| store_id | string | FK→Store, not null | |
| name | string | not null, 1~50자 | 카테고리명 |
| display_order | int | not null, default 0 | 표시 순서(오름차순) |

- 계약 §3.2 `Category` 대응(응답: category_id, name, display_order).

### 2.6 Menu (메뉴)
| 속성 | 타입 | 제약 | 설명 |
|---|---|---|---|
| menu_id | string | PK | |
| store_id | string | FK→Store, not null | |
| category_id | string | FK→Category, not null | |
| name | string | not null, 1~100자 | 메뉴명 |
| price | int | not null, ≥ 0 | 단가(정수 KRW) |
| description | string | nullable, ≤ 500자 | 설명 |
| image_url | string | nullable | 이미지 URL |
| is_available | boolean | not null, default true | **가용성(Q10=B)**. false=품절/비활성 |

- **가용성(Q10=B)**: `is_available=false` 메뉴는 주문 불가(business-rules.md BR-ORD-05, 422 거부). 계약 응답 모델 `Menu`에 `is_available` 필드 추가(계약 §3.2 확장 — 하위호환 minor, §9 절차로 반영 대상).
- 메뉴는 고정/시드(Q7). 관리자 CRUD는 범위 외.

### 2.7 Order (주문 — 현재 세션)
| 속성 | 타입 | 제약 | 설명 |
|---|---|---|---|
| order_id | string | PK | |
| store_id | string | FK→Store, not null | |
| table_id | string | FK→Table, not null | |
| session_id | string | FK→TableSession, not null | 현재 세션 범위 |
| order_number | string | not null, (store_id, order_date, seq) 파생 UNIQUE | `{store_id}-{YYYYMMDD}-{NNN}`(§6) |
| order_seq | int | not null | 매장·일자 순번(NNN 원본, 채번 Q6=A) |
| order_date | date | not null | 채번 기준 일자(Asia/Seoul) |
| status | enum(PENDING, PREPARING, COMPLETED) | not null, default PENDING | 계약 §3.1 |
| total_amount | int | not null, ≥ 0 | Σ line_amount(서버 재검증) |
| created_at | datetime | not null | |
| deleted_at | datetime | nullable | **soft delete(Q3=B)**. null=유효 |
| deleted_by | string | nullable | 삭제 관리자 식별자(감사) |

- **Soft delete(Q3=B)**: 삭제는 `deleted_at`/`deleted_by` 세팅. 대시보드·총액 집계·목록 조회에서 `deleted_at IS NULL`만 포함. 레코드는 보존하며 별도 `AuditLog`(§2.11) 기록(SECURITY-13).
- 인덱스: `(store_id, session_id, deleted_at)`, `(store_id, order_date)`(채번), `(store_id, table_id, deleted_at)`(총액 집계).

### 2.8 OrderItem (주문 항목 — 스냅샷)
| 속성 | 타입 | 제약 | 설명 |
|---|---|---|---|
| order_item_id | string | PK | |
| order_id | string | FK→Order, not null | |
| menu_id | string | not null | 참조(스냅샷이므로 FK 강제 아님) |
| name | string | not null | **주문 시점 메뉴명 스냅샷** |
| unit_price | int | not null, ≥ 0 | **주문 시점 단가 스냅샷** |
| quantity | int | not null, ≥ 1 | 수량 |
| line_amount | int | not null | `unit_price × quantity` |

- **스냅샷 규칙(계약 §3.3)**: 주문 생성 시점의 `name`·`unit_price`를 복사 보존. 이후 메뉴 변경(가격/이름/품절)과 무관하게 주문·이력 일관성 유지.

### 2.9 OrderHistory (과거 주문 — 이관본)
| 속성 | 타입 | 제약 | 설명 |
|---|---|---|---|
| history_id | string | PK | |
| store_id | string | not null | |
| table_id | string | not null | |
| session_id | string | not null | 그룹화 키(NFR-D-01) |
| order_id | string | not null | 원본 주문 ID(추적) |
| order_number | string | not null | 스냅샷 |
| total_amount | int | not null | 스냅샷 |
| status | enum(PENDING, PREPARING, COMPLETED) | not null | 이관 시점 상태 스냅샷 |
| created_at | datetime | not null | 원 주문 생성 시각 |
| completed_at | datetime | not null | **이용 완료 시각**(세션 종료 시각) |

- 세션 종료(A3-S3) 시 현재 세션의 **유효 주문(soft-delete 제외)**을 이관. 계약 §3.2 `HistoryEntry`로 직렬화(items 포함, 아래 §2.10).

### 2.10 OrderHistoryItem (과거 주문 항목 — 스냅샷)
| 속성 | 타입 | 제약 | 설명 |
|---|---|---|---|
| history_item_id | string | PK | |
| history_id | string | FK→OrderHistory, not null | |
| menu_id | string | not null | |
| name | string | not null | 스냅샷 |
| unit_price | int | not null | 스냅샷 |
| quantity | int | not null | |
| line_amount | int | not null | |

- OrderItem 스냅샷을 그대로 복사(이력 불변).

### 2.11 AuditLog (감사 로그 — SECURITY-13)
| 속성 | 타입 | 제약 | 설명 |
|---|---|---|---|
| audit_id | string | PK | |
| store_id | string | not null | |
| actor | string | not null | 수행 주체(관리자 식별자/username) |
| action | string | not null | 예: `ORDER_DELETE`, `SESSION_COMPLETE`, `ORDER_STATUS_CHANGE`, `TABLE_SETUP` |
| target_type | string | not null | 대상 엔티티(예: `Order`) |
| target_id | string | not null | 대상 ID |
| before_value | json/text | nullable | 변경 전 값(민감정보 마스킹) |
| after_value | json/text | nullable | 변경 후 값 |
| request_id | string | not null | 상관관계 ID(§1.3 request_id) |
| created_at | datetime | not null | |

- **SECURITY-13**: 중요 데이터 변경(삭제·상태변경·세션종료·테이블설정)은 누가/언제/무엇/before·after를 기록. 애플리케이션은 자기 감사 로그를 삭제/수정하지 않음(append-only 지향).
- 민감정보(비밀번호/토큰)는 절대 저장 금지(SECURITY-03).

### 2.12 LoginAttempt (로그인 시도 — SECURITY-12)
| 속성 | 타입 | 제약 | 설명 |
|---|---|---|---|
| attempt_id | string | PK | |
| store_id | string | not null | |
| principal | string | not null | 관리자 username 또는 `table_no`(로그인 키) |
| attempt_type | enum(ADMIN, TABLE) | not null | 로그인 종류 |
| success | boolean | not null | 성공/실패 |
| attempted_at | datetime | not null | |

- 브루트포스 방지(SECURITY-12): 최근 실패 횟수/윈도우 기반 rate limit(business-rules.md BR-AUTH-03). 저장 매체는 SQLite 테이블 또는 인메모리(로컬 MVP) — NFR Design에서 확정.

---

## 3. 열거형 (Enums)

```
OrderStatus       = "PENDING" | "PREPARING" | "COMPLETED"      # 계약 §3.1 (표시: 대기중|준비중|완료)
SessionStatus     = "ACTIVE" | "COMPLETED" | "EXPIRED"          # 내부 상태 (계약 응답에는 직접 노출 안 함)
LoginAttemptType  = "ADMIN" | "TABLE"
```

---

## 4. SQLite 스키마 매핑 지침

| 도메인 타입 | SQLite 타입 | 비고 |
|---|---|---|
| string(ID/이름/URL) | TEXT | |
| int(금액/수량/순번) | INTEGER | 금액은 정수 KRW |
| boolean | INTEGER(0/1) | is_available, auto_login_enabled, success |
| datetime(+09:00) | TEXT(ISO8601) | Asia/Seoul 오프셋 포함 저장(NFR-D-03) |
| date | TEXT(YYYY-MM-DD) | order_date 채번 기준 |
| enum | TEXT + CHECK 제약 | 허용값 제한 |
| json(before/after) | TEXT | 감사 값 직렬화 |

- **파라미터화 쿼리만 사용**(SECURITY-05, 문자열 연결 금지).
- 외래키 제약(`PRAGMA foreign_keys=ON`)과 트랜잭션은 NFR/Code 단계에서 구체화. 채번·이용완료 등 다중 쓰기는 단일 트랜잭션(business-logic-model.md 참조).
- 스냅샷 항목(OrderItem/OrderHistoryItem)은 menu_id를 참조로 두되 FK 강제하지 않음(메뉴 변경/삭제와 독립).

---

## 5. 계약 정합성 및 확장 필드 정리

| 항목 | 계약 §3 모델 | 본 설계 매핑 | 비고 |
|---|---|---|---|
| Category | category_id, name, display_order | Category | 일치 |
| Menu | menu_id, category_id, name, price, description, image_url | Menu + `is_available` | **확장 필드 `is_available` 추가(Q10=B)** — 계약 §9 minor 반영 대상 |
| OrderItem | menu_id, name, unit_price, quantity, line_amount | OrderItem | 일치(스냅샷) |
| Order | order_id, order_number, table_id, session_id, status, items, total_amount, created_at | Order(내부 order_seq/order_date/soft-delete 필드는 응답 비노출) | 일치 |
| TableCard | table_id, table_no, total_amount, recent_orders, has_new | 집계 뷰(엔티티 아님) | **`has_new`는 서버 미계산(Q9=A)** — 생략 또는 항상 false |
| HistoryEntry | order_id, order_number, table_id, items, total_amount, created_at, completed_at | OrderHistory(+Item) | 일치 |
| PageMeta | page, size, total | 조회 응답 메타 | 일치 |

**계약 반영 필요(§9 변경 절차 대상)**:
1. `Menu.is_available` 필드 추가 (하위호환 minor).
2. `TableCard.has_new`는 서버가 세팅하지 않음(항상 false 또는 생략) — 문구 명확화.

> 위 2건은 backend-api OpenAPI에 반영 → `shared` 타입 동기화 순으로 전파(계약 §9).
