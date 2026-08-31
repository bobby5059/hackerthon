# Business Rules — backend-api

> CONSTRUCTION / Unit 1 (backend-api) / Functional Design
> 검증 규칙·상태 전이·인가/IDOR·총액 재검증·에러 매핑·감사 규칙을 확정한다.
> SECURITY Baseline(Enabled) 매핑 포함. 엔티티=`domain-entities.md`, 로직=`business-logic-model.md`.

---

## 1. 입력 검증 규칙 (SECURITY-05, Q11=보안 최소 상한 적용)

> Q11 답변 B(수치 상한 없음)는 활성 Security Baseline(SECURITY-05, 블로킹) 및 계약 §8과 충돌 →
> 사용자 확정에 따라 **SECURITY-05가 요구하는 최소 경계만 적용**하고, 그 외 임의 비즈니스 캡은 두지 않는다.

| ID | 규칙 | 위반 시 | 매핑 |
|---|---|---|---|
| BR-VAL-01 | 모든 요청 본문/쿼리는 스키마 검증(타입·형식). 파라미터화 쿼리만 사용 | 400 VALIDATION_ERROR | SECURITY-05 |
| BR-VAL-02 | 주문 생성: `items`는 배열, 각 원소 `{menu_id:string, quantity:int≥1}`. **items 배열 최대 크기·quantity 상한·문자열 필드 max length 적용**(정확한 수치는 NFR Design에서 확정; 예: items≤100, quantity≤999, string≤원 필드 정의 길이) | 400 VALIDATION_ERROR | SECURITY-05 |
| BR-VAL-03 | 테이블 setup: `table_no`(1~20자), `table_password`=**4~6자리 숫자 PIN**(Q4=A) | 400 VALIDATION_ERROR | SECURITY-05, SECURITY-12(예외) |
| BR-VAL-04 | 관리자 로그인: `store_id`,`username`(1~50자),`password`(존재·길이) | 400/401 | SECURITY-05/12 |
| BR-VAL-05 | **요청 본문 크기 제한** 프레임워크/미들웨어 레벨 설정(기본값 NFR Design 확정) | 413/400 | SECURITY-05 |
| BR-VAL-06 | 페이지네이션 `page≥1`, `size`는 1..100(계약 §1.4), 초과 시 클램프 또는 400 | 400/클램프 | SECURITY-05 |
| BR-VAL-07 | 사용자 제공 문자열은 저장/응답 시 이스케이프(XSS 방지). API-only 응답이라 위험 낮으나 스냅샷 문자열 정규화 | — | SECURITY-05 |

> **최소 경계 원칙**: 위 상한은 "안전을 위한 상한"이며 정상 사용을 방해하지 않는 넉넉한 값. Q11=A식 엄격한 비즈니스 규칙(예: 50개/99개)은 강제하지 않되, SECURITY-05 준수를 위해 상한 자체는 반드시 존재한다.

---

## 2. 상태 전이 규칙

### 2.1 주문 상태 (Q1=B — 관리자 자유 전이)
| ID | 규칙 | 매핑 |
|---|---|---|
| BR-ORD-06 | 관리자는 매장 범위 내 주문 상태를 `PENDING`/`PREPARING`/`COMPLETED` 중 **임의로 전이** 가능(역방향·건너뛰기 포함). MVP 단순화 | 계약 §5.3 |
| BR-ORD-07 | 허용값 외 status 값 → 400 VALIDATION_ERROR | SECURITY-05 |
| BR-ORD-08 | 상태 변경 대상은 **삭제되지 않은(deleted_at IS NULL)** 주문에 한함. 삭제된 주문 상태변경 → 404 | — |

```
PENDING ⇄ PREPARING ⇄ COMPLETED   (관리자, 매장 범위 내 임의 전이)
```

### 2.2 세션 상태
| ID | 규칙 | 매핑 |
|---|---|---|
| BR-SESS-01 | 한 테이블에 `ACTIVE` 세션은 **최대 1개**(유일성) | — |
| BR-SESS-02 | 주문은 `ACTIVE`이며 만료되지 않은 세션에만 생성. 토큰 session_id ≠ 현재 활성 session_id → 409 SESSION_CLOSED | 계약 §2.3 |
| BR-SESS-03 | **활성 세션이 있는 테이블 재-setup → 409**(Q5=C). 먼저 이용 완료 요구 | 계약 §2.4 |
| BR-SESS-04 | **이용 완료 시 PENDING/PREPARING 주문 존재 → 409**(Q2=B). 완료 차단, 상태 정리 요구 | 계약 §2.4 |
| BR-SESS-05 | 세션 만료(now ≥ expires_at, ≤16h): 요청 시 검사 → `EXPIRED` 처리 후 401 TOKEN_EXPIRED. **자동 연장/자동 재시작 없음**(Q7=A) → 관리자 재-setup 필요 | 계약 §2.1 |

