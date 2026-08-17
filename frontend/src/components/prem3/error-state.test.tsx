import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ErrorState } from "./error-state";

describe("ErrorState", () => {
  it("renders the title/description and calls onRetry when the retry button is used", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(<ErrorState title="Could not load run" description="The run could not be found." onRetry={onRetry} />);

    expect(screen.getByText("Could not load run")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("omits the retry button when onRetry is not provided", () => {
    render(<ErrorState title="Could not load run" description="The run could not be found." />);
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });
});
