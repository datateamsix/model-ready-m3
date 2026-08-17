import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DomainViewCard } from "./domain-view-card";
import { domainViewV1 } from "@/lib/fixtures/domain-view";

describe("DomainViewCard", () => {
  it("renders the real DOMAIN_VIEW version and claim count", () => {
    render(<DomainViewCard domainView={domainViewV1} />);
    expect(screen.getByText("DOMAIN_VIEW 1.0.0")).toBeInTheDocument();
    expect(screen.getByText("35")).toBeInTheDocument();
  });

  it("shows the mission's exact honest zero-promoted-lesson copy when promoted_lesson_count is 0", () => {
    render(<DomainViewCard domainView={domainViewV1} />);
    expect(screen.getByText("NO EXPERIENTIAL LESSONS PROMOTED")).toBeInTheDocument();
    expect(
      screen.getByText(
        /PreM3 has captured and reflected on completed assignments, but no candidate has yet passed the promotion bar\./,
      ),
    ).toBeInTheDocument();
  });

  it("does not show the zero-lesson copy when lessons have been promoted", () => {
    render(<DomainViewCard domainView={{ ...domainViewV1, promoted_lesson_count: 2 }} />);
    expect(screen.queryByText("NO EXPERIENTIAL LESSONS PROMOTED")).not.toBeInTheDocument();
  });
});