```
(setup/첫주문) → ACTIVE ──16h 경과(요청시 검사)──> EXPIRED
                    │
                    └── 관리자 이용완료(미완료 주문 없을 때) ──> COMPLETED
```

---

## 3. 주문 도메인 규칙

| ID | 규칙 | 위반 시 | 매핑 |
|---|---|---|---|
| BR-ORD-01 | 빈 장바구니 주문 금지(items 0개) | 400 ORDER_EMPTY | 계약 §2.3, C4-S1 |
| BR-ORD-02 | store/table/session은 **토큰에서만 도출**(요청 본문 무시) | 서버 강제 | SECURITY-08 |
| BR-ORD-03 | 총액은 서버가 Σ(단가×수량) **재검증**. 클라 총액 신뢰 안 함. (클라가 총액 전달 시) 불일치 → 422 TOTAL_MISMATCH | 422 | 계약 §2.3, C4-S1 |
| BR-ORD-04 | 존재하지 않는 menu_id(매장 범위 밖 포함) → 422(또는 400 VALIDATION) | 422/400 | — |
| BR-ORD-09 | 단가·명칭은 주문 시점 **스냅샷** 보존. 이후 메뉴 변경과 무관하게 이력 일관 | 불변 | 계약 §3.3 |
| BR-ORD-10 | 실패 시 주문 **미생성**(부분 저장 금지) | rollback | SECURITY-15, C4-S3 |

### 3.1 채번 규칙 (Q6=A)
| ID | 규칙 |
|---|---|
| BR-NUM-01 | 형식 `{store_id}-{YYYYMMDD}-{NNN}`, YYYYMMDD는 Asia/Seoul 일자 |
| BR-NUM-02 | NNN은 매장·일자 기준 001부터. **삽입 트랜잭션 내 MAX(order_seq)+1**(트랜잭션 락 직렬화) |
| BR-NUM-03 | 999 초과 시 자릿수 확장(1000, …). 삭제(soft-delete) 주문의 순번도 재사용 금지(MAX 기준) |
| BR-NUM-04 | `(store_id, order_date, order_seq)` UNIQUE — 경합 시 위반→재시도/실패(fail closed) |

---

## 4. 인가 / IDOR 규칙 (SECURITY-08)

| ID | 규칙 | 매핑 |
|---|---|---|
| BR-AUTHZ-01 | **Deny-by-default**: 공개 2종(admin/login, table/login) 외 모든 엔드포인트는 유효 JWT 필수 | SECURITY-08 |
| BR-AUTHZ-02 | 토큰 `typ` 검사: 테이블 토큰(typ=table)으로 관리자(🔑A) 엔드포인트 접근 → 403 FORBIDDEN. 반대도 동일 | SECURITY-08, 계약 §4 |
| BR-AUTHZ-03 | **객체 소유권(IDOR)**: 리소스 ID 참조 시 `resource.store_id == claims.store_id` 검증. 위반 → 404(존재 은닉) 또는 403 | SECURITY-08 |
| BR-AUTHZ-04 | 테이블 토큰은 자신의 `table_id`/`session_id` 범위만 접근(타 테이블 주문 조회/생성 불가) | SECURITY-08 |
| BR-AUTHZ-05 | 모든 서비스 메서드는 `store_id`로 스코프(테넌트 격리, defense in depth) | SECURITY-08/11 |
| BR-AUTHZ-06 | JWT 서버측 검증(서명·exp·iss)을 **매 요청**마다 수행(로그인 시점만이 아님) | SECURITY-08 |
| BR-AUTHZ-07 | CORS는 고객/관리자 앱 오리진만 명시 허용(인증 엔드포인트에 와일드카드 금지) | SECURITY-08 |

---

## 5. 인증 / 자격증명 규칙 (SECURITY-12)

