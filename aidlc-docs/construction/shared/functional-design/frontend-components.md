# Functional Design — Frontend Components & Hooks — Unit `shared`

> `shared`가 제공하는 **재사용 React 구성요소(UiKit)** 와 **훅(PollingHook)** 의 계층·props·상태·인터랙션을 정의한다.
> React=peerDependency(Q9=A). 스타일=CSS Modules + 디자인 토큰(Q8=A). 패키지=서브경로 export(Q10=A).
> 상세 로직/알고리즘은 `business-logic-model.md`, 규칙은 `business-rules.md` 참조.

---

## 1. 패키지 export 지도 (Q10=A)

```
@table-order/shared
├── /types     → 도메인·응답·에러 타입 (순수 TS)         [domain-entities.md]
├── /pricing   → lineTotal, cartTotal, formatKRW         (순수 TS)
├── /api       → createApiClient, ApiClient, ApiError    (순수 TS)
├── /hooks     → usePolling                              (React)
└── /ui        → Button, Card, Modal, Spinner, ErrorBanner (React + CSS Modules)
```
- 순수 TS 계층(`/types`,`/pricing`,`/api`)은 React 없이 임포트 가능(테스트·backend 타입 검증 용이).
- React 계층(`/hooks`,`/ui`)만 React peerDependency 요구.

---

## 2. UiKit 컴포넌트 (Q8=A — MVP 5종)

### 2.1 컴포넌트 계층
```
UiKit (프레젠테이션, 상태 최소 — controlled 지향)
├── Button        (터치 ≥44×44px, variant/size/loading/disabled)
├── Card          (컨테이너 — 메뉴 카드, 대시보드 테이블 카드에 사용)
├── Modal         (오버레이 — 주문 상세, 삭제/이용완료 확인)
├── Spinner       (로딩 인디케이터)
└── ErrorBanner   (일반화 오류 표시)
```

### 2.2 Props / 상태 정의

**Button**
```ts
interface ButtonProps {
  variant?: "primary" | "secondary" | "danger";  // danger=삭제/이용완료
  size?: "md" | "lg";                              // 최소 44px 보장(BR-U-01)
  loading?: boolean;      // true 시 Spinner 표시 + disabled
  disabled?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
  "data-testid"?: string;  // 자동화 친화(BR-U-05)
}
```
- 상태: 없음(controlled). `loading`은 부모가 제어.
- 인터랙션: `loading || disabled` 시 클릭 무시.

**Card**
```ts
interface CardProps {
  onClick?: () => void;    // 클릭 가능 카드(주문 상세 열기 등)
  highlighted?: boolean;   // 신규 주문 강조(A2-S2) — 소비 앱이 결정
  children: React.ReactNode;
  "data-testid"?: string;
}
```
- 상태 없음. `highlighted`는 시각 강조 클래스 토글.

**Modal**
```ts
interface ModalProps {
  open: boolean;
  title?: string;
  onClose: () => void;         // 오버레이/ESC/닫기 버튼
  footer?: React.ReactNode;    // 확인/취소 버튼 슬롯(삭제·이용완료 확인 팝업)
  children: React.ReactNode;
  "data-testid"?: string;
}
```
- 상태: 내부 상태 없음(open은 부모 제어). 접근성: focus trap, ESC 닫기, 오버레이 클릭 닫기.
- 사용처: OrderDetailModal(A2-S3), OrderDeleteAction 확인(A3-S2), SessionCompleteAction 확인(A3-S3).

**Spinner**
```ts
interface SpinnerProps { size?: "sm" | "md" | "lg"; label?: string; }
```

**ErrorBanner**
```ts
interface ErrorBannerProps {
  error: ApiError | string | null;   // null이면 렌더 안 함
  onRetry?: () => void;              // 폴링 재시도 등
  "data-testid"?: string;
}
```
- `ApiError`면 `error.message`(일반화 메시지, BR-S-03)만 표시. `code`는 노출하지 않음(내부 정보).

### 2.3 디자인 토큰 (CSS Modules 변수)
```
--touch-min: 44px;        /* BR-U-01 */
--color-primary / --color-danger / --color-surface / --color-text
--space-1..4 (4·8·12·16px)
--radius-card / --font-size-base
```
> 구체 색상·타이포 값은 Code Generation 단계에서 확정. 두 앱이 토큰을 오버라이드 가능.

---

## 3. Hook — usePolling (React 계층)

> 시그니처·라이프사이클은 `business-logic-model.md` §3. 여기서는 소비 관점 요약.

```ts
const { data, error, isLoading, lastServerTime, refetch } =
  usePolling<DashboardResponse>(
    (signal) => api.get<DashboardResponse>("/tables/dashboard", { signal }),
    { intervalMs: 2000, enabled: isLoggedIn }
  );
```
- **소비 예 (admin-web DashboardGrid, A2-S2)**: `data.tables`를 그리드 렌더, `card.created_at > lastServerTime` 항목에 `<Card highlighted>` 적용(신규 강조 — Q6=A로 판단은 소비 앱).
- **소비 예 (customer-web OrderHistoryView, C5-S2)**: `usePolling<OrderListResponse>(() => api.get("/orders"))`로 상태 준실시간 갱신.
- **에러 표시**: `error` 지속 시 `<ErrorBanner error={error} onRetry={refetch} />`.

---

## 4. API 통합 지점 (컴포넌트 ↔ 백엔드)

| shared 요소 | 사용 backend 엔드포인트(계약 §2) | 소비 스토리 |
|---|---|---|
| ApiClient.post `/orders` | POST /api/orders | C4-S1 |
| ApiClient.get `/orders` (+usePolling) | GET /api/orders | C5-S1/S2 |
| ApiClient.get `/menu` | GET /api/menu | C2-S1 |
| ApiClient.get `/tables/dashboard` (+usePolling) | GET /api/tables/dashboard | A2-S1/S2 |
| ApiClient.patch `/orders/{id}/status` | PATCH …/status | A2-S4 |
| ApiClient.delete `/orders/{id}` | DELETE /api/orders/{id} | A3-S2 |
| ApiClient.post `/admin/login` · `/table/login` | 로그인 2종 | A1-S1, C1-S1 |
| ApiClient.post `/tables/{id}/setup` · `/complete` | 테이블 설정·이용완료 | A3-S1, A3-S3 |
| ApiClient.get `/history` | GET /api/history | A3-S4 |

> shared는 위 호출을 **가능케 하는 공통 계층**만 제공. 실제 화면·라우팅·폼은 customer-web/admin-web 소유.

---

## 5. 폼 검증 규칙 (shared 제공 범위)
- shared는 완성된 폼 컴포넌트를 제공하지 않는다(로그인·설정 폼은 소비 앱 소유).
- shared는 **표시/입력 보조**만: Button(제출 버튼 로딩), 금액 포맷(formatKRW), 수량 경계(PricingUtil BR-P-03)로 소비 앱의 검증을 지원.

---

## 6. 컴포넌트 ↔ 스토리 추적
- Button/Card/Modal/Spinner/ErrorBanner → C2-S3(터치 UI) 및 전 UI 스토리 지원
- usePolling → C5-S2, A2-S2
- Card(highlighted)/Modal → A2-S2(신규 강조), A2-S3(상세), A3-S2/S3(확인 팝업)
