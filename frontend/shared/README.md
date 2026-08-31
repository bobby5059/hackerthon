# @table-order/shared

테이블오더 서비스의 프론트엔드 공유 라이브러리. `customer-web`와 `admin-web`가
공통으로 쓰는 **타입 · 가격 계산 · API 클라이언트 · 폴링 훅 · UI 킷**을 제공한다.

- 런타임 의존성 **0** (네이티브 `fetch` 사용)
- **ESM 전용**, TypeScript strict
- React는 `peerDependency` (`^18`) — `hooks`/`ui` 서브경로에서만 필요

> 도메인 데이터의 SSOT는 백엔드다. 본 라이브러리는 [Integration Contract v1.0](../../aidlc-docs/construction/integration-contract.md)을 미러링한다.

## 서브경로 export

| import                        | 내용                                                               | React 필요 |
| ----------------------------- | ------------------------------------------------------------------ | ---------- |
| `@table-order/shared/types`   | 도메인 타입, `OrderStatus`, `ORDER_STATUS_LABELS`, `ApiError` 코드 | ✗          |
| `@table-order/shared/pricing` | `lineTotal`, `cartTotal` (정수 KRW 순수 함수)                      | ✗          |
| `@table-order/shared/api`     | `createApiClient`, `ApiError`, `normalizeError`                    | ✗          |
| `@table-order/shared/hooks`   | `usePolling` (2초 폴링, 탭 비활성 정지)                            | ✓          |
| `@table-order/shared/ui`      | `Button`/`Card`/`Modal`/`Spinner`/`ErrorBanner`                    | ✓          |

## 사용 예

```ts
import { createApiClient } from '@table-order/shared/api';
import { cartTotal } from '@table-order/shared/pricing';
import type { MenuListResponse } from '@table-order/shared/types';

const api = createApiClient({
  baseUrl: import.meta.env.VITE_API_BASE_URL,
  getToken: () => localStorage.getItem('access_token'),
  onUnauthorized: () => redirectToLogin(),
});

const menu = await api.request<MenuListResponse>('GET', '/api/menu');
const total = cartTotal(cartItems); // 정수 KRW
```

```tsx
import { usePolling } from '@table-order/shared/hooks';
import type { OrderListResponse } from '@table-order/shared/types';

const { data, error, loading } = usePolling<OrderListResponse>(
  (signal) => api.request('GET', '/api/orders', { signal }),
  { intervalMs: 2000 },
);
```

## 개발 스크립트

```bash
npm run gen:types   # openapi.json → src/types/generated/schema.ts
npm run build       # tsup (ESM + d.ts)
npm run test        # vitest run (PricingUtil은 PBT + 100% 커버리지)
npm run typecheck   # tsc --noEmit
npm run lint        # eslint + prettier --check
```

### 타입 스냅샷 갱신

`src/types/generated/schema.ts`는 **자동 생성물**이다. 직접 수정하지 말 것.
백엔드 계약이 바뀌면 Integration Contract §9 절차에 따라 `openapi.json`을 교체하고
`npm run gen:types`를 재실행한 뒤 커밋한다. CI는 `git diff --exit-code src/types/generated`로
스냅샷과 생성물의 동기화를 강제한다.
