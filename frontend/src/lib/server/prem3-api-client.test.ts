import { afterEach, describe, expect, it, vi } from "vitest";

const mockAuth = vi.fn();
vi.mock("@clerk/nextjs/server", () => ({
  auth: () => mockAuth(),
}));

import { callPreM3Api, callPublicPreM3Api } from "./prem3-api-client";

describe("callPreM3Api", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    mockAuth.mockReset();
    vi.restoreAllMocks();
  });

  it("returns 401 without ever calling fetch when there is no signed-in session", async () => {
    mockAuth.mockResolvedValue({ userId: null, getToken: async () => null });
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const result = await callPreM3Api("v1/me");

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.status).toBe(401);
      expect(result.error.code).toBe("UNAUTHENTICATED");
    }
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("fails loudly with a typed 503 when PREM3_API_BASE_URL is unset, instead of fabricating a response", async () => {
    mockAuth.mockResolvedValue({ userId: "user_123", getToken: async () => "session-token" });
    vi.stubEnv("PREM3_API_BASE_URL", "");

    const result = await callPreM3Api("v1/me");

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.status).toBe(503);
      expect(result.error.code).toBe("PREM3_API_NOT_CONFIGURED");
    }
  });

  it("returns typed data straight through on a successful response", async () => {
    mockAuth.mockResolvedValue({ userId: "user_123", getToken: async () => "session-token" });
    vi.stubEnv("PREM3_API_BASE_URL", "https://prem3-api.example.com");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ plan: "project" }), { status: 200 }));

    const result = await callPreM3Api<{ plan: string }>("v1/me");

    expect(result).toEqual({ ok: true, data: { plan: "project" } });
  });

  it("parses the real ProblemDetail (application/problem+json) shape on a non-2xx response, keying off code not detail prose", async () => {
    mockAuth.mockResolvedValue({ userId: "user_123", getToken: async () => "session-token" });
    vi.stubEnv("PREM3_API_BASE_URL", "https://prem3-api.example.com");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "about:blank",
          title: "Entitlement Denied",
          status: 403,
          detail: "This tenant's plan does not permit another active project.",
          code: "PROJECT_LIMIT_REACHED",
          request_id: "req-abc",
        }),
        { status: 403, headers: { "content-type": "application/problem+json" } },
      ),
    );

    const result = await callPreM3Api("v1/workspaces");

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.status).toBe(403);
      expect(result.error.code).toBe("PROJECT_LIMIT_REACHED");
      expect(result.error.requestId).toBe("req-abc");
    }
  });

  it("passes through ProblemDetail's field-level validation errors when present", async () => {
    mockAuth.mockResolvedValue({ userId: "user_123", getToken: async () => "session-token" });
    vi.stubEnv("PREM3_API_BASE_URL", "https://prem3-api.example.com");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "about:blank",
          title: "Validation Error",
          status: 422,
          detail: "Invalid request.",
          code: "VALIDATION_ERROR",
          request_id: "req-1",
          errors: [{ field: "name", message: "must not be empty" }],
        }),
        { status: 422 },
      ),
    );

    const result = await callPreM3Api("v1/workspaces", { method: "POST" });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.errors).toEqual([{ field: "name", message: "must not be empty" }]);
    }
  });

  it("falls back to a generic typed error when the backend's error body isn't a ProblemDetail", async () => {
    mockAuth.mockResolvedValue({ userId: "user_123", getToken: async () => "session-token" });
    vi.stubEnv("PREM3_API_BASE_URL", "https://prem3-api.example.com");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("not json", { status: 500 }));

    const result = await callPreM3Api("v1/me");

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.status).toBe(500);
      expect(result.error.code).toBe("PREM3_API_ERROR");
    }
  });

  it("returns a typed unreachable error when fetch itself throws", async () => {
    mockAuth.mockResolvedValue({ userId: "user_123", getToken: async () => "session-token" });
    vi.stubEnv("PREM3_API_BASE_URL", "https://prem3-api.example.com");
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network down"));

    const result = await callPreM3Api("v1/me");

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.status).toBe(502);
      expect(result.error.code).toBe("PREM3_API_UNREACHABLE");
    }
  });

  it("returns a typed timeout error when the request is aborted", async () => {
    mockAuth.mockResolvedValue({ userId: "user_123", getToken: async () => "session-token" });
    vi.stubEnv("PREM3_API_BASE_URL", "https://prem3-api.example.com");
    vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      const abortError = new Error("aborted");
      abortError.name = "AbortError";
      return Promise.reject(abortError);
    });

    const result = await callPreM3Api("v1/me");

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.status).toBe(502);
      expect(result.error.code).toBe("PREM3_API_TIMEOUT");
    }
  });

  it("forwards the Clerk session token as a Bearer header", async () => {
    mockAuth.mockResolvedValue({ userId: "user_123", getToken: async () => "the-token" });
    vi.stubEnv("PREM3_API_BASE_URL", "https://prem3-api.example.com");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200 }));

    await callPreM3Api("v1/me");

    const [, requestInit] = fetchSpy.mock.calls[0];
    const headers = requestInit?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer the-token");
  });
});

describe("callPublicPreM3Api", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    mockAuth.mockReset();
    vi.restoreAllMocks();
  });

  it("never calls auth() or requires a signed-in session -- the public catalog endpoint must work signed out", async () => {
    vi.stubEnv("PREM3_API_BASE_URL", "https://prem3-api.example.com");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ plans: [] }), { status: 200 }));

    const result = await callPublicPreM3Api("v1/catalog/plans");

    expect(mockAuth).not.toHaveBeenCalled();
    expect(result).toEqual({ ok: true, data: { plans: [] } });
  });

  it("never forwards an Authorization header", async () => {
    vi.stubEnv("PREM3_API_BASE_URL", "https://prem3-api.example.com");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}", { status: 200 }));

    await callPublicPreM3Api("v1/catalog/plans");

    const [, requestInit] = fetchSpy.mock.calls[0];
    const headers = requestInit?.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it("still fails loudly with a typed 503 when PREM3_API_BASE_URL is unset", async () => {
    vi.stubEnv("PREM3_API_BASE_URL", "");

    const result = await callPublicPreM3Api("v1/catalog/plans");

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.status).toBe(503);
      expect(result.error.code).toBe("PREM3_API_NOT_CONFIGURED");
    }
  });
});
