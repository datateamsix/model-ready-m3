import type { SemanticQuestionCard } from "@/types/response";

export function QuestionCard({ question }: { question: SemanticQuestionCard }) {
  return (
    <div className="rounded-lg border border-prem3-cool-gray bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-prem3-navy">{question.question}</p>
        {question.open_human_question && (
          <span className="shrink-0 rounded border border-prem3-indigo/30 bg-prem3-indigo/10 px-2 py-0.5 text-xs font-medium text-prem3-indigo">
            Open question
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{question.why_asking}</p>
      <p className="mt-2 text-xs text-prem3-navy/70">
        <span className="font-semibold uppercase tracking-wide">What changes: </span>
        {question.what_changes}
      </p>
      <p className="mt-1 text-xs text-prem3-navy/70">
        <span className="font-semibold uppercase tracking-wide">Owner: </span>
        {question.owner}
      </p>
    </div>
  );
}
