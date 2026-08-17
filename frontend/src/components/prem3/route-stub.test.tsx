import { Compass } from "lucide-react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RouteStub } from "./route-stub";

describe("RouteStub", () => {
  it("renders the title and description it's given", () => {
    render(<RouteStub icon={Compass} title="Pricing" description="Lands in M2-05." />);
    expect(screen.getByText("Pricing")).toBeInTheDocument();
    expect(screen.getByText("Lands in M2-05.")).toBeInTheDocument();
  });
});
