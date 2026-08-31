# Tech Stack Decisions — Unit `shared`

> `shared` TS 라이브러리의 툴체인 결정. 사용자 답변: **Q1~Q9 전부 추천안(A)** (2026-08-31).
> 확장: Security Baseline(Yes), PBT Partial(fast-check for PricingUtil).

---

## 1. 결정 요약

| # | 항목 | 결정 | 비고 |
|---|---|---|---|
| Q1 | 테스트/PBT | **Vitest + fast-check** | ESM/TS 친화, PBT 표준 |
| Q2 | 빌드 도구 | **tsup** (esbuild 기반) | 라이브러리 번들 + `.d.ts` 자동 |
| Q3 | 모듈 포맷 | **ESM 전용** | 소비 앱(Vite) 최신 번들러 가정 |
| Q4 | React | **peerDependency `react ^18`** (+ `react-dom ^18`) | Hook/UiKit만 사용 |
| Q5 | TypeScript | **strict: true** + `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` | |
| Q6 | 성능/번들 | **soft 예산** — 코어 의존성 0, 불필요 의존성 금지 | 정량 상한 없음 |
| Q7 | 린트/포맷 | **ESLint + Prettier** (+ typescript-eslint) | |
| Q8 | OpenAPI 생성 | **커밋 스냅샷 + `gen:types` 스크립트** | `openapi-typescript` |
| Q9 | 테스트 목표 | PricingUtil 100% + 핵심경로, **CI: lint+typecheck+test** | 전역 커버리지 게이트 없음 |

---

## 2. 의존성 (버전 고정 — SECURITY-10)

**dependencies (런타임)**: 없음(코어 순수 TS). *네이티브 fetch 사용(Q2=A) → HTTP 라이브러리 무의존.*

**peerDependencies**
```
react ^18
react-dom ^18
```

**devDependencies (예정)**
```
typescript, vite/tsup, vitest, @vitest/coverage-v8, fast-check,
eslint, @typescript-eslint/*, prettier, openapi-typescript,
@types/react, @types/react-dom
```
> 정확한 버전은 Code Generation에서 lock 파일로 고정. 취약점 스캔 구성(SECURITY-10)은 CI 설정 시 포함.

---

## 3. 패키지 구성 (모노레포 npm workspace, FD Q10=A)

```
frontend/shared/
├── package.json          # name: @table-order/shared, type: module, exports 맵
├── tsconfig.json         # strict
├── tsup.config.ts        # ESM, dts, entry per subpath
├── vitest.config.ts
├── .eslintrc / .prettierrc
├── openapi.json          # backend 계약 스냅샷 (커밋, SECURITY-10)
├── scripts/gen-types     # openapi-typescript 실행 (npm run gen:types)
└── src/
    ├── types/            # generated/schema.ts (자동) + index.ts (보강 레이어)
    ├── pricing/          # PricingUtil (+ pricing.pbt.test.ts)
    ├── api/              # createApiClient, ApiError
    ├── hooks/            # usePolling
    └── ui/               # Button/Card/Modal/Spinner/ErrorBanner (+ *.module.css)
```

**package.json exports (서브경로 — FD Q10=A)**
```jsonc
"exports": {
  "./types":   "./dist/types/index.js",
  "./pricing": "./dist/pricing/index.js",
  "./api":     "./dist/api/index.js",
  "./hooks":   "./dist/hooks/index.js",
  "./ui":      "./dist/ui/index.js"
}
```

---

## 4. npm 스크립트 (예정)
```
gen:types   openapi-typescript openapi.json -o src/types/generated/schema.ts
build       tsup
test        vitest run
test:watch  vitest
typecheck   tsc --noEmit
lint        eslint . && prettier --check .
```

---

## 5. 근거·트레이드오프
- **네이티브 fetch(Q2=A)**: 런타임 의존성 0 → NFR-SH-P-02 충족. 구형 브라우저 폴리필 불필요(태블릿 최신 크롬 가정).
- **ESM 전용(Q3=A)**: 소비 앱 2개 모두 Vite로 가정 → CJS 불요, 빌드 단순. 추후 CJS 필요 시 tsup에 포맷 추가로 확장 가능.
- **tsup(Q2=A)**: 라이브러리 다중 엔트리·타입선언 자동화가 vite lib mode보다 간결.
- **커밋 스냅샷(Q8=A)**: 백엔드 미가동 상태에서도 shared 독립 개발/CI 가능. 계약 변경은 §9(계약) 절차로 스냅샷 갱신.

---

## 6. 다음 단계
본 결정을 근거로 **NFR Design(shared)** 에서 툴체인·계층을 설계에 반영하고, 이후 **Code Generation(shared)** 에서 실제 코드/설정/테스트를 생성한다.
