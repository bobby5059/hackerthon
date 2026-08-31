# Code Generation Summary — Unit `shared`

> `@table-order/shared` 코드 생성 결과 요약(문서). 실제 코드는 `frontend/shared/`.
> Greenfield. 계획서 `../../plans/shared-code-generation-plan.md`의 G1~G8 실행 결과.
> **검증 상태(2026-08-31, 로컬)**: typecheck ✅ · lint ✅ · test 43/43 ✅ · build ✅ · codegen drift 0 ✅.

---

## 1. 생성 파일 (created)

### 툴체인 / 설정 (G1)
- `frontend/shared/package.json` — `@table-order/shared`, ESM, 5개 서브경로 exports, react/react-dom ^18 peerDeps, devDeps 버전 고정(SECURITY-10), scripts
- `frontend/shared/tsconfig.json` — strict + noUncheckedIndexedAccess + exactOptionalPropertyTypes
- `frontend/shared/tsup.config.ts` — ESM, dts, 서브경로별 엔트리, react external
- `frontend/shared/vitest.config.ts` + `vitest.setup.ts` — pricing 100% 커버리지 게이트
- `frontend/shared/.eslintrc.cjs` — `no-console: error`(SECURITY-03 무로깅 강제)
- `frontend/shared/.prettierrc`, `.prettierignore`, `.gitignore`
- `frontend/shared/scripts/gen-types.mjs` — openapi-typescript 래퍼(MP-01)
- `frontend/shared/README.md` — 사용법/서브경로/개발 스크립트

### Types 계층 (G2)  → C1~C5 / A1~A3
- `frontend/shared/openapi.json` — 계약 v1.0 스냅샷(커밋)
- `frontend/shared/src/types/generated/schema.ts` — **자동 생성물**(openapi-typescript 7.4.0 실제 출력, 편집 금지)
- `frontend/shared/src/types/index.ts` — 보강 레이어: 도메인 타입 별칭, `OrderStatus`, `ORDER_STATUS_LABELS`, `ApiErrorCode`, 요청/응답 래퍼

### Pricing 계층 (G3/G3T)  → C3~C4
- `frontend/shared/src/pricing/index.ts` — `lineTotal`, `cartTotal` (정수 KRW, O(n))
- `frontend/shared/src/pricing/pricing.pbt.test.ts` — **PBT** P1~P6 (fast-check) + 예제

### API 계층 (G4/G4T)  → C/A 전반
- `frontend/shared/src/api/errors.ts` — `ApiError` 클래스 + `normalizeError`/`errorFromResponse` 단일 매핑 모듈(MP-02)
- `frontend/shared/src/api/client.ts` — `createApiClient` 팩토리(Q4): 10s AbortController 타임아웃+signal 병합(RP-01), 무재시도(RP-02), getToken 헤더 주입(SP-02), onError(SP-01), onUnauthorized fail-closed(RP-04)
- `frontend/shared/src/api/index.ts` — 공개 export
- `frontend/shared/src/api/api.test.ts` — 14 테스트(토큰/쿼리/204/에러/401/네트워크/타임아웃)

### Hooks 계층 (G5/G5T)  → C5, A2
- `frontend/shared/src/hooks/usePolling.ts` — 2s 폴링, useRef/useCallback/useReducer(PP-02), visibility pause/resume(PP-04/RP-03), 조용한 재시도, cleanup(clearInterval+abort), `lastServerTime`
- `frontend/shared/src/hooks/index.ts` — export
- `frontend/shared/src/hooks/usePolling.test.tsx` — 8 테스트(주기/가시성/에러보존/비활성/ref안정/언마운트/refetch)

### UI 계층 (G6/G6T)  → 전 화면 공통
- `frontend/shared/src/ui/tokens.ts` — 디자인 토큰 + `safeImageUrl`(SP-03 XSS-safe)
- `frontend/shared/src/ui/{Button,Card,Modal,Spinner,ErrorBanner}.tsx` — 무상태 controlled(MP-03), 44px 터치 타깃, `data-testid`, Modal focus-trap/ESC/overlay/scroll-lock, ErrorBanner role=alert, Spinner role=status
- `frontend/shared/src/ui/index.ts` — export
- `frontend/shared/src/ui/ui.test.tsx` — 11 테스트(렌더/접근성/XSS-safe)

---

## 2. 스토리 커버리지
- 전 서버통신(C1~C5, A1~A3): Types + ApiClient 제공
- 폴링(C5, A2): usePolling
- 가격(C3~C4): PricingUtil
- 상태 라벨(C5-S2, A2-S4): ORDER_STATUS_LABELS

## 3. NFR / 보안 준수
| 항목 | 반영 |
|---|---|
| RP-01 타임아웃 | `client.ts` 10s AbortController + signal 병합 |
| RP-02 무재시도 | mutation/GET 자동재시도 없음(폴링만) |
| RP-03/PP-04 폴링 | `usePolling` visibility pause + silent retry + cleanup |
| RP-04 fail-closed | 401/TOKEN_EXPIRED → onUnauthorized |
| PP-02 훅 안정성 | useRef/useCallback/useReducer |
| MP-01 드리프트 | `gen:types` + `git diff --exit-code`(로컬 0 diff 확인) |
| MP-02 에러 단일화 | `normalizeError` 단일 모듈 |
| MP-03 UiKit | 무상태 controlled + a11y + data-testid |
| SECURITY-03 무로깅 | `no-console: error` lint + onError 위임 |
| SECURITY-04 XSS | React 이스케이프, `dangerouslySetInnerHTML` 미사용, `safeImageUrl` |
| SECURITY-08 자격증명 | 토큰 미저장, getToken 콜백 |
| SECURITY-10 공급망 | 런타임 의존성 0, devDeps 버전 고정 |
| PBT (Partial) | PricingUtil P1~P6, pricing 100% 커버리지 게이트 |

## 4. 계획 대비 편차(의도적)
- **CSS Module → 인라인 스타일 객체(tokens.ts)**: ESM 빌드 무설정성·타입 안정성 확보를 위해. 시각 토큰은 `tokens.ts`에 중앙화. 접근성/`data-testid`/터치 타깃 요건은 그대로 충족. 추후 CSS Module 마이그레이션 가능.
- **CI YAML**: NFR-design MP-01의 드리프트 게이트는 로컬 스크립트로 검증 완료. GitHub Actions 워크플로 파일 작성은 **Build & Test 단계**로 이관(계획 G8 명시).

## 5. 다음 단계
per-unit loop(shared) 완료. 전체 유닛 완료 후 **Build & Test** 단계에서 CI 구성 + 통합/계약 테스트.
