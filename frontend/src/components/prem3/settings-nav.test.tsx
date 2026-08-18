import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SettingsNav } from "./settings-nav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/app/settings/billing",
}));

describe("SettingsNav", () => {
  it("renders Account and Billing tabs and marks the active one", () => {
    render(<SettingsNav />);
    expect(screen.getByRole("link", { name: "Account" })).toBeInTheDocument();
    const billing = screen.getByRole("link", { name: "Billing" });
    expect(billing).toHaveAttribute("aria-current", "page");
  });
});
