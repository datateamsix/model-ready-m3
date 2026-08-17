import { afterEach, describe, expect, it, vi } from "vitest";

const mockAuth = vi.fn();
vi.mock("@clerk/nextjs/server", () => ({
  auth: () => mockAuth(),
}));

import { callPreM3Api } from "./prem3-api-client";

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

  it("surfaces the backend's own typed error body on a non-2xx response", async () => {
    mockAuth.mockResolvedValue({ userId: "user_123", getToken: async () => "session-token" });
    vi.stubEnv("PREM3_API_BASE_URL", "https://prem3-api.example.com");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "PLAN_NOT_FOUND", message: "no such plan", requestId: "r1" } }), {
        status: 404,
      }),
    );

    const result = await callPreM3Api("v1/billing/checkout");

    expect(result).toEqual({
      ok: false,
      status: 404,
      error: { code: "PLAN_NOT_FOUND", message: "no such plan", requestId: "r1" },
    });
  });

  it("falls back to a generic typed error when the backend's error body doesn't match the contract", async () => {
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
});
