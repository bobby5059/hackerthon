/**
 * usePolling — 2s polling hook (NFR-design PP-02/PP-04, RP-03; FD BR-PL).
 *
 * - Fetches immediately on mount, then every `intervalMs` (default 2000).
 * - Pauses while the tab is hidden and resumes (with an immediate tick) on
 *   visibility (PP-04/RP-03) — no wasted requests in the background.
 * - Silent retry on failure: keeps the last good `data`, records `error`,
 *   retries next tick without interrupting the UI (BR-PL-03).
 * - Reference-stable: the latest `fetchFn` is kept in a ref so its identity
 *   changing does NOT restart the interval (PP-02); `refetch` is memoized.
 * - Cleans up on unmount: clears the interval and aborts the in-flight request.
 */
import { useCallback, useEffect, useReducer, useRef } from 'react';
import type { ApiError } from '../api';
import { normalizeError } from '../api';

export interface UsePollingOptions {
  /** Poll interval in ms. Default 2000. */
  intervalMs?: number;
  /** When false, polling is stopped entirely. Default true. */
  enabled?: boolean;
  /** Optional per-error observation hook. */
  onError?: (error: ApiError) => void;
}

export interface PollingState<T> {
  data: T | null;
  error: ApiError | null;
  /** True only during the very first load (no data yet). */
  loading: boolean;
  /** `server_time` from the latest successful payload, if present. */
  lastServerTime: string | null;
}

type Action<T> =
  | { type: 'success'; data: T; serverTime: string | null }
  | { type: 'error'; error: ApiError };

function reducer<T>(state: PollingState<T>, action: Action<T>): PollingState<T> {
  switch (action.type) {
    case 'success':
      return {
        data: action.data,
        error: null,
        loading: false,
        lastServerTime: action.serverTime ?? state.lastServerTime,
      };
    case 'error':
      // Keep last good data; surface the error without clearing the screen.
      return { ...state, error: action.error, loading: false };
  }
}

function extractServerTime(payload: unknown): string | null {
  if (
    typeof payload === 'object' &&
    payload !== null &&
    'server_time' in payload &&
    typeof (payload as { server_time: unknown }).server_time === 'string'
  ) {
    return (payload as { server_time: string }).server_time;
  }
  return null;
}

export function usePolling<T>(
  fetchFn: (signal: AbortSignal) => Promise<T>,
  options: UsePollingOptions = {},
): PollingState<T> & { refetch: () => void } {
  const { intervalMs = 2000, enabled = true, onError } = options;

  const [state, dispatch] = useReducer(reducer<T>, {
    data: null,
    error: null,
    loading: true,
    lastServerTime: null,
  });

  // Latest fetchFn / onError held in refs so their identity does not restart polling.
  const fetchRef = useRef(fetchFn);
  fetchRef.current = fetchFn;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  // Tracks the in-flight request so we can abort it on unmount / re-tick.
  const abortRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  const runFetch = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const data = await fetchRef.current(controller.signal);
      if (!mountedRef.current || controller.signal.aborted) return;
      dispatch({ type: 'success', data, serverTime: extractServerTime(data) });
    } catch (err) {
      if (!mountedRef.current || controller.signal.aborted) return;
      const apiError = normalizeError(err);
      onErrorRef.current?.(apiError);
      dispatch({ type: 'error', error: apiError });
    }
  }, []);

  const refetch = useCallback(() => {
    void runFetch();
  }, [runFetch]);

  useEffect(() => {
    mountedRef.current = true;
    if (!enabled) return;

    let timer: ReturnType<typeof setInterval> | null = null;

    const start = () => {
      if (timer !== null) return;
      timer = setInterval(() => void runFetch(), intervalMs);
    };
    const stop = () => {
      if (timer !== null) {
        clearInterval(timer);
        timer = null;
      }
    };

    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        void runFetch(); // immediate catch-up tick
        start();
      } else {
        stop();
        abortRef.current?.abort();
      }
    };

    // Initial load + interval (only when visible).
    void runFetch();
    if (document.visibilityState === 'visible') start();
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      mountedRef.current = false;
      stop();
      abortRef.current?.abort();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [enabled, intervalMs, runFetch]);

  return { ...state, refetch };
}
