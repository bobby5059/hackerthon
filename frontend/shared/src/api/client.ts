/**
 * createApiClient — factory-function HTTP client (NFR-design Q4/RP-01/02/04, SP-01/02).
 *
 * - Native fetch, zero runtime deps.
 * - 10s default timeout via AbortController, merged with any caller signal (RP-01).
 * - No automatic retries (RP-02) — mutations are not idempotent; periodic retry is
 *   the polling hook's job only.
 * - Never stores credentials (SP-02): the token is read per request via getToken().
 * - Never logs (SP-01): observation is delegated to the optional onError callback.
 * - 401 / TOKEN_EXPIRED trigger onUnauthorized() then throw (RP-04, fail-closed).
 */
import { ApiError, errorFromResponse, normalizeError } from './errors';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface ApiClientConfig {
  /** Base URL, e.g. "https://api.example.com" or "" for same-origin. */
  baseUrl: string;
  /** Read the current bearer token; return null when unauthenticated. */
  getToken?: () => string | null;
  /** Per-request timeout in ms. Default 10000. */
  timeoutMs?: number;
  /** Optional observation hook — receives every ApiError before it is thrown. */
  onError?: (error: ApiError) => void;
  /** Called on 401 / TOKEN_EXPIRED so the consumer can re-authenticate. */
  onUnauthorized?: () => void;
}

export interface RequestOptions {
  /** JSON-serializable request body. */
  body?: unknown;
  /** Query params; nullish values are skipped. */
  query?: Record<string, string | number | boolean | null | undefined>;
  /** Extra headers (Authorization is injected automatically). */
  headers?: Record<string, string>;
  /** Caller abort signal; merged with the internal timeout signal. */
  signal?: AbortSignal;
}

export interface ApiClient {
  request<T>(method: HttpMethod, path: string, options?: RequestOptions): Promise<T>;
}

const DEFAULT_TIMEOUT_MS = 10_000;

function buildUrl(
  baseUrl: string,
  path: string,
  query?: RequestOptions['query'],
): string {
  const base = baseUrl.replace(/\/$/, '');
  let url = `${base}${path}`;
  if (query) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== null && value !== undefined) params.append(key, String(value));
    }
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }
  return url;
}

/** Merge the internal timeout signal with an optional caller signal. */
function linkAbort(
  timeoutMs: number,
  external?: AbortSignal,
): { signal: AbortSignal; cleanup: () => void } {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const onExternalAbort = () => controller.abort();
  if (external) {
    if (external.aborted) controller.abort();
    else external.addEventListener('abort', onExternalAbort);
  }

  return {
    signal: controller.signal,
    cleanup: () => {
      clearTimeout(timer);
      external?.removeEventListener('abort', onExternalAbort);
    },
  };
}

export function createApiClient(config: ApiClientConfig): ApiClient {
  const timeoutMs = config.timeoutMs ?? DEFAULT_TIMEOUT_MS;

  async function request<T>(
    method: HttpMethod,
    path: string,
    options: RequestOptions = {},
  ): Promise<T> {
    const url = buildUrl(config.baseUrl, path, options.query);

    const headers: Record<string, string> = { ...options.headers };
    const token = config.getToken?.();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const hasBody = options.body !== undefined;
    if (hasBody && headers['Content-Type'] === undefined) {
      headers['Content-Type'] = 'application/json';
    }

    const { signal, cleanup } = linkAbort(timeoutMs, options.signal);

    const init: RequestInit = { method, headers, signal };
    if (hasBody) init.body = JSON.stringify(options.body);

    let response: Response;
    try {
      response = await fetch(url, init);
    } catch (err) {
      cleanup();
      throw fail(normalizeError(err));
    }
    cleanup();

    if (!response.ok) {
      const body = await safeJson(response);
      throw fail(errorFromResponse(response.status, body));
    }

    if (response.status === 204) return undefined as T;

    try {
      return (await response.json()) as T;
    } catch {
      throw fail(new ApiError('NETWORK_ERROR', '응답을 해석할 수 없습니다.', 0));
    }
  }

  /** Route every error through onUnauthorized (fail-closed) + onError, then return it to throw. */
  function fail(error: ApiError): ApiError {
    if (error.code === 'UNAUTHORIZED' || error.code === 'TOKEN_EXPIRED') {
      config.onUnauthorized?.();
    }
    config.onError?.(error);
    return error;
  }

  return { request };
}

async function safeJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}
