# NFR Design Patterns — Unit `shared`

> NFR Requirements(`../nfr-requirements/`)를 **설계 패턴**으로 구체화한다. 사용자 답변 Q1~Q8=A.
> `shared`는 TS 라이브러리이므로 인프라 패턴(큐/캐시/서킷브레이커)이 아니라 **클라이언트측 신뢰성·성능·보안 패턴**에 집중한다.

---

## 1. Resilience 패턴

### RP-01 요청 타임아웃 (Q1=A)
- 모든 `ApiClient` 요청은 **기본 10,000ms 타임아웃**. `AbortController`로 구현.
- 호출측 `signal`이 주어지면 내부 타임아웃 signal과 **병합**(둘 중 하나라도 abort 시 취소).
- 초과 시 `ApiError(code:"NETWORK_ERROR", httpStatus:0, message:"요청 시간이 초과되었습니다.")`.

### RP-02 재시도 정책 (Q2=A)
- **shared는 자동 재시도를 하지 않는다.** 근거: mutation(주문 생성 등) 멱등성 미보장 → 중복 위험(계약 §2.3 fail closed).
- 주기 재시도는 **PollingHook만** 담당(다음 주기 자연 재시도, RP-03).
- 소비 앱이 필요 시 명시적으로 `refetch()`/재호출.

### RP-03 폴링 조용한 재시도 + 정리 (FD BR-PL-03/04)
- 폴링 tick 실패 → 데이터 보존, `error`에 마지막 오류 저장, 다음 주기 재시도(사용자 방해 없음).
- 탭 비활성 시 인터벌 정지, 재활성 시 즉시 1회 + 재개(Q5 정책).
- 언마운트 시 인터벌 clear + `AbortController.abort()` → 누수/경합 방지.

### RP-04 Fail-closed 인증 (SECURITY-08)
- 401 또는 `TOKEN_EXPIRED` 수신 → `onUnauthorized()` 콜백 호출 후 `ApiError` throw. 소비 앱이 폴링 중단·재로그인 유도.

---

## 2. Performance 패턴

### PP-01 계층 분리 & 트리셰이킹 (Q4/서브경로 export)
- 순수 TS 계층(`types`/`pricing`/`api`)은 React 무의존 → 소비 앱이 필요한 서브경로만 임포트.
- ESM 전용 + `sideEffects:false`(가능 범위)로 번들러 트리셰이킹 극대화.

### PP-02 훅 참조 안정성 (Q5=A)
- `usePolling` 내부:
  - 최신 `fetchFn`을 `useRef`에 보관 → **fetchFn 아이덴티티 변경이 인터벌 재시작을 유발하지 않음**(안정적 폴링).
  - `refetch`는 `useCallback`으로 안정화.
  - 상태는 단일 객체/`useReducer`로 묶어 부분 갱신 리렌더 최소화.
- 인터벌은 `intervalMs`/`enabled` 변경 시에만 재구성.

### PP-03 순수 계산 효율 (NFR-SH-P-03)
- PricingUtil은 단일 O(n) reduce, 메모이제이션 불필요(호출 저렴). 소비 앱이 필요 시 자체 메모.

### PP-04 폴링 부하 억제 (NFR-SH-P-01)
- 기본 2000ms, 탭 비활성 정지(RP-03). 다중 훅 인스턴스는 각자 독립(전역 스케줄러는 MVP 범위 외 — 소비 앱이 화면당 1개 사용 권장).

---

## 3. Security 패턴 (Security Baseline)

### SP-01 무로깅 + onError (Q3=A / SECURITY-03)
- 라이브러리는 `console`에 쓰지 않는다. 관측은 선택적 `onError(err: ApiError)` 콜백으로 소비 앱에 위임.
- shared가 전달하는 `ApiError`에는 토큰·비밀번호 등 민감정보를 포함하지 않는다(요청 헤더/바디 원본 미첨부).

### SP-02 자격증명 미보유 (SECURITY-08)
- shared는 토큰을 저장/영속화하지 않는다. `getToken()` 콜백으로 매 요청 조회만. 저장·만료는 소비 앱(localStorage) 책임.

### SP-03 XSS-safe 렌더 (SECURITY-04)
- UiKit은 React 기본 이스케이프에만 의존. `dangerouslySetInnerHTML` 금지. URL(`image_url`) 렌더 시 `http(s)` 스킴만 허용(javascript: 차단).

### SP-04 공급망 무결성 (SECURITY-10)
- 런타임 의존성 0(네이티브 fetch). devDeps 버전 고정(lock). `openapi.json` 스냅샷은 신뢰된 backend 산출물만, 드리프트 CI 체크(RP는 아니고 아래 MP-01).

---

## 4. Maintainability 패턴

### MP-01 codegen 드리프트 게이트 (Q6=A)
- CI: `npm run gen:types` 재실행 후 `git diff --exit-code src/types/generated` → 스냅샷과 생성 타입 불일치 시 실패. 스냅샷 갱신은 계약 §9 절차의 PR로만.

### MP-02 에러 매핑 단일화 (Q7=A)
- `normalizeError(input): ApiError` 단일 내부 모듈이 (HTTP 상태 | `{error:{...}}` envelope | 네트워크/파싱 실패)를 `ApiError`로 매핑. ApiClient는 이 모듈만 사용 → 일관성·테스트 용이(단위테스트 표적).

### MP-03 무상태 controlled UiKit (Q8=A)
- UiKit 컴포넌트는 상태를 소유하지 않음(부모 제어). Modal은 focus-trap·ESC·오버레이 닫기 접근성 포함. 모든 인터랙티브 요소 `data-testid`.

---

## 5. Scalability
- **N/A** — 라이브러리는 스케일 단위가 아님. 부하/동시성은 backend-api·소비 앱 책임.

---

## 6. NFR ↔ 패턴 추적

| NFR | 패턴 |
|---|---|
| NFR-SH-R-01/02/03 | RP-01/02/03/04, MP-02 |
| NFR-SH-P-01/02/03 | PP-01/02/03/04 |
| NFR-SH-S-01~04 | SP-01/02/03/04 |
| NFR-SH-M-01~04 | MP-01/02/03, PP-01 |
| NFR-SH-T-01~04 | MP-02(테스트 표적), 아래 logical-components 테스트 하니스 |
