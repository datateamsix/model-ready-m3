import { auth } from "@clerk/nextjs/server";
import { NextResponse, type NextRequest } from "next/server";
import { randomUUID } from "node:crypto";

/**
 * The BFF boundary for every authenticated call to `prem3-api` (M2-06).
 * Pages and client components never call `prem3-api` directly and never
 * hold its base URL or a Clerk token themselves -- they call this route,
 * which resolves the caller's identity server-side, forwards a verified
 * session token, and passes the backend's response straight through.
 *
 * `PREM3_API_BASE_URL` is intentionally server-only (no NEXT_PUBLIC_
 * prefix): it never reaches the client bundle. It is also not configured
 * anywhere in this repo yet -- there is no deployed `prem3-api` REST
 * surface for the frontend to call (see docs/contracts/BACKEND_REQUESTS.md
 * REQ-003 and REQ-011 through REQ-014, all NOT STARTED). This handler
 * fails loudly with a typed error in that case rather than fabricating a
 * response, matching the documented-gap pattern already established by
 * ApiPreM3DataSource (src/lib/adapters/api-data-source.ts).
 */

const REQUEST_TIMEOUT_MS = 15_000;

interface PreM3ApiError {
  error: {
    code: string;
    message: string;
    requestId: string;
  };
}

function backendNotConfigured(requestId: string): NextResponse<PreM3ApiError> {
  return NextResponse.json(
    {
      error: {
        code: "PREM3_API_NOT_CONFIGURED",
        message:
          "No prem3-api backend is configured (PREM3_API_BASE_URL unset). This BFF route is wired " +
          "and ready to forward authenticated requests once REQ-003/REQ-011..014 in " +
          "docs/contracts/BACKEND_REQUESTS.md are fulfilled.",
        requestId,
      },
    },
    { status: 503, headers: { "x-request-id": requestId } },
  );
}

async function proxy(req: NextRequest, path: string[]): Promise<NextResponse> {
  const incomingRequestId = req.headers.get("x-request-id");
  const requestId = incomingRequestId && incomingRequestId.length > 0 ? incomingRequestId : randomUUID();

  const { userId, getToken } = await auth();
  if (!userId) {
    return NextResponse.json(
      { error: { code: "UNAUTHENTICATED", message: "Sign in required.", requestId } } satisfies PreM3ApiError,
      { status: 401, headers: { "x-request-id": requestId } },
    );
  }

  const baseUrl = process.env.PREM3_API_BASE_URL;
  if (!baseUrl) {
    return backendNotConfigured(requestId);
  }

  const token = await getToken();
  const targetUrl = new URL(path.join("/"), baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`);
  targetUrl.search = req.nextUrl.search;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const upstream = await fetch(targetUrl, {
      method: req.method,
      headers: {
        Authorization: `Bearer ${token}`,
        "x-request-id": requestId,
        "content-type": req.headers.get("content-type") ?? "application/json",
      },
      body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.text(),
      signal: controller.signal,
    });

    const body = await upstream.text();
    return new NextResponse(body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/json",
        "x-request-id": requestId,
      },
    });
  } catch (cause) {
    const timedOut = cause instanceof Error && cause.name === "AbortError";
    return NextResponse.json(
      {
        error: {
          code: timedOut ? "PREM3_API_TIMEOUT" : "PREM3_API_UNREACHABLE",
          message: timedOut
            ? `prem3-api did not respond within ${REQUEST_TIMEOUT_MS}ms.`
            : "prem3-api request failed.",
          requestId,
        },
      } satisfies PreM3ApiError,
      { status: 502, headers: { "x-request-id": requestId } },
    );
  } finally {
    clearTimeout(timeout);
  }
}

interface RouteParams {
  params: Promise<{ path: string[] }>;
}

export async function GET(req: NextRequest, { params }: RouteParams) {
  return proxy(req, (await params).path);
}
export async function POST(req: NextRequest, { params }: RouteParams) {
  return proxy(req, (await params).path);
}
export async function PATCH(req: NextRequest, { params }: RouteParams) {
  return proxy(req, (await params).path);
}
export async function PUT(req: NextRequest, { params }: RouteParams) {
  return proxy(req, (await params).path);
}
export async function DELETE(req: NextRequest, { params }: RouteParams) {
  return proxy(req, (await params).path);
}
