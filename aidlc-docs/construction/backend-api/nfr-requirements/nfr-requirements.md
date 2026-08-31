# NFR Requirements — Unit 1 (backend-api)

> backend-api는 **실행 서비스**(FastAPI + SQLite, 로컬 배포). 본 문서는 이 유닛의 비기능 요구사항을 확정한다.
> 기술 스택 결정은 `tech-stack-decisions.md` 참조. 확장: **Security Baseline(Yes, 블로킹)**, **PBT(Partial)**, Resiliency(No).
> 정합성 기준: `integration-contract.md` v1.0(§1/§4/§5/§8), FD(`../functional-design/*`), `shared` NFR/tech-stack.
> 사용자 답변: **Q1~Q12 전부 추천안(A)** (2026-08-31).

---

## 1. 성능 (Performance)

| ID | 요구사항 | 근거 |
|---|---|---|
| NFR-BE-P-01 | 대시보드/주문 폴링 응답에 `server_time`(Asia/Seoul) 포함, 폴링 주기 2000ms 정합(`shared/PollingHook`) | NFR-P-01, 계약 §5.1 |
| NFR-BE-P-02 | 로컬 응답시간 목표 **p95 < 300ms**(폴링/조회 엔드포인트), 정상 데이터 규모(단일 매장) 기준 | Q11=A |
| NFR-BE-P-03 | 목록 조회는 페이지네이션(`page`/`size` 1..100, 계약 §1.4)으로 응답 크기 제한 | 계약 §1.4, BR-VAL-06 |
| NFR-BE-P-04 | DB 조회는 파라미터화 + 인덱스(매장·세션·created_at) 활용, N+1 회피 | FD, SECURITY-05 |

## 2. 확장성 / 가용성 (Scalability / Availability)

| ID | 요구사항 | 근거 |
|---|---|---|
| NFR-BE-SC-01 | **단일 Uvicorn 워커, 수평 확장 없음**(로컬 단일 매장 MVP) | Q11=A |
| NFR-BE-SC-02 | 가용성 SLA·DR·페일오버·다중 인스턴스 = **N/A**(로컬 개발 배포). 프로덕션 전환 시 재검토 | Q11=A |

## 3. 신뢰성 (Reliability)

| ID | 요구사항 | 근거 |
|---|---|---|
| NFR-BE-R-01 | 다중 쓰기(채번 MAX+1 삽입 / soft-delete+총액재계산 / 이용완료 이력이관)는 **원자 트랜잭션**, 부분 성공 금지 | FD §7, BR-ORD-10, SECURITY-15 |
| NFR-BE-R-02 | 채번 경합은 `(store_id, order_date, order_seq)` UNIQUE + 쓰기 트랜잭션 직렬화로 방지, 위반 시 재시도/실패(fail closed) | BR-NUM-02/04 |
| NFR-BE-R-03 | 전역 에러 핸들러로 모든 예외를 표준 에러(`{error:{code,message,request_id}}`)로 정규화, 내부 스택/경로/DB 정보 미노출 | 계약 §1.3, SECURITY-15/09 |
| NFR-BE-R-04 | 외부 호출(DB)은 명시적 예외 처리 + 롤백 + 리소스 정리(fail closed) | FD §7, SECURITY-15 |
| NFR-BE-R-05 | SQLite 무결성: WAL 모드 + `foreign_keys=ON` + `busy_timeout`(5000ms)로 FK 강제·잠금 대기 | Q5=A |

## 4. 보안 (Security Baseline — Enabled/블로킹)

| ID | 요구사항 | 매핑 |
|---|---|---|
| NFR-BE-S-01 | JWT **매 요청** 서버측 검증(서명 HS256·`exp`·`iss`·`typ`), deny-by-default, IDOR 객체 소유권 검증 | SECURITY-08, BR-AUTHZ-01~07 |
| NFR-BE-S-02 | 비밀번호/PIN **bcrypt** 해시(passlib), 관리자 최소 8자·테이블 PIN 4~6자리(문서화 예외) | SECURITY-12, BR-AUTH-01/02 |
| NFR-BE-S-03 | 로그인 rate limit: **5회 실패 / 5분 → 429**, 잠금(cooldown) 5분(인메모리 슬라이딩 윈도우, `LoginAttempt`는 감사 기록) | SECURITY-12, BR-AUTH-03, Q8=A |
| NFR-BE-S-04 | 입력 검증 상한: **items ≤ 100, quantity 1..999, table_no ≤ 20, name ≤ 100, description ≤ 500, 요청 본문 ≤ 1MB** | SECURITY-05, BR-VAL-02/05, Q9=A |
| NFR-BE-S-05 | 파라미터화 쿼리만 사용(SQL 인젝션 방지), 사용자 문자열 정규화 | SECURITY-05, BR-VAL-01/07 |
| NFR-BE-S-06 | **CORS 허용 오리진 명시**(와일드카드 금지): env `CORS_ORIGINS`, 기본값 customer `http://localhost:5173` / admin `http://localhost:5174` | SECURITY-08, BR-AUTHZ-07, Q10=A |
| NFR-BE-S-07 | 구조화 JSON 로깅 + `request_id` 미들웨어, 민감정보(비번/토큰/PIN) 마스킹, 보안 이벤트 로깅 | SECURITY-03/13/14, BR-AUD-01~04 |
| NFR-BE-S-08 | 서명키·시드 비밀번호 등 자격증명은 **환경설정/시드 스크립트로 주입**(하드코딩 금지) | SECURITY-12, BR-AUTH-06 |
| NFR-BE-S-09 | 적용 가능한 API 보안 헤더(`X-Content-Type-Options: nosniff` 등) 미들웨어 설정. HTML 미제공(API-only)이라 CSP 등 대부분 N/A | SECURITY-04, 계약 §8 |
| NFR-BE-S-10 | 의존성 버전 고정(lock: `requirements.txt`/`uv.lock`), 취약점 스캔 CI 구성 | SECURITY-10 |
| — | SECURITY-01/02/06/07 = **N/A**(로컬 SQLite·HTTP·클라우드 IAM/네트워크 없음). 프로덕션 전환 시 재검토 | — |

