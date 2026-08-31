/**
 * PricingUtil — pure integer-KRW pricing functions (business-logic-model.md).
 *
 * All amounts are integer KRW (contract §3.3) — no floating point, no currency
 * symbols. These are display/estimation helpers; the server's re-validated
 * `total_amount` is always authoritative (BR-P). Zero runtime dependencies.
 */

/** A cart line usable for totalling. Accepts the order-item snapshot shape
 *  (`unit_price`) or a menu-derived shape (`price`); `unit_price` wins. */
export interface PricingLine {
  unit_price?: number;
  price?: number;
  quantity: number;
}

/** Coerce to a safe non-negative integer; non-finite/NaN → 0. */
function toSafeInt(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.trunc(value);
}

/**
 * Amount for a single line = unitPrice × quantity (integer KRW).
 * Negative or non-integer inputs are truncated toward zero and floored at 0,
 * so the result is always a non-negative integer (BR-P, PBT P1).
 */
export function lineTotal(unitPrice: number, quantity: number): number {
  const price = Math.max(0, toSafeInt(unitPrice));
  const qty = Math.max(0, toSafeInt(quantity));
  return price * qty;
}

/**
 * Sum of all line totals in a cart (integer KRW). O(n) single pass.
 * Uses `unit_price` when present, otherwise `price` (menu-derived), else 0.
 */
export function cartTotal(items: readonly PricingLine[]): number {
  return items.reduce((sum, item) => {
    const unit = item.unit_price ?? item.price ?? 0;
    return sum + lineTotal(unit, item.quantity);
  }, 0);
}