| ID | 규칙 | 매핑 |
|---|---|---|
| BR-AUTH-01 | 비밀번호는 **bcrypt**로 해시 저장(관리자·테이블 PIN 모두). 평문/로그 노출 금지 | SECURITY-12/03 |
| BR-AUTH-02 | 관리자 비밀번호 **최소 8자**. **테이블 PIN은 4~6자리 숫자 예외(Q4=A)** — 본 문서에 명시된 문서화 예외 | SECURITY-12 |
| BR-AUTH-03 | 로그인 실패 rate limit: 윈도우 내 임계 초과 시 429 RATE_LIMITED(관리자·테이블 로그인 모두). 임계/윈도우 NFR Design 확정 | SECURITY-12 |
| BR-AUTH-04 | 인증 실패는 **일반화 메시지**(사용자 열거/존재여부 노출 금지). 존재/부재 동일 응답 경로 | SECURITY-12/15 |
| BR-AUTH-05 | 세션 서버측 만료·무효화: 이용 완료 시 세션 COMPLETED로 토큰 무효화(fail closed) | SECURITY-12 |
| BR-AUTH-06 | 하드코딩 자격증명·서명키 금지. 서명키/시드 비번은 환경설정·시드 스크립트로 주입 | SECURITY-12 |
| BR-AUTH-07 | JWT에 민감정보 미포함(비밀번호/해시 등). 클레임은 계약 §4 한정 | SECURITY-12 |

> **MFA(SECURITY-12 일부)**: 로컬 단일 매장 MVP·태블릿 자동로그인 특성상 MFA는 **N/A**(비블로킹, 문서화 예외). 프로덕션 전환 시 관리자 계정 MFA 재검토.

---

## 6. 대시보드 / 이력 규칙

| ID | 규칙 | 매핑 |
|---|---|---|
| BR-DASH-01 | `TableCard.recent_orders`는 최신 3건(created_at 내림차순, soft-delete 제외). `item_summary` 축약: "대표메뉴명 외 N건" | 계약 §2.4 |
| BR-DASH-02 | `TableCard.total_amount`는 활성 세션 유효 주문 Σ(soft-delete 제외) | 계약 §2.4 |
| BR-DASH-03 | **`has_new`는 서버가 계산하지 않음**(Q9=A): 응답에 **항상 `false`로 포함**(생략 금지 — `shared` 필수 필드). 클라가 server_time/created_at 비교로 신규 판단 | 계약 §5.1 |
| BR-DASH-04 | 대시보드/주문 목록은 **폴링 전체 조회**(계약 §5.1, Q4=A). 응답에 server_time(Asia/Seoul) 포함 | NFR-P-01 |
| BR-HIST-01 | 이력은 세션 종료 시 유효 주문 스냅샷 이관, session_id 그룹화, completed_at 기록 | NFR-D-01 |
| BR-HIST-02 | 이력 조회 정렬: completed_at 역순. 날짜 필터는 completed_at 기준 | 계약 §2.5 |
| BR-HIST-03 | 세션 종료 후 현재 주문/총액 0 리셋(세션 COMPLETED로 집계 제외) | NFR-D-02 |

---

## 7. 에러 매핑 (계약 §1.3, SECURITY-15)

| 상황 | HTTP | code |
|---|---|---|
| 입력 검증 실패(타입/길이/형식/상한) | 400 | VALIDATION_ERROR |
| 빈 장바구니 | 400 | ORDER_EMPTY |
| 토큰 없음/무효 | 401 | UNAUTHORIZED |
| 토큰/세션 만료 | 401 | TOKEN_EXPIRED |
| typ 불일치·소유권 위반(인가) | 403 | FORBIDDEN |
| 리소스 없음(또는 은닉) | 404 | NOT_FOUND |
| 활성 세션 재-setup(Q5=C) / 미완료 주문 있는 이용완료(Q2=B) / 종료 세션 주문 | 409 | SESSION_CLOSED |
| 총액 불일치 | 422 | TOTAL_MISMATCH |
| 유효하지 않은 menu_id(의미 검증) | 422 | VALIDATION_ERROR |
| 로그인 시도 제한 | 429 | RATE_LIMITED |
| 예기치 못한 오류 | 500 | INTERNAL_ERROR |

- 모든 에러는 `{error:{code,message,request_id}}` 형식(계약 §1.3). **내부 스택/경로/DB 정보 노출 금지**(SECURITY-15/09).
- **Fail closed**: 오류 시 접근 거부/작업 중단, 부분 성공 없음. 외부 호출(DB)은 명시적 예외 처리 + 롤백 + 리소스 정리.
- **Global error handler**: 애플리케이션 진입점에 전역 핸들러 → 일반화 응답 + 구조화 로깅.

---

## 8. 감사 / 로깅 규칙 (SECURITY-03/13)