## 5. 유지보수성 (Maintainability)

| ID | 요구사항 | 근거 |
|---|---|---|
| NFR-BE-M-01 | 정적 타입 검사 **mypy**, 린트/포맷 **ruff** | Q12=A |
| NFR-BE-M-02 | 계층 분리: Router / Service / Repository, 트랜잭션 경계는 Service | FD, Q3=A |
| NFR-BE-M-03 | OpenAPI(`/openapi.json`)를 계약 SSOT로 자동 노출, 계약 문서와 일치 유지(계약 §7/§9) | 계약 §7, Q1=A |
| NFR-BE-M-04 | 스키마는 기동 시 생성(create tables) + 시드 스크립트(Alembic 없음), 고정 스키마 MVP | Q4=A |

## 6. 테스트 (PBT Partial — NFR-T-01)

| ID | 요구사항 | 근거 |
|---|---|---|
| NFR-BE-T-01 | **pytest + Hypothesis**로 순수 계산/직렬화 라운드트립 PBT(FD BLM §8: 금액 계산 invariant, 주문번호·직렬화 라운드트립) | NFR-T-01, FD §8, Q12=A |
| NFR-BE-T-02 | **httpx TestClient** 통합 테스트: 인증·주문 생성/조회·상태변경·삭제·세션 setup/complete 핵심 경로 | Q12=A |
| NFR-BE-T-03 | 보안 경로 테스트: deny-by-default, typ 불일치(403), IDOR(404/403), rate limit(429), 총액 재검증(422) | SECURITY-08/12, Q12=A |
| NFR-BE-T-04 | CI에서 **lint(ruff) + typecheck(mypy) + test** 실행(전역 커버리지 정량 게이트 미설정, `shared`와 정합) | Q12=A |

## 7. 데이터 (Data)

| ID | 요구사항 | 근거 |
|---|---|---|
| NFR-BE-D-01 | 모든 타임스탬프는 **Asia/Seoul(+09:00)** ISO 8601 문자열 | NFR-D-03, 계약 §1.1 |
| NFR-BE-D-02 | 금액은 **정수 KRW**, ID는 응답 시 string 직렬화 | 계약 §1.1 |
| NFR-BE-D-03 | 주문 항목은 주문 시점 스냅샷(단가·명칭) 보존, soft-delete 유지(이력 일관) | 계약 §3.3, BR-ORD-09 |

---

## 8. Security Baseline 준수 요약 (NFR 단계)

**Compliant(반영/설계 확정)**: SECURITY-03(로깅) / 05(입력검증 상한 확정) / 08(인가·CORS·IDOR·JWT 매요청) / 09(하드닝·일반화 에러) / 11(보안설계) / 12(bcrypt·rate limit 수치 확정·서버측 만료) / 13(감사) / 15(전역 핸들러·fail closed).
**부분(N/A 항목 포함)**: SECURITY-04(API-only → 적용 가능한 헤더만, 나머지 N/A).
**Deferred→해소**: SECURITY-10(lock 파일 + 취약점 스캔 CI — 본 NFR에서 확정, Code Generation에서 실제 lock).
**N/A(문서화)**: SECURITY-01/02/06/07(로컬 배포·클라우드/네트워크 인프라 없음), SECURITY-14 알림 대시보드(보안 이벤트 로깅으로 대체), MFA(로컬 단일 매장 MVP).

> **블로킹 findings: 없음.** Q9=A로 SECURITY-05 입력 상한이 구체 수치로 확정되어 FD의 유보 사항 해소. 계약 §3(모델)·§4(클레임) 변경 없음.
