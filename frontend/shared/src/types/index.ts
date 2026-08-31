/**
 * Types — augmentation layer (hand-authored).
 *
 * `shared` does NOT own domain data; the backend (Pydantic) is the SSOT and this
 * module mirrors it via openapi-typescript. Consumers import ONLY from here
 * (`@table-order/shared/types`), never from `./generated` directly — that keeps
 * alias names stable across snapshot regenerations.
 *
 * Field names stay snake_case to match the contract exactly (no camelCase mapping).
 */
import type { components } from './generated/schema';

type Schemas = components['schemas'];

/* ── Enums & display labels (contract §3.1) ───────────────────────────── */

export type OrderStatus = Schemas['OrderStatus'];

/** Front-only display labels (not in OpenAPI). */
export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  PENDING: '대기중',
  PREPARING: '준비중',
  COMPLETED: '완료',
};

/* ── Domain models (contract §3.2) ────────────────────────────────────── */

export type Category = Schemas['Category'];
export type Menu = Schemas['Menu'];
export type OrderItemInput = Schemas['OrderItemInput'];
export type OrderItem = Schemas['OrderItem'];
export type Order = Schemas['Order'];
export type OrderPreview = Schemas['OrderPreview'];
export type TableCard = Schemas['TableCard'];
export type HistoryEntry = Schemas['HistoryEntry'];
export type PageMeta = Schemas['PageMeta'];

/* ── Auth / response wrappers (contract §2) ───────────────────────────── */

export type StoreBrief = Schemas['StoreBrief'];
export type TableBrief = Schemas['TableBrief'];
export type SessionBrief = Schemas['SessionBrief'];
export type AdminLoginResponse = Schemas['AdminLoginResponse'];
export type TableLoginResponse = Schemas['TableLoginResponse'];
export type MenuListResponse = Schemas['MenuListResponse'];
export type OrderListResponse = Schemas['OrderListResponse'];
export type DashboardResponse = Schemas['DashboardResponse'];
export type HistoryListResponse = Schemas['HistoryListResponse'];
export type DeleteOrderResponse = Schemas['DeleteOrderResponse'];
export type CompleteSessionResponse = Schemas['CompleteSessionResponse'];

/* ── Request bodies ───────────────────────────────────────────────────── */

export type AdminLoginRequest = Schemas['AdminLoginRequest'];
export type TableLoginRequest = Schemas['TableLoginRequest'];
export type CreateOrderRequest = Schemas['CreateOrderRequest'];
export type UpdateStatusRequest = Schemas['UpdateStatusRequest'];
export type TableSetupRequest = Schemas['TableSetupRequest'];

/* ── Errors (contract §1.3 — augmentation) ────────────────────────────── */

/**
 * Server error codes (contract §1.3) plus shared-only `NETWORK_ERROR`
 * (network/timeout/parse failures wrapped by ApiClient).
 */
export type ApiErrorCode =
  | 'VALIDATION_ERROR'
  | 'UNAUTHORIZED'
  | 'TOKEN_EXPIRED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'ORDER_EMPTY'
  | 'TOTAL_MISMATCH'
  | 'SESSION_CLOSED'
  | 'RATE_LIMITED'
  | 'INTERNAL_ERROR'
  | 'NETWORK_ERROR';

/** Raw server error envelope (contract §1.3). */
export type ApiErrorEnvelope = Schemas['ApiErrorEnvelope'];
