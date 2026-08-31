/**
 * Property-based tests for PricingUtil (PBT Partial — NFR-SH-T-01, properties P1~P6).
 * Target: 100% coverage of src/pricing.
 */
import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { lineTotal, cartTotal, type PricingLine } from './index';

// Non-negative integer prices/quantities within a realistic KRW range.
const price = fc.integer({ min: 0, max: 10_000_000 });
const qty = fc.integer({ min: 0, max: 1000 });

describe('lineTotal', () => {
  // P1: non-negativity + integrality
  it('P1: is always a non-negative integer', () => {
    fc.assert(
      fc.property(price, qty, (p, q) => {
        const r = lineTotal(p, q);
        expect(Number.isInteger(r)).toBe(true);
        expect(r).toBeGreaterThanOrEqual(0);
      }),
    );
  });

  // P2: zero quantity (or zero price) yields zero
  it('P2: quantity 0 → 0', () => {
    fc.assert(
      fc.property(price, (p) => {
        expect(lineTotal(p, 0)).toBe(0);
      }),
    );
  });

  // P5: scalar multiple — lineTotal is exactly price*quantity
  it('P5: equals price × quantity', () => {
    fc.assert(
      fc.property(price, qty, (p, q) => {
        expect(lineTotal(p, q)).toBe(p * q);
      }),
    );
  });

  // P6: negatives / non-integers are clamped and truncated (defensive, BR-P)
  it('P6: negative or fractional inputs are floored to a non-negative integer', () => {
    expect(lineTotal(-100, 3)).toBe(0);
    expect(lineTotal(100, -3)).toBe(0);
    expect(lineTotal(100.9, 2)).toBe(200);
    expect(lineTotal(Number.NaN, 2)).toBe(0);
    expect(lineTotal(100, Number.POSITIVE_INFINITY)).toBe(0);
  });
});

describe('cartTotal', () => {
  const lineArb = fc.record({
    unit_price: price,
    quantity: qty,
  });

  // P1 (cart): non-negative integer
  it('P1: is always a non-negative integer', () => {
    fc.assert(
      fc.property(fc.array(lineArb), (items) => {
        const r = cartTotal(items);
        expect(Number.isInteger(r)).toBe(true);
        expect(r).toBeGreaterThanOrEqual(0);
      }),
    );
  });

  // P3: distributivity — cartTotal equals the sum of per-line totals
  it('P3: equals the sum of lineTotal over items', () => {
    fc.assert(
      fc.property(fc.array(lineArb), (items) => {
        const expected = items.reduce(
          (s, i) => s + lineTotal(i.unit_price, i.quantity),
          0,
        );
        expect(cartTotal(items)).toBe(expected);
      }),
    );
  });

  // P4: order invariance — permuting items does not change the total
  it('P4: is invariant under item reordering', () => {
    fc.assert(
      fc.property(fc.array(lineArb), (items) => {
        const reversed = [...items].reverse();
        expect(cartTotal(reversed)).toBe(cartTotal(items));
      }),
    );
  });

  // P2 (cart): empty cart → 0
  it('P2: empty cart → 0', () => {
    expect(cartTotal([])).toBe(0);
  });

  // Example: falls back to `price` when `unit_price` is absent
  it('falls back to price when unit_price is missing', () => {
    const items: PricingLine[] = [
      { price: 5000, quantity: 2 },
      { unit_price: 3000, quantity: 1 },
    ];
    expect(cartTotal(items)).toBe(13_000);
  });

  it('treats a line with neither price nor unit_price as 0', () => {
    expect(cartTotal([{ quantity: 5 }])).toBe(0);
  });
});
