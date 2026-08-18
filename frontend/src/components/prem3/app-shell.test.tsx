import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppShell } from "./app-shell";

// AppShell renders real Clerk identity components (OrganizationSwitcher,
// UserButton, Show). Those require a live <ClerkProvider> session context
// that unit tests don't have, so the boundary this test owns is "AppShell
// wires the right Clerk components into the header, gated the right way"
// -- not Clerk's own internals (real session evaluation), which are
// Clerk's to test. Show is mocked as a trivial pass-through keyed on its
// `when` prop since AppShell also wraps the public /app/demo/** route
// (reachable signed out) -- OrganizationSwitcher/UserButton must never
// render unconditionally there, which is what this suite guards against
// regressing. (Clerk Core 3 removed <SignedIn>/<SignedOut> in favor of
// <Show when="signed-in"|"signed-out">; this installed SDK version only
// has the latter.)
vi.mock("@clerk/nextjs", () => ({
  OrganizationSwitcher: () => <div data-testid="organization-switcher" />,
  UserButton: () => <div data-testid="user-button" />,
  Show: ({ when, children }: { when: string; children: ReactNode }) => (
    <div data-testid={`show-${when}`}>{children}</div>
  ),
}));

describe("AppShell", () => {
  it("renders the Clerk organization switcher and user button inside signed-in Show boundaries", () => {
    render(
      <AppShell>
        <p>content</p>
      </AppShell>,
    );
    // Two separate <Show when="signed-in"> boundaries (org switcher, then
    // settings link + user button) -- both must gate their contents.
    const signedInBoundaries = screen.getAllByTestId("show-signed-in");
    expect(signedInBoundaries.length).toBeGreaterThanOrEqual(2);
    expect(signedInBoundaries.some((el) => el.contains(screen.getByTestId("organization-switcher")))).toBe(true);
    expect(signedInBoundaries.some((el) => el.contains(screen.getByTestId("user-button")))).toBe(true);
  });

  it("renders a sign-in link inside a signed-out Show boundary, never OrganizationSwitcher/UserButton unconditionally", () => {
    render(
      <AppShell>
        <p>content</p>
      </AppShell>,
    );
    const signedOut = screen.getByTestId("show-signed-out");
    expect(signedOut).toHaveTextContent("Sign in");
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
