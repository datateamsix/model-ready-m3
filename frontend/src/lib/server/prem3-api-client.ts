import { auth } from "@clerk/nextjs/server";

/**
 * The server-side (never client-bundled) call path into `prem3-api`, shared
 * by the generic BFF route (src/app/api/prem3/[...path]/route.ts, for any
 * browser-originated call) and by Server Components/Actions that can call
 * straight through without a self-referential HTTP hop -- M2-07's Billing
 * settings page and actions are the first caller.
 *
 * `PREM3_API_BASE_URL` is server-only and unset in this repo: there is no
 * deployed `prem3-api` REST surface yet (docs/contracts/BACKEND_REQUESTS.md
 * REQ-003, REQ-011..014, all NOT STARTED). Every call fails loudly with a
 * typed error in that case, matching the documented-gap pattern already
 * established by ApiPreM3DataSource (src/lib/adapters/api-data-source.ts).
 */

const REQUEST_TIMEOUT_MS = 15_000;

export interface PreM3ApiError {
  code: string;
  message: string;
  requestId: string;
}

export type PreM3ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: number; error: PreM3ApiError };

export async function callPreM3Api<T>(path: string, init: RequestInit = {}): Promise<PreM3ApiResult<T>> {
  const requestId = globalThis.crypto.randomUUID();

  const { userId, getToken } = await auth();
  if (!userId) {
    return {
      ok: false,
      status: 401,
      error: { code: "UNAUTHENTICATED", message: "Sign in required.", requestId },
    };
  }

  const baseUrl = process.env.PREM3_API_BASE_URL;
  if (!baseUrl) {
    return {
      ok: false,
      status: 503,
      error: {
        code: "PREM3_API_NOT_CONFIGURED",
        message:
          "No prem3-api backend is configured yet (PREM3_API_BASE_URL unset). See " +
          "docs/contracts/BACKEND_REQUESTS.md REQ-003 and REQ-013.",
        requestId,
      },
    };
  }

  const token = await getToken();
  const targetUrl = new URL(path.replace(/^\//, ""), baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(targetUrl, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        "content-type": "application/json",
        "x-request-id": requestId,
        ...init.headers,
      },
      signal: controller.signal,
      cache: "no-store",
    });

    const body = await response.json().catch(() => null);

    if (!response.ok) {
      const backendError = body && typeof body === "object" ? (body as { error?: PreM3ApiError }).error : undefined;
      return {
        ok: false,
        status: response.status,
        error: backendError ?? {
          code: "PREM3_API_ERROR",
          message: `prem3-api returned ${response.status}.`,
          requestId,
        },
      };
    }

    return { ok: true, data: body as T };
  } catch (cause) {
    const timedOut = cause instanceof Error && cause.name === "AbortError";
    return {
      ok: false,
      status: 502,
      error: {
        code: timedOut ? "PREM3_API_TIMEOUT" : "PREM3_API_UNREACHABLE",
        message: timedOut
          ? `prem3-api did not respond within ${REQUEST_TIMEOUT_MS}ms.`
          : "prem3-api request failed.",
        requestId,
      },
    };
  } finally {
    clearTimeout(timeout);
  }
}
