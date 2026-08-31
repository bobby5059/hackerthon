// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { usePolling } from './usePolling';

function setVisibility(state: 'visible' | 'hidden') {
  Object.defineProperty(document, 'visibilityState', {
    configurable: true,
    get: () => state,
  });
  document.dispatchEvent(new Event('visibilitychange'));
}

describe('usePolling', () => {
  beforeEach(() => {
    setVisibility('visible');
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('fetches immediately on mount and exposes data + server_time', async () => {
    const fetchFn = vi
      .fn()
      .mockResolvedValue({ value: 1, server_time: '2026-08-31T00:00:00Z' });
    const { result } = renderHook(() => usePolling(fetchFn, { intervalMs: 2000 }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(fetchFn).toHaveBeenCalledTimes(1);
    expect(result.current.data).toEqual({
      value: 1,
      server_time: '2026-08-31T00:00:00Z',
    });
    expect(result.current.loading).toBe(false);
    expect(result.current.lastServerTime).toBe('2026-08-31T00:00:00Z');
  });

  it('polls every intervalMs', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ n: 1 });
    renderHook(() => usePolling(fetchFn, { intervalMs: 2000 }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0); // initial
      await vi.advanceTimersByTimeAsync(2000); // tick 1
      await vi.advanceTimersByTimeAsync(2000); // tick 2
    });

    expect(fetchFn).toHaveBeenCalledTimes(3);
  });

  it('preserves last good data and records error on failure (silent retry)', async () => {
    const fetchFn = vi
      .fn()
      .mockResolvedValueOnce({ n: 1 })
      .mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const { result } = renderHook(() => usePolling(fetchFn, { intervalMs: 2000 }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0); // success
    });
    expect(result.current.data).toEqual({ n: 1 });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000); // failure
    });
    expect(result.current.data).toEqual({ n: 1 }); // preserved
    expect(result.current.error?.code).toBe('NETWORK_ERROR');
  });

  it('pauses while hidden and resumes on visibility', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ n: 1 });
    renderHook(() => usePolling(fetchFn, { intervalMs: 2000 }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0); // initial (1)
    });
    expect(fetchFn).toHaveBeenCalledTimes(1);

    act(() => setVisibility('hidden'));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(6000); // no ticks while hidden
    });
    expect(fetchFn).toHaveBeenCalledTimes(1);

    act(() => setVisibility('visible')); // immediate catch-up tick
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });

  it('does not fetch when disabled', async () => {
    const fetchFn = vi.fn().mockResolvedValue({});
    renderHook(() => usePolling(fetchFn, { enabled: false }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(fetchFn).not.toHaveBeenCalled();
  });

  it('does not restart the interval when fetchFn identity changes', async () => {
    let calls = 0;
    const { rerender } = renderHook(({ fn }) => usePolling(fn, { intervalMs: 2000 }), {
      initialProps: { fn: () => Promise.resolve(++calls) },
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    // New fetchFn identity on every rerender must not reset the timer.
    rerender({ fn: () => Promise.resolve(++calls) });
    rerender({ fn: () => Promise.resolve(++calls) });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    // 1 initial + 1 tick = 2, not multiplied by rerenders.
    expect(calls).toBe(2);
  });

  it('cleans up the interval on unmount', async () => {
    const fetchFn = vi.fn().mockResolvedValue({});
    const { unmount } = renderHook(() => usePolling(fetchFn, { intervalMs: 2000 }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(6000);
    });
    expect(fetchFn).toHaveBeenCalledTimes(1);
  });

  it('refetch triggers an out-of-cycle fetch', async () => {
    const fetchFn = vi.fn().mockResolvedValue({ n: 1 });
    const { result } = renderHook(() => usePolling(fetchFn, { intervalMs: 100000 }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(fetchFn).toHaveBeenCalledTimes(1);
    await act(async () => {
      result.current.refetch();
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });
});
