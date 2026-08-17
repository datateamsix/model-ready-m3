import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PlannerExperience } from "./planner-experience";

vi.mock("@clerk/nextjs", () => ({
  useUser: () => ({ isSignedIn: false, isLoaded: true }),
}));

async function completeIntake(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Start planning" }));
  // Section 1: About your business
  await user.click(screen.getByRole("button", { name: "Next" }));
  // Section 2: Channels & platforms
  await user.click(screen.getByRole("button", { name: "Next" }));
  // Section 3: Data readiness
  await user.click(screen.getByRole("button", { name: "Next" }));
  // Section 4: Your goal
  await user.click(screen.getByRole("button", { name: "Show my brief" }));
}

describe("PlannerExperience", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("makes zero network requests through the entire anonymous intake-to-result flow", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const user = userEvent.setup();
    render(<PlannerExperience />);

    await completeIntake(user);

    expect(await screen.findByText(/Planning guidance/)).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("produces a result that carries the planning-guidance disclaimer, never a readiness certification", async () => {
    const user = userEvent.setup();
    render(<PlannerExperience />);

    await completeIntake(user);

    expect(await screen.findByText(/not a MODEL_READY or COLLECTION_READY assessment/)).toBeInTheDocument();
  });

  it("lets the user start over, discarding the stored draft", async () => {
    const user = userEvent.setup();
    render(<PlannerExperience />);

    await completeIntake(user);
    await user.click(await screen.findByRole("button", { name: "Start over" }));

    expect(screen.getByRole("button", { name: "Start planning" })).toBeInTheDocument();
    expect(window.localStorage.getItem("prem3.planner.draft.v1")).toBeNull();
  });
});
