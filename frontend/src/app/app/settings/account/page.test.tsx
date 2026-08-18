import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "./page";

// Same boundary as app-shell.test.tsx: UserProfile needs a live ClerkProvider
// session context unit tests don't have, so this test owns "the account page
// renders Clerk's UserProfile", not Clerk's own internals.
vi.mock("@clerk/nextjs", () => ({
  UserProfile: () => <div data-testid="clerk-user-profile" />,
}));

describe("Account settings page", () => {
  it("renders Clerk's UserProfile", () => {
    render(<Page />);
    expect(screen.getByTestId("clerk-user-profile")).toBeInTheDocument();
  });
});