| ID | 규칙 | 매핑 |
|---|---|---|
| BR-AUD-01 | 중요 변경(주문 삭제·상태변경·세션 종료·테이블 설정)은 AuditLog 기록: actor/시각/target/before·after/request_id | SECURITY-13 |
| BR-AUD-02 | 구조화 로깅: timestamp·request_id·level·message. 인증 실패/인가 거부/rate limit 등 보안 이벤트 로깅 | SECURITY-03/14 |
| BR-AUD-03 | 비밀번호·토큰·PIN 등 **민감정보 로깅/저장 금지**(마스킹) | SECURITY-03 |
| BR-AUD-04 | 애플리케이션은 자기 감사 로그를 삭제/수정하지 않음(append-only 지향) | SECURITY-13/14 |

---

## 9. Security Baseline 적용성 평가 (Compliance Summary)

| 규칙 | 상태 | 근거 |
|---|---|---|
| SECURITY-01 (암호화 at-rest/transit) | **N/A** | 로컬 SQLite 파일·로컬 배포(HTTP). 프로덕션 전환 시 TLS·DB 암호화 재검토(Infrastructure 단계) |
| SECURITY-02 (네트워크 중개 로깅) | **N/A** | 로컬 MVP, LB/API GW/CDN 없음 |
| SECURITY-03 (앱 로깅) | **Compliant** | 구조화 로깅·request_id·민감정보 마스킹(BR-AUD-02/03) |
| SECURITY-04 (HTTP 보안 헤더) | **Partial/N/A** | API-only(JSON) 서비스로 HTML 미제공 → 헤더 대부분 N/A. 적용 가능한 항목(X-Content-Type-Options 등)은 미들웨어로 설정(NFR Design). HTML은 프론트 유닛 책임 |
| SECURITY-05 (입력 검증) | **Compliant** | BR-VAL-01~07: 타입·길이·상한·본문크기·파라미터화 쿼리. **Q11 충돌은 보안 최소 상한 적용으로 해소** |
| SECURITY-06 (최소 권한 IAM) | **N/A** | 클라우드 IAM 없음(로컬) |
| SECURITY-07 (네트워크 구성) | **N/A** | 로컬, 보안그룹/ACL 없음 |
| SECURITY-08 (앱 인가) | **Compliant** | BR-AUTHZ-01~07: deny-by-default·IDOR·typ 검증·CORS·JWT 매요청 검증 |
| SECURITY-09 (하드닝/오구성) | **Compliant(설계)** | 기본자격증명 금지·일반화 에러(§7)·디렉터리 리스팅 N/A. 세부는 Code/NFR |
| SECURITY-10 (공급망) | **Deferred→NFR** | 의존성 lock·취약점 스캔은 NFR Requirements/Code에서 확정(requirements.txt lock) |
| SECURITY-11 (보안 설계) | **Compliant** | AuthService/SecurityMiddleware 격리·rate limit·오남용 케이스(§2,§5) |
| SECURITY-12 (인증/자격) | **Compliant(문서화 예외)** | bcrypt·rate limit·서버측 만료(BR-AUTH-*). **테이블 PIN 4~6자리 예외(Q4=A) 문서화**, 관리자 8자↑ 유지. **MFA는 N/A(로컬 MVP)** |
| SECURITY-13 (무결성/감사) | **Compliant** | AuditLog before/after·안전 역직렬화(Pydantic 스키마)(BR-AUD-01/04) |
| SECURITY-14 (알림/모니터링) | **Partial/Deferred** | 로컬 MVP: 보안 이벤트 로깅으로 대체. 알림 대시보드·로그 보존 정책은 프로덕션 전환 시(N/A로 문서화) |
| SECURITY-15 (예외 처리/fail-safe) | **Compliant** | 전역 에러 핸들러·fail closed·트랜잭션 롤백·일반화 메시지(§7) |

> **블로킹 결함: 없음**. Q11 충돌은 사용자 확정(보안 최소 상한)으로 해소되어 SECURITY-05 Compliant. 문서화 예외(테이블 PIN, MFA N/A)는 비블로킹.

## 10. PBT 적용성 (Partial 모드, PBT-01)
- Testable Properties는 `business-logic-model.md §8`에 문서화(금액 계산 invariant, 주문번호/직렬화 라운드트립).
- Partial 모드 블로킹 규칙(PBT-02/03/07/08/09) 대상 식별 완료. 프레임워크=Hypothesis(NFR Requirements에서 tech stack 고정).
- 상태 기반(PBT-06)·오라클(PBT-05)은 advisory(비블로킹).
