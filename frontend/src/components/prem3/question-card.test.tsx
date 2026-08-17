import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { QuestionCard } from "./question-card";
import type { SemanticQuestionCard } from "@/types/response";

const question: SemanticQuestionCard = {
  question_id: "q-1",
  question: "Does the Music Center promotion indicator represent paid or organic activity?",
  why_asking: "The control's provenance is ambiguous in the source export.",
  triggered_by: "controls_weekly.csv",
  trigger_evidence: [],
  what_changes: "Whether the field is scoped as a control or as a media variable.",
  owner: "ANALYST",
  decision_authority: "MODELER_REVIEW_REQUIRED",
  affected_scope: ["controls_weekly.csv"],
  open_human_question: true,
  prior_provenance: null,
};

describe("QuestionCard", () => {
  it("renders the question, why PreM3 is asking, and marks it open", () => {
    render(<QuestionCard question={question} />);
    expect(screen.getByText(question.question)).toBeInTheDocument();
    expect(screen.getByText(question.why_asking)).toBeInTheDocument();
    expect(screen.getByText(/open question/i)).toBeInTheDocument();
  });
});
