/**
 * ApiError + normalizeError — the single error-mapping module (NFR-design MP-02).
 *
 * Every failure a consumer sees from the ApiClient is an `ApiError`. Mapping from
 * HTTP status / contract envelope / network / timeout / parse failure lives here
 * only, so it is consistent and unit-testable.
 *
 * Security (SP-01): ApiError never carries request headers, tokens, or raw
 * request bodies — nothing sensitive is attached.
 */
import type { ApiErrorCode } from '../types';

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  /** HTTP status, or 0 for network/timeout/parse failures. */
  readonly httpStatus: number;
  /** Server-provided correlation id (contract §1.3), when available. */
  readonly requestId: string | undefined;

  constructor(
    code: ApiErrorCode,
    message: string,
    httpStatus: number,
    requestId?: string,
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.httpStatus = httpStatus;
    this.requestId = requestId;
    // Restore prototype chain for instanceof across transpile targets.
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

const KNOWN_CODES: ReadonlySet<string> = new Set<ApiErrorCode>([
  'VALIDATION_ERROR',
  'UNAUTHORIZED',
  'TOKEN_EXPIRED',
  'FORBIDDEN',
  'NOT_FOUND',
  'ORDER_EMPTY',
  'TOTAL_MISMATCH',
  'SESSION_CLOSED',
  'RATE_LIMITED',
  'INTERNAL_ERROR',
  'NETWORK_ERROR',
]);

/** Map an HTTP status to a contract error code when the body has none. */
function codeFromStatus(status: number): ApiErrorCode {
  switch (status) {
    case 400:
      return 'VALIDATION_ERROR';
    case 401:
      return 'UNAUTHORIZED';
    case 403:
      return 'FORBIDDEN';
    case 404:
      return 'NOT_FOUND';
    case 409:
      return 'SESSION_CLOSED';
    case 429:
      return 'RATE_LIMITED';
    default:
      return status >= 500 ? 'INTERNAL_ERROR' : 'VALIDATION_ERROR';
  }
}

function narrowCode(raw: string, status: number): ApiErrorCode {
  return KNOWN_CODES.has(raw) ? (raw as ApiErrorCode) : codeFromStatus(status);
}

type EnvelopeLike = {
  error?: { code?: unknown; message?: unknown; request_id?: unknown };
};

function isEnvelope(body: unknown): body is EnvelopeLike {
  return typeof body === 'object' && body !== null && 'error' in body;
}

/**
 * Build an ApiError from a non-OK HTTP response body.
 * `status` is the HTTP status; `body` is the parsed JSON (may be anything).
 */
export function errorFromResponse(status: number, body: unknown): ApiError {
  if (isEnvelope(body) && body.error && typeof body.error === 'object') {
    const rawCode = typeof body.error.code === 'string' ? body.error.code : '';
    const message =
      typeof body.error.message === 'string' && body.error.message
        ? body.error.message
        : `요청이 실패했습니다. (HTTP ${status})`;
    const requestId =
      typeof body.error.request_id === 'string' ? body.error.request_id : undefined;
    return new ApiError(narrowCode(rawCode, status), message, status, requestId);
  }
  return new ApiError(
    codeFromStatus(status),
    `요청이 실패했습니다. (HTTP ${status})`,
    status,
  );
}

/**
 * Normalize ANY thrown/rejected value from a fetch call into an ApiError.
 * Handles AbortError (timeout), network TypeErrors, and already-ApiErrors.
 */
export function normalizeError(input: unknown): ApiError {
  if (input instanceof ApiError) return input;

  if (input instanceof DOMException && input.name === 'AbortError') {
    return new ApiError('NETWORK_ERROR', '요청 시간이 초과되었습니다.', 0);
  }
  if (input instanceof Error && input.name === 'AbortError') {
    return new ApiError('NETWORK_ERROR', '요청 시간이 초과되었습니다.', 0);
  }
  // fetch throws a TypeError on network failure / CORS / DNS.
  if (input instanceof TypeError) {
    return new ApiError('NETWORK_ERROR', '네트워크 오류가 발생했습니다.', 0);
  }
  const message =
    input instanceof Error && input.message
      ? input.message
      : '알 수 없는 오류가 발생했습니다.';
  return new ApiError('NETWORK_ERROR', message, 0);
}
