import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import { CheckoutSuccessRefresher } from "./checkout-success-refresher";

const mockRefresh = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: mockRefresh }),
  useSearchParams: () => mockSearchParams,
}));

describe("CheckoutSuccessRefresher", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockRefresh.mockReset();
    mockSearchParams = new URLSearchParams();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("never refreshes when checkout=success isn't present -- no polling for the ordinary case", () => {
    mockSearchParams = new URLSearchParams();
    render(<CheckoutSuccessRefresher />);

    vi.advanceTimersByTime(20_000);

    expect(mockRefresh).not.toHaveBeenCalled();
  });

  it("re-reads the server projection on an interval after a successful Checkout redirect", () => {
    mockSearchParams = new URLSearchParams("checkout=success");
    render(<CheckoutSuccessRefresher />);

    vi.advanceTimersByTime(2_000);
    expect(mockRefresh).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(2_000);
    expect(mockRefresh).toHaveBeenCalledTimes(2);
  });

  it("stops after a bounded number of attempts -- never polls forever", () => {
    mockSearchParams = new URLSearchParams("checkout=success");
    render(<CheckoutSuccessRefresher />);

    vi.advanceTimersByTime(20_000);

    expect(mockRefresh).toHaveBeenCalledTimes(5);
  });

  it("renders nothing -- it never itself represents entitlement state", () => {
    mockSearchParams = new URLSearchParams("checkout=success");
    const { container } = render(<CheckoutSuccessRefresher />);

    expect(container).toBeEmptyDOMElement();
  });
});
