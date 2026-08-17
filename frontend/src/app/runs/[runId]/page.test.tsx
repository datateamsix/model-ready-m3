import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "./page";

describe("/runs/[runId] workspace", () => {
  it("renders the Music Center run header, timeline, MODEL_READY gate, and honest zero-learning state", async () => {
    render(await Page({ params: Promise.resolve({ runId: "music-center-dataset-a-demo" }) }));

    // "Music Center" is PageHeader's eyebrow -- a <span> deliberately
    // separate from the <h1> (see Task 13's own PageHeader test), not part
    // of any heading's accessible name, so this asserts it as text rather
    // than as a heading match.
    expect(screen.getByText("Music Center")).toBeInTheDocument();
    expect(screen.getByText("BigQuery model artifact")).toBeInTheDocument();
    expect(screen.getByText("NO EXPERIENTIAL LESSONS PROMOTED")).toBeInTheDocument();
    expect(screen.getByText(/reflection is evidence, not a decision/i)).toBeInTheDocument();
  });

  it("renders an honest not-found state for an unknown run id instead of throwing", async () => {
    render(await Page({ params: Promise.resolve({ runId: "does-not-exist" }) }));
    expect(screen.getByText(/run not found/i)).toBeInTheDocument();
  });
});
