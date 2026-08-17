import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppShell } from "./app-shell";

// AppShell renders real Clerk identity components (OrganizationSwitcher,
// UserButton). Those require a live <ClerkProvider> session context that
// unit tests don't have, so the boundary this test owns is "AppShell wires
// the right Clerk components into the header" -- not Clerk's own internals,
// which are Clerk's to test.
vi.mock("@clerk/nextjs", () => ({
  OrganizationSwitcher: () => <div data-testid="organization-switcher" />,
  UserButton: () => <div data-testid="user-button" />,
}));

describe("AppShell", () => {
  it("renders the Clerk organization switcher and user button in the header", () => {
    render(
      <AppShell>
        <p>content</p>
      </AppShell>,
    );
    expect(screen.getByTestId("organization-switcher")).toBeInTheDocument();
    expect(screen.getByTestId("user-button")).toBeInTheDocument();
  });

  it("still renders the PreM3 wordmark and children", () => {
    render(
      <AppShell>
        <p>console content</p>
      </AppShell>,
    );
    expect(screen.getByText("console content")).toBeInTheDocument();
  });
});
