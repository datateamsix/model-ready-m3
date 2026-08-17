import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { GET } from "./route";

const mockAuth = vi.fn();
vi.mock("@clerk/nextjs/server", () => ({
  auth: () => mockAuth(),
}));

function params(path: string[]) {
  return { params: Promise.resolve({ path }) };
}

describe("/api/prem3/[...path] (BFF)", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    mockAuth.mockReset();
  });

  it("returns 401 when there is no signed-in session -- never forwards an unauthenticated request", async () => {
    mockAuth.mockResolvedValue({ userId: null, getToken: async () => null });
    const req = new NextRequest("http://localhost/api/prem3/v1/me");

    const response = await GET(req, params(["v1", "me"]));

    expect(response.status).toBe(401);
    const body = await response.json();
    expect(body.error.code).toBe("UNAUTHENTICATED");
  });

  it("fails loudly with a typed 503 when PREM3_API_BASE_URL is unset, instead of fabricating a response", async () => {
    mockAuth.mockResolvedValue({ userId: "user_123", getToken: async () => "session-token" });
    vi.stubEnv("PREM3_API_BASE_URL", "");
    const req = new NextRequest("http://localhost/api/prem3/v1/me");

    const response = await GET(req, params(["v1", "me"]));

    expect(response.status).toBe(503);
    const body = await response.json();
    expect(body.error.code).toBe("PREM3_API_NOT_CONFIGURED");
  });

  it("always returns a request ID header, generating one if the caller didn't send one", async () => {
    mockAuth.mockResolvedValue({ userId: "user_123", getToken: async () => "session-token" });
    const req = new NextRequest("http://localhost/api/prem3/v1/me");

    const response = await GET(req, params(["v1", "me"]));

    expect(response.headers.get("x-request-id")).toBeTruthy();
  });

  it("echoes a caller-supplied x-request-id back on the response", async () => {
    mockAuth.mockResolvedValue({ userId: "user_123", getToken: async () => "session-token" });
    const req = new NextRequest("http://localhost/api/prem3/v1/me", {
      headers: { "x-request-id": "req-abc-123" },
    });

    const response = await GET(req, params(["v1", "me"]));

    expect(response.headers.get("x-request-id")).toBe("req-abc-123");
  });
});
