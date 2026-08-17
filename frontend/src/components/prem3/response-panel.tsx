import { BookOpen, FileSearch, Info, Route, ShieldCheck, Sparkles, Workflow } from "lucide-react";
import { ActionCard } from "./action-card";
import { FindingCard } from "./finding-card";
import { InsightCard } from "./insight-card";
import { MeridianFindingCard } from "./meridian-finding-card";
import { MetricRow } from "./metric-row";
import { QuestionCard } from "./question-card";
import { ScenarioCard } from "./scenario-card";
import { SectionHeader } from "./section-header";
import { SourceBadge } from "./source-badge";
import { StatusHeader } from "./status-header";
import type { StructuredResponse } from "@/types/response";

export function ResponsePanel({ response }: { response: StructuredResponse }) {
  return (
    <div className="flex flex-col gap-4">
      <StatusHeader title={response.title} summary={response.summary} status={response.status} />
      <MetricRow metrics={response.metrics} />

      {response.findings.length > 0 && (
        <div className="flex flex-col gap-3">
          <SectionHeader icon={FileSearch} title="Findings" count={response.findings.length} />
          {response.findings.map((finding) => (
            <FindingCard key={finding.finding_id} finding={finding} />
          ))}
        </div>
      )}

      {response.insights.length > 0 && (
        <div className="flex flex-col gap-3">
          <SectionHeader icon={Sparkles} title="Insights" count={response.insights.length} />
          {response.insights.map((insight) => (
            <InsightCard key={insight.insight_id} insight={insight} />
          ))}
        </div>
      )}

      {response.actions.length > 0 && (
        <div className="flex flex-col gap-3">
          <SectionHeader icon={Workflow} title="Actions" count={response.actions.length} />
          {response.actions.map((action) => (
            <ActionCard key={action.action_id} action={action} />
          ))}
        </div>
      )}

      {response.questions.length > 0 && (
        <div className="flex flex-col gap-3">
          <SectionHeader icon={Info} title="Semantic questions" count={response.questions.length} />
          {response.questions.map((question) => (
            <QuestionCard key={question.question_id} question={question} />
          ))}
        </div>
      )}

      {response.scenarios.length > 0 && (
        <div className="flex flex-col gap-3">
          <SectionHeader icon={Route} title="Scope scenarios" count={response.scenarios.length} />
          {response.scenarios.map((scenario) => (
            <ScenarioCard key={scenario.scenario_id} scenario={scenario} />
          ))}
        </div>
      )}

      {response.official_meridian.length > 0 && (
        <div className="flex flex-col gap-3">
          <SectionHeader icon={ShieldCheck} title="Official Meridian" count={response.official_meridian.length} />
          {response.official_meridian.map((finding) => (
            <MeridianFindingCard key={finding.finding_id} finding={finding} />
          ))}
        </div>
      )}

      {response.sources.length > 0 && (
        <div className="flex flex-col gap-2">
          <SectionHeader icon={BookOpen} title="Sources" count={response.sources.length} />
          <div className="flex flex-wrap gap-2">
            {response.sources.map((source) => (
              <SourceBadge key={source} sourceRef={source} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
