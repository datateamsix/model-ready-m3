import { auth } from "@clerk/nextjs/server";

/**
 * The server-side (never client-bundled) call path into `prem3-api`, shared
 * by the generic BFF route (src/app/api/prem3/[...path]/route.ts, for any
 * browser-originated call) and by Server Components/Actions that can call
 * straight through without a self-referential HTTP hop.
 *
 * `PREM3_API_BASE_URL` is server-only. As of 2026-08-17 the backend has
 * frozen a real OpenAPI contract (commit `e045b4294e2bba36efa74b132e976e
 * 0959e2644b`, see docs/context/PREM3_API.md) but no deployment is
 * configured here yet, and Clerk/Stripe adapters on the backend side are
 * explicitly pending (backend Mission 07) -- every call still fails
 * loudly with a typed error until then, matching the documented-gap
 * pattern already established by ApiPreM3DataSource
 * (src/lib/adapters/api-data-source.ts).
 *
 * Error parsing matches the frozen contract's ProblemDetail schema
 * (application/problem+json: type, title, status, detail, code,
 * request_id, errors?, instance?) -- callers key off `error.code`, never
 * `error.message`/`detail` prose, per docs/context/PREM3_API.md's own
 * instruction.
 */

const REQUEST_TIMEOUT_MS = 15_000;

export interface PreM3ApiError {
  code: string;
  /** ProblemDetail.detail -- human-readable, never parsed for logic. */
  message: string;
  requestId: string;
  title?: string;
  errors?: { field: string; message: string }[];
}

export type PreM3ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: number; error: PreM3ApiError };

interface ProblemDetailBody {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  code?: string;
  request_id?: string;
  errors?: { field: string; message: string }[] | null;
  instance?: string | null;
}

function localError<T>(status: number, code: string, message: string, requestId: string): PreM3ApiResult<T> {
  return { ok: false, status, error: { code, message, requestId } };
}

async function performRequest<T>(
  path: string,
  init: RequestInit,
  token: string | null,
  requestId: string,
): Promise<PreM3ApiResult<T>> {
  const baseUrl = process.env.PREM3_API_BASE_URL;
  if (!baseUrl) {
    return localError(
      503,
      "PREM3_API_NOT_CONFIGURED",
      "No prem3-api backend is configured yet (PREM3_API_BASE_URL unset). See docs/context/PREM3_API.md.",
      requestId,
    );
  }

  const targetUrl = new URL(path.replace(/^\//, ""), baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(targetUrl, {
      ...init,
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        "content-type": "application/json",
        "x-request-id": requestId,
        ...init.headers,
      },
      signal: controller.signal,
      cache: "no-store",
    });

    const body = await response.json().catch(() => null);

    if (!response.ok) {
      const problem = body && typeof body === "object" ? (body as ProblemDetailBody) : null;
      return {
        ok: false,
        status: response.status,
        error: {
          code: problem?.code ?? "PREM3_API_ERROR",
          message: problem?.detail ?? `prem3-api returned ${response.status}.`,
          requestId: problem?.request_id ?? requestId,
          title: problem?.title,
          errors: problem?.errors ?? undefined,
        },
      };
    }

    return { ok: true, data: body as T };
  } catch (cause) {
    const timedOut = cause instanceof Error && cause.name === "AbortError";
    return localError(
      502,
      timedOut ? "PREM3_API_TIMEOUT" : "PREM3_API_UNREACHABLE",
      timedOut ? `prem3-api did not respond within ${REQUEST_TIMEOUT_MS}ms.` : "prem3-api request failed.",
      requestId,
    );
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Authenticated call -- requires a signed-in Clerk session and forwards the
 * verified session token as `Authorization: Bearer`. Use for every endpoint
 * except prem3-api's genuinely public ones (health, ready, plan catalog --
 * no `HTTPBearer` security requirement in the frozen OpenAPI contract); see
 * callPublicPreM3Api for those.
 */
export async function callPreM3Api<T>(path: string, init: RequestInit = {}): Promise<PreM3ApiResult<T>> {
  const requestId = globalThis.crypto.randomUUID();

  const { userId, getToken } = await auth();
  if (!userId) {
    return localError(401, "UNAUTHENTICATED", "Sign in required.", requestId);
  }

  const token = await getToken();
  return performRequest<T>(path, init, token, requestId);
}

/**
 * Unauthenticated call for prem3-api's genuinely public routes (`GET
 * /healthz`, `/readyz`, `/v1/catalog/plans`) -- never requires a signed-in
 * session, never forwards a Clerk token. Using callPreM3Api for these would
 * incorrectly gate a public endpoint behind sign-in.
 */
export async function callPublicPreM3Api<T>(path: string, init: RequestInit = {}): Promise<PreM3ApiResult<T>> {
  const requestId = globalThis.crypto.randomUUID();
  return performRequest<T>(path, init, null, requestId);
}

/**
 * Maps a successful result's data through `transform`, passing an error
 * result through unchanged. Every adapter that translates prem3-api's real
 * wire shapes (WorkspaceResponse, DatasetResponse, MeResponse, ...) into
 * this frontend's presentation types (ProjectSummary, DatasetSummary,
 * BillingSummary, ...) uses this rather than a raw type cast.
 */
export function mapPreM3ApiResult<From, To>(
  result: PreM3ApiResult<From>,
  transform: (value: From) => To,
): PreM3ApiResult<To> {
  return result.ok ? { ok: true, data: transform(result.data) } : result;
}
