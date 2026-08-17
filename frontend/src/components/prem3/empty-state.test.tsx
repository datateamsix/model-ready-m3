import { Inbox } from "lucide-react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "./empty-state";

describe("EmptyState", () => {
  it("renders a title and description", () => {
    render(<EmptyState icon={Inbox} title="No runs yet" description="Start a new assessment to see it here." />);
    expect(screen.getByText("No runs yet")).toBeInTheDocument();
    expect(screen.getByText("Start a new assessment to see it here.")).toBeInTheDocument();
  });
});
