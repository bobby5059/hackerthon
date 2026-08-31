import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createApiClient, ApiError } from './index';
import { normalizeError, errorFromResponse } from './errors';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('normalizeError', () => {
  it('passes through an existing ApiError', () => {
    const e = new ApiError('NOT_FOUND', 'x', 404);
    expect(normalizeError(e)).toBe(e);
  });

  it('maps AbortError to NETWORK_ERROR/timeout', () => {
    const abort = new DOMException('aborted', 'AbortError');
    const e = normalizeError(abort);
    expect(e.code).toBe('NETWORK_ERROR');
    expect(e.httpStatus).toBe(0);
  });

  it('maps a TypeError (network failure) to NETWORK_ERROR', () => {
    const e = normalizeError(new TypeError('Failed to fetch'));
    expect(e.code).toBe('NETWORK_ERROR');
  });
});

describe('errorFromResponse', () => {
  it('reads code/message/request_id from the contract envelope', () => {
    const e = errorFromResponse(409, {
      error: { code: 'SESSION_CLOSED', message: '세션 종료됨', request_id: 'req-1' },
    });
    expect(e.code).toBe('SESSION_CLOSED');
    expect(e.message).toBe('세션 종료됨');
    expect(e.requestId).toBe('req-1');
    expect(e.httpStatus).toBe(409);
  });

  it('falls back to a status-derived code when the body has none', () => {
    expect(errorFromResponse(404, undefined).code).toBe('NOT_FOUND');
    expect(errorFromResponse(500, {}).code).toBe('INTERNAL_ERROR');
    expect(errorFromResponse(429, {}).code).toBe('RATE_LIMITED');
  });

  it('narrows an unknown envelope code back to the status mapping', () => {
    const e = errorFromResponse(400, {
      error: { code: 'WEIRD_CODE', message: 'm', request_id: 'r' },
    });
    expect(e.code).toBe('VALIDATION_ERROR');
  });
});

describe('createApiClient.request', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock);
    fetchMock.mockReset();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('injects the bearer token and returns parsed JSON', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { ok: true }));
    const api = createApiClient({ baseUrl: 'https://x', getToken: () => 'tok' });

    const result = await api.request<{ ok: boolean }>('GET', '/api/menu');

    expect(result).toEqual({ ok: true });
    const [, init] = fetchMock.mock.calls[0]!;
    expect((init.headers as Record<string, string>)['Authorization']).toBe('Bearer tok');
  });

  it('omits Authorization when no token is available', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, {}));
    const api = createApiClient({ baseUrl: 'https://x', getToken: () => null });
    await api.request('GET', '/api/menu');
    const [, init] = fetchMock.mock.calls[0]!;
    expect((init.headers as Record<string, string>)['Authorization']).toBeUndefined();
  });

  it('serializes a JSON body with the correct content type and query string', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, {}));
    const api = createApiClient({ baseUrl: 'https://x/' });
    await api.request('POST', '/api/orders', {
      body: { items: [] },
      query: { page: 1, skip: null },
    });
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe('https://x/api/orders?page=1');
    expect(init.body).toBe(JSON.stringify({ items: [] }));
    expect((init.headers as Record<string, string>)['Content-Type']).toBe(
      'application/json',
    );
  });

  it('returns undefined for 204 No Content', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    const api = createApiClient({ baseUrl: '' });
    await expect(api.request('DELETE', '/api/orders/1')).resolves.toBeUndefined();
  });

  it('throws an ApiError from a non-OK response and fires onError', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(404, {
        error: { code: 'NOT_FOUND', message: '없음', request_id: 'r' },
      }),
    );
    const onError = vi.fn();
    const api = createApiClient({ baseUrl: '', onError });

    await expect(api.request('GET', '/api/orders/1')).rejects.toMatchObject({
      code: 'NOT_FOUND',
      httpStatus: 404,
    });
    expect(onError).toHaveBeenCalledOnce();
  });

  it('fires onUnauthorized on 401 (fail-closed)', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(401, {
        error: { code: 'TOKEN_EXPIRED', message: '만료', request_id: 'r' },
      }),
    );
    const onUnauthorized = vi.fn();
    const api = createApiClient({ baseUrl: '', onUnauthorized });

    await expect(api.request('GET', '/api/orders')).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it('wraps a network failure as NETWORK_ERROR', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const api = createApiClient({ baseUrl: '' });
    await expect(api.request('GET', '/api/menu')).rejects.toMatchObject({
      code: 'NETWORK_ERROR',
      httpStatus: 0,
    });
  });

  it('aborts and reports NETWORK_ERROR when the timeout elapses', async () => {
    vi.useFakeTimers();
    // fetch that rejects with AbortError once its signal fires.
    fetchMock.mockImplementationOnce(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener('abort', () =>
            reject(new DOMException('aborted', 'AbortError')),
          );
        }),
    );
    const api = createApiClient({ baseUrl: '', timeoutMs: 5000 });
    const promise = api.request('GET', '/api/menu');
    const assertion = expect(promise).rejects.toMatchObject({ code: 'NETWORK_ERROR' });
    await vi.advanceTimersByTimeAsync(5000);
    await assertion;
  });
});
