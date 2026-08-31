# NFR Requirements — Unit `shared`

> `shared`는 TS 라이브러리 유닛. 본 문서는 이 유닛에 적용되는 비기능 요구사항을 확정한다.
> 기술 스택 결정은 `tech-stack-decisions.md` 참조. 확장: Security Baseline(Yes), PBT(Partial), Resiliency(No).

---

## 1. 성능 (Performance)

| ID | 요구사항 | 근거 |
|---|---|---|
| NFR-SH-P-01 | PollingHook 기본 주기 2000ms, 탭 비활성 시 폴링 정지(불필요 네트워크/CPU 억제) | NFR-P-01, FD BR-PL-01/02 |
| NFR-SH-P-02 | 순수 코어(`types`/`pricing`/`api`)는 **런타임 의존성 0** 유지(경량, 트리셰이킹) — soft 예산(Q6=A) | Q6=A |
| NFR-SH-P-03 | PricingUtil은 O(n) 단일 순회, 부수효과 없음(순수) | FD §1 |

## 2. 사용성 (Usability)

| ID | 요구사항 | 근거 |
|---|---|---|
| NFR-SH-U-01 | UiKit 터치 대상 ≥44×44px | NFR-U-02 |
| NFR-SH-U-02 | 한국어 라벨(OrderStatus), KRW 천단위 포맷 제공 | NFR-U-01/03 |
| NFR-SH-U-03 | 타임스탬프는 Asia/Seoul(+09:00) 문자열 표시, 타임존 재변환 없음 | NFR-D-03 |

## 3. 신뢰성 (Reliability)

| ID | 요구사항 | 근거 |
|---|---|---|
| NFR-SH-R-01 | 모든 HTTP 실패를 `ApiError`로 정규화, 네트워크 실패 포함(fail closed) | NFR-S-06, FD BR-A-03/04 |
| NFR-SH-R-02 | 폴링 실패는 조용히 재시도, 마지막 오류만 노출, 데이터 보존 | FD BR-PL-03 |
| NFR-SH-R-03 | 언마운트/비활성 시 인터벌 정리 + 진행 요청 abort(누수 없음) | FD BR-PL-04 |

## 4. 보안 (Security Baseline)

| ID | 요구사항 | 매핑 |
|---|---|---|
| NFR-SH-S-01 | 토큰·비밀번호 로깅/노출 금지(마스킹) | SECURITY-03 |
| NFR-SH-S-02 | React 기본 이스케이프 의존, `dangerouslySetInnerHTML` 금지 | SECURITY-04 |
| NFR-SH-S-03 | 401/TOKEN_EXPIRED 시 `onUnauthorized` 후 throw(deny-by-default 협조) | SECURITY-08 |
| NFR-SH-S-04 | 의존성 버전 고정(lock 파일), openapi 스냅샷 신뢰 출처 고정 | SECURITY-10 |
| — | SECURITY-01/06/07/14 = **N/A** (인프라/백엔드 사안, 라이브러리 무관) | — |

## 5. 유지보수성 (Maintainability)

| ID | 요구사항 | 근거 |
|---|---|---|
| NFR-SH-M-01 | TypeScript `strict: true`(+ 강화 옵션) | Q5=A |
| NFR-SH-M-02 | ESLint + Prettier로 스타일/품질 일관성 | Q7=A |
| NFR-SH-M-03 | 서브경로 export로 관심사 분리, 순수 계층/React 계층 경계 유지 | FD Q9/Q10 |
| NFR-SH-M-04 | OpenAPI 타입은 `gen:types` 스크립트로 재현 가능하게 생성, 스냅샷 커밋 | Q8=A |

## 6. 테스트 (PBT Partial — NFR-T-01)

| ID | 요구사항 | 근거 |
|---|---|---|
| NFR-SH-T-01 | PricingUtil 속성 기반 테스트(P1~P6) fast-check로 구현, 라인 커버리지 100% | NFR-T-01, Q1/Q9=A |
| NFR-SH-T-02 | ApiClient 핵심 경로(성공/에러 정규화/401 콜백/네트워크 실패) 단위테스트 | Q9=A |
| NFR-SH-T-03 | usePolling 핵심 경로(주기 fetch/가시성 정지·재개/정리) 단위테스트 | Q9=A |
| NFR-SH-T-04 | CI에서 lint + typecheck + test 실행(전역 커버리지 정량 게이트 미설정) | Q9=A |

## 7. 가용성/확장성
- **N/A** — `shared`는 실행 서비스가 아님(가동시간·스케일링 대상 아님). 소비 앱이 담당.

---

## 8. Security Baseline 준수 요약 (NFR 단계)
반영: SECURITY-03/04/08/10. N/A: SECURITY-01/02/06/07/14(인프라). 부분(후속 Code): SECURITY-05는 서버 책임이나 shared는 타입 계약으로 협조, SECURITY-15는 ApiClient 에러 정규화로 반영. **블로킹 findings 없음.**
