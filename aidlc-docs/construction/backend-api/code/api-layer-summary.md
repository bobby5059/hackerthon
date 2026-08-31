# API Layer Summary — backend-api

> AI-DLC CONSTRUCTION / Unit 1 (backend-api) / Code Generation / Step 10 산출물 요약
> 근거: integration-contract.md v1.0 §2.6/§3/§4, nfr-design(logical-components), Security Baseline

## 1. 라우터 인벤토리 (계약 §2.6 정합)

| 파일 | 엔드포인트 | 인증(typ) | 서비스 | 성공 코드 |
|---|---|---|---|---|
| `auth.py` | `POST /api/admin/login` | 🔓 | auth_service | 200 |
| `auth.py` | `POST /api/table/login` | 🔓 | auth_service | 200 |
| `menu.py` | `GET /api/menu` | 🔑T/A | menu_service | 200 |
| `menu.py` | `GET /api/menu/{menu_id}` | 🔑T/A | menu_service | 200 |
| `order.py` | `POST /api/orders` | 🔑T | order_service | 201 |
| `order.py` | `GET /api/orders` | 🔑T | order_service | 200 |
| `order.py` | `PATCH /api/orders/{order_id}/status` | 🔑A | order_service | 200 |
| `order.py` | `DELETE /api/orders/{order_id}` | 🔑A | order_service | 200 |
| `table.py` | `POST /api/tables/{table_id}/setup` | 🔑A | session_service | 200 |
| `table.py` | `GET /api/tables/dashboard` | 🔑A | session_service | 200 |
| `table.py` | `POST /api/tables/{table_id}/complete` | 🔑A | session_service | 200 |
| `history.py` | `GET /api/history` | 🔑A | history_service | 200 |

`main.py`의 `/health`(🔓)는 계약 외 운영용.

## 2. 인증·인가 (deny-by-default)

- 모든 보호 라우트는 FastAPI 의존성으로 인증을 **명시 선언**한다(`require_admin`/`require_table`/`require_any`). 의존성 누락 라우트 없음.
- `security/deps.py`가 `get_claims`(Authorization Bearer 파싱·검증) → typ별 가드로 이어진다. typ 불일치 시 `FORBIDDEN`(403), 토큰 부재/무효/만료 시 `UNAUTHORIZED`(401)/`TOKEN_EXPIRED`.
- 관리자 라우트는 `store_id` 스코프를 principal에서 취득 → 서비스로 전달(IDOR 차단, SECURITY-08).

## 3. 요청/응답 계약 정합 (§3)

- 요청/응답 모델은 `app/schemas/*`의 Pydantic v2 모델(계약 §3 미러). 응답 모델을 `response_model`로 지정하여 OpenAPI가 계약과 일치.
- 필드 규약: 모든 ID는 문자열 직렬화, 금액은 정수 KRW, 타임스탬프는 ISO 8601 `+09:00`.
- 폴링 응답(`GET /api/orders`, dashboard)은 `server_time` 포함.
- 페이지네이션: `page≥1`, `size 1..100`(초과 시 422), 응답에 `page_meta`.

## 4. 에러 계약 (§1.3, SECURITY-15)

전역 핸들러(`errors.py`)가 모든 에러를 표준 형식으로 통일:

```json
{ "error": { "code": "<ERROR_CODE>", "message": "<메시지>", "request_id": "<uuid>" } }
```

| 상황 | 코드 | HTTP |
|---|---|---|
| 인증 실패/토큰 무효 | `UNAUTHORIZED` | 401 |
| 토큰 만료 | `TOKEN_EXPIRED` | 401 |
| typ 불일치/권한 없음 | `FORBIDDEN` | 403 |
| 리소스 없음/IDOR 은닉 | `NOT_FOUND` | 404 |
| 세션 종료/재-setup/완료 차단 | `SESSION_CLOSED` | 409 |
| 스키마 검증 실패 | `VALIDATION_ERROR` | 400 |
| 시맨틱 검증(미존재 메뉴 등) | `VALIDATION_ERROR` | 422 |
| 총액 불일치 | `TOTAL_MISMATCH` | 422 |
| 빈 주문 | `ORDER_EMPTY` | 400 |
| rate limit | `RATE_LIMITED` | 429 |
| 미처리 예외 | `INTERNAL_ERROR` | 500(fail-closed) |

RequestValidationError → 400 `VALIDATION_ERROR`로 변환, 일반 예외 → 500(스택 미노출).

## 5. 미들웨어 체인 (main.py, logical-components §2)

추가 순서(Starlette: 나중 추가가 아우터):
`SecurityHeaders → BodySizeLimit → CORS → Logging → RequestId` 순으로 add → 실행 시 RequestId가 최외곽.
- RequestId: 요청마다 uuid 생성·contextvar 전파·`X-Request-Id` 응답 헤더.
- Logging: 요청/응답 구조화 JSON + 민감필드 마스킹.
- CORS: env 오리진만 허용(와일드카드 제거).
- BodySize: 본문 >1MB 차단(C5).
- SecurityHeaders: `X-Content-Type-Options: nosniff` 등.

## 6. 준수 요약
- 계약 §2/§3/§4와 경로·모델·클레임 일치(OpenAPI 진실 원천).
- deny-by-default, IDOR 은닉, typ 분리, 표준 에러 — 전 라우트 적용.
