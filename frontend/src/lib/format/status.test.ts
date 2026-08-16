import { describe, expect, it } from "vitest";
import { STATUS_LABEL, severityTone, statusTone } from "./status";

describe("statusTone", () => {
  it("maps READY and PASS to the positive tone", () => {
    expect(statusTone("READY")).toBe("positive");
    expect(statusTone("PASS")).toBe("positive");
  });

  it("maps BLOCKED and USER_ACTION_REQUIRED to the critical tone", () => {
    expect(statusTone("BLOCKED")).toBe("critical");
    expect(statusTone("USER_ACTION_REQUIRED")).toBe("critical");
  });

  it("maps REVIEW_RECOMMENDED and MODELER_REVIEW_REQUIRED to the warning tone", () => {
    expect(statusTone("REVIEW_RECOMMENDED")).toBe("warning");
    expect(statusTone("MODELER_REVIEW_REQUIRED")).toBe("warning");
  });

  it("has a human label for every PresentationStatus value", () => {
    expect(STATUS_LABEL.PENDING).toBe("Pending");
    expect(STATUS_LABEL.NOT_APPLICABLE).toBe("Not applicable");
  });

  it("preserves official Meridian ERROR as critical without softening it", () => {
    expect(severityTone("ERROR")).toBe("critical");
    expect(severityTone("ATTENTION")).toBe("warning");
    expect(severityTone("INFO")).toBe("neutral");
  });
});
