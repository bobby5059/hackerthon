# Code Generation Summary — backend-api

> AI-DLC CONSTRUCTION / Unit 1 (backend-api) / Code Generation / Step 13 종합
> 근거: backend-api-code-generation-plan.md, integration-contract v1.0, functional-design/*, nfr-requirements/*, nfr-design/*

## 1. 개요

Unit 1(backend-api)의 전체 애플리케이션 코드·테스트·설정·시드·문서를 승인된 계획(Step 1~13)에 따라 생성 완료했다. 코드 위치는 워크스페이스 루트의 `backend/`, 문서 요약은 `aidlc-docs/construction/backend-api/code/`.

## 2. 생성 파일 인벤토리

### 2.1 프로젝트 설정 (Step 1~2)
| 파일 | 책임 |
|---|---|
| `backend/pyproject.toml` | 프로젝트 메타·런타임/dev deps·ruff/mypy/pytest 설정 |
| `backend/requirements.txt` / `requirements-dev.txt` | 버전 lock(SECURITY-10) |
| `backend/.env.example` | 전체 env 변수 + 주석 |
| `backend/.gitignore` | `*.db`/`.env`/`__pycache__` 등 |
| `backend/README.md` | 설치·env·기동·시드·테스트 가이드 |
| `app/config.py` | Pydantic Settings(env 로딩·검증) |
| `app/time_utils.py` | Asia/Seoul now/ISO8601(+09:00) 헬퍼 |
| `app/logging_config.py` | JSON 로깅 + request_id + 민감필드 마스킹 |

### 2.2 DB 계층 (Step 3)
| 파일 | 책임 |
|---|---|
| `app/db/engine.py` | Engine + connect 훅 PRAGMA(WAL/FK/busy_timeout) |
| `app/db/models.py` | 전 엔티티 ORM(CHECK·UNIQUE·인덱스) |
| `app/db/schema.py` | 기동 시 create_all |
| `app/db/session.py` | get_db 요청 세션 + retry_on_write_conflict |
| `app/db/seed.py` | 단일 매장 멱등 시드 |

### 2.3 스키마 (Step 5)
`app/schemas/`: common, auth, menu, order, table, history — 계약 §3 미러 + 입력 상한(Q9).

### 2.4 보안 (Step 6)
`app/security/`: hashing(bcrypt), jwt(HS256 typ/exp/iss), ratelimit(인메모리 슬라이딩 윈도우), deps(deny-by-default 가드).

### 2.5 미들웨어·에러 (Step 7)
`app/errors.py`(예외 계층 + 전역 핸들러 3종), `app/middleware/`: request_id, logging, body_size, security_headers.

### 2.6 리포지토리 (Step 8)
`app/repositories/`: store, table, menu, order, history, audit, ids. → `repository-layer-summary.md`

### 2.7 서비스 (Step 9)
`app/services/`: auth, menu, order, session, history + 순수 함수 pricing/order_number. → `business-logic-summary.md`

### 2.8 라우터·앱 (Step 10~11)
`app/routers/`: auth, menu, order, table, history. `app/main.py`(앱 조립·미들웨어 체인·라우터 등록·create_all). → `api-layer-summary.md`

### 2.9 테스트 (Step 12)
- 단위(PBT): `test_pricing_pbt.py`, `test_order_number_pbt.py`, `test_serialization_pbt.py`
- 통합: `test_auth.py`, `test_order_flow.py`, `test_session_flow.py`, `test_security.py`
- `conftest.py`: 임시 DB·시드·TestClient·토큰 픽스처
> 실행은 Build & Test 단계. 본 단계는 생성만.

## 3. 계약 정합성 요약
- **§2.6 엔드포인트 12개**: 전부 구현(경로·메서드·인증 typ 일치). `/health`만 계약 외 운영용.
- **§3 공유 모델**: Pydantic v2 모델로 미러, `response_model` 지정 → OpenAPI가 계약과 일치. 가용성 필드 없음(Q10=A), `has_new` 항상 포함/false(Q9=A).
- **§4 JWT 클레임**: typ/store_id/exp/iss(+table_id/session_id) — 변경 없음.
- **§1.3 표준 에러**: `{error:{code,message,request_id}}` 전역 통일.

## 4. Security Baseline 준수 (블로킹 — 결함 없음)
| 항목 | 반영 |
|---|---|
| deny-by-default | 전 보호 라우트 인증 의존성 명시 |
| IDOR 차단 | store_id 스코프 + 404 은닉 |
| typ 분리 | require_admin/require_table 가드(403) |
| bcrypt | passlib, cost=env |
| rate limit | 5회/300s → 429 + 쿨다운 |
| 파라미터화 쿼리 | ORM 전용, raw SQL 없음 |
| 구조화 로깅·마스킹 | logging_config + 미들웨어 |
| 전역 에러·fail-closed | errors.py 3핸들러, 500 스택 미노출 |
| 감사 로깅 | audit_repo + 서비스 |
| 버전 lock | requirements.txt |

## 5. PBT 준수 (Partial)
순수 계산(pricing line/total), 채번 포맷 라운드트립, Pydantic 직렬화 라운드트립(스냅샷 보존, NFR-T-01) — Hypothesis 테스트 생성 완료.

## 6. 검증 상태
- 시스템 Python(3.9)에는 프로젝트 deps 미설치 → `py_compile`로 전 모듈 문법 검증 통과(`from __future__ import annotations`로 3.12 타입 문법 호환).
- 실제 테스트 실행·정적 분석(ruff/mypy)은 Build & Test 단계에서 수행.

## 7. 계약 변경 여부
- 계약 §3(모델)·§4(클레임) **변경 없음**. backend-api는 제공자로서 계약 v1.0을 그대로 구현.
