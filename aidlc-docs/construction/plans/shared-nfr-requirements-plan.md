# NFR Requirements Plan — Unit `shared`

> AI-DLC CONSTRUCTION / Unit 2 (`shared`) / NFR Requirements.
> 전제: Functional Design 승인 완료(PR #1). 산출물 = `aidlc-docs/construction/shared/functional-design/`.
> 적용 확장: **Security Baseline(Yes)**, **PBT(Partial — PricingUtil, NFR-T-01)**, Resiliency(No).
> `shared`는 배포 서비스가 아닌 **TS 라이브러리**이므로, NFR의 핵심은 **기술 스택/툴체인 선택**과 **유지보수·테스트·성능(번들)** 이다.

---

## 1. NFR 실행 체크리스트

- [ ] Step 1: Functional Design 분석 — **완료**
- [ ] Step 2: 본 계획서 작성 — **완료(본 파일)**
- [ ] Step 3: 명확화 질문 임베드 (아래 §3) — **완료, 답변 대기**
- [ ] Step 4: 계획서 저장 — **완료**
- [x] Step 5: 답변 수집 및 모호성 분석 (전부 추천안 A 선택 — 모호성 없음)
- [x] Step 6: 산출물 생성
  - [x] `construction/shared/nfr-requirements/nfr-requirements.md`
  - [x] `construction/shared/nfr-requirements/tech-stack-decisions.md`
- [x] Step 7: 완료 메시지 제시 (2-옵션)
- [ ] Step 8: 명시적 승인 대기
- [ ] Step 9: 승인 기록(audit.md) + aidlc-state.md 갱신

---

## 2. 사전 도출된 NFR (요구사항/계약에서 상속 — 재확인용)

| 영역 | shared 관련 NFR | 근거 |
|---|---|---|
| 성능 | 폴링 2초 주기 효율(불필요 폴링 억제), 번들 경량 | NFR-P-01, FD BR-PL-* |
| 사용성 | 터치 ≥44px, 한국어 라벨, KRW 포맷 | NFR-U-01/02/03 |
| 신뢰성 | 에러 정규화·fail closed·조용한 재시도 | NFR-S-06, FD BR-A/BR-PL |
| 보안 | 토큰/비밀번호 마스킹, XSS 이스케이프, 의존성 고정 | SECURITY-03/04/10 |
| 테스트 | PricingUtil PBT(P1~P6) | NFR-T-01 |
| 데이터 | 타임스탬프 Asia/Seoul 표시(변환 없음) | NFR-D-03 |

> 위는 이미 확정된 사항. 아래 질문은 **툴체인·구현 NFR**에 집중한다.

---

## 3. 명확화 질문 (`[Answer]:` 태그에 작성)

> **사용자 선택: 전부 추천안(★) = A** (2026-08-31).

### Q1. 테스트 프레임워크 + PBT 라이브러리
PricingUtil PBT(NFR-T-01)와 단위 테스트에 쓸 도구는?
- A. ★ **Vitest + fast-check** (Vite 생태계, TS/ESM 친화, PBT 표준)
- B. Jest + fast-check
- C. 기타

[Answer]: A

### Q2. 빌드/번들 도구 (라이브러리)
`shared` 패키지 빌드 방식은?
- A. ★ **tsup** (esbuild 기반, 라이브러리 번들·타입선언 간편)
- B. Vite (library mode)
- C. `tsc`만 사용(번들 없이 컴파일)
- D. 기타

[Answer]:

### Q3. 모듈 포맷 타깃
- A. ★ **ESM 전용** (customer/admin 모두 Vite/최신 번들러 소비 가정, 단순)
- B. ESM + CJS 듀얼
- C. 기타

[Answer]:

### Q4. React 버전 (peerDependency 범위, Q9=A)
- A. ★ **React 18** (`peerDependencies: react ^18`)
- B. React 19
- C. 기타/범위 지정

[Answer]:

### Q5. TypeScript 엄격도
- A. ★ **strict: true** (+ `noUncheckedIndexedAccess` 등 강화)
- B. 기본 strict만
- C. 기타

[Answer]:

### Q6. 성능/번들 예산 (성능 NFR)
`shared`에 번들 사이즈 예산을 둘까요?
- A. ★ **soft 예산** — 순수 TS 코어(types/pricing/api)는 의존성 0 유지, UI/hooks만 React 소비. 정량 상한은 두지 않되 불필요 의존성 추가 금지
- B. hard 예산(예: gzip <20KB) + 측정 게이트
- C. 예산 없음
- D. 기타

[Answer]:

### Q7. 린트/포맷
- A. ★ **ESLint + Prettier** (+ typescript-eslint)
- B. Biome (린트+포맷 통합)
- C. 없음
- D. 기타

[Answer]:

### Q8. OpenAPI 타입 생성 파이프라인 (Q1=B FD 결정 운영화)
`openapi-typescript` 실행/스냅샷 관리는?
- A. ★ **커밋된 `openapi.json` 스냅샷 + npm 스크립트(`gen:types`)로 재생성**, 생성물 `src/types/generated/`에 커밋. 백엔드 계약 변경 시 스냅샷 갱신(계약 §9)
- B. 빌드 시 backend 라이브 `/openapi.json`에서 매번 생성(백엔드 가동 필요)
- C. 기타

[Answer]:

### Q9. 테스트 커버리지/CI 목표
- A. ★ **PricingUtil 100%(PBT 포함) + ApiClient/PollingHook 핵심 경로 단위테스트**, CI에서 lint+typecheck+test 실행(정량 전역 커버리지 게이트는 미설정)
- B. 전역 커버리지 임계값 설정(예: 80%)
- C. 최소한만(핵심 함수만)
- D. 기타

[Answer]:

---

## 4. 다음 단계
답변 작성 후 알려주시면, 모호성 점검 후 `nfr-requirements.md`·`tech-stack-decisions.md`를 생성하고 2-옵션 완료 메시지로 승인을 요청합니다. ("전부 추천안(★)"도 가능)
