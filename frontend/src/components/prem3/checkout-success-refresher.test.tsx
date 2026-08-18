import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
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
    render(<CheckoutSuccessRefresher isPending={true} />);

    act(() => {
      vi.advanceTimersByTime(20_000);
    });

    expect(mockRefresh).not.toHaveBeenCalled();
  });

  it("never refreshes once the plan is confirmed, even with checkout=success in the URL", () => {
    mockSearchParams = new URLSearchParams("checkout=success");
    render(<CheckoutSuccessRefresher isPending={false} />);

    act(() => {
      vi.advanceTimersByTime(20_000);
    });

    expect(mockRefresh).not.toHaveBeenCalled();
  });

  it("re-reads the server projection on an interval while still pending after a successful Checkout redirect", () => {
    mockSearchParams = new URLSearchParams("checkout=success");
    render(<CheckoutSuccessRefresher isPending={true} />);

    act(() => {
      vi.advanceTimersByTime(2_000);
    });
    expect(mockRefresh).toHaveBeenCalledTimes(1);

    act(() => {
      vi.advanceTimersByTime(2_000);
    });
    expect(mockRefresh).toHaveBeenCalledTimes(2);
  });

  it("stops after a bounded number of attempts -- never polls forever", () => {
    mockSearchParams = new URLSearchParams("checkout=success");
    render(<CheckoutSuccessRefresher isPending={true} />);

    act(() => {
      vi.advanceTimersByTime(20_000);
    });

    expect(mockRefresh).toHaveBeenCalledTimes(5);
  });

  it("renders nothing when there's no pending Checkout to confirm -- it never itself represents entitlement state", () => {
    mockSearchParams = new URLSearchParams();
    const { container } = render(<CheckoutSuccessRefresher isPending={true} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("shows a waiting state, not a silent no-op, while confirming a pending Checkout", () => {
    mockSearchParams = new URLSearchParams("checkout=success");
    render(<CheckoutSuccessRefresher isPending={true} />);

    expect(screen.getByRole("status")).toHaveTextContent("Confirming your upgrade");
  });

  it("offers a manual retry once polling is exhausted, and clicking it resumes polling", () => {
    mockSearchParams = new URLSearchParams("checkout=success");
    render(<CheckoutSuccessRefresher isPending={true} />);

    act(() => {
      vi.advanceTimersByTime(10_000);
    });
    expect(mockRefresh).toHaveBeenCalledTimes(5);
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    });
    expect(mockRefresh).toHaveBeenCalledTimes(6);
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
  });
});
