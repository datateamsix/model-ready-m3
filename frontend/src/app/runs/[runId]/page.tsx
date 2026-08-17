import { Eye, History, SearchX } from "lucide-react";
import { AppShell } from "@/components/prem3/app-shell";
import { PageHeader } from "@/components/prem3/page-header";
import { RunTimeline } from "@/components/prem3/run-timeline";
import { MetricRow } from "@/components/prem3/metric-row";
import { ModelReadyCard } from "@/components/prem3/model-ready-card";
import { ExperienceEpisodeCard } from "@/components/prem3/experience-episode-card";
import { ReflectionCard } from "@/components/prem3/reflection-card";
import { DomainViewCard } from "@/components/prem3/domain-view-card";
import { DomainViewDiff } from "@/components/prem3/domain-view-diff";
import { ProofDrawer } from "@/components/prem3/proof-drawer";
import { ResponsePanel } from "@/components/prem3/response-panel";
import { SectionHeader } from "@/components/prem3/section-header";
import { EmptyState } from "@/components/prem3/empty-state";
import { preM3DataSource } from "@/lib/adapters/fixture-data-source";
import type { ResponseMetric } from "@/types/response";

function runMetrics(run: NonNullable<Awaited<ReturnType<typeof preM3DataSource.getRun>>>): ResponseMetric[] {
  return [
    { metric_id: "detected-issues", label: "Detected issues", value: run.detected_issue_count, evidence_id: "run.detected_issue_count", unit: null },
    { metric_id: "resolved-issues", label: "Resolved issues", value: run.resolved_issue_count, evidence_id: "run.resolved_issue_count", unit: null },
    { metric_id: "open-issues", label: "Open issues", value: run.open_issue_count, evidence_id: "run.open_issue_count", unit: null },
    { metric_id: "geos", label: "Geos", value: run.geos.length, evidence_id: "run.geos", unit: null },
    { metric_id: "periods", label: "Periods", value: run.period_count, evidence_id: "run.period_count", unit: run.grain },
  ];
}

export default async function Page({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const run = await preM3DataSource.getRun(runId);

  if (!run) {
    return (
      <AppShell>
        <EmptyState icon={SearchX} title="Run not found" description={`No run matches "${runId}".`} />
      </AppShell>
    );
  }

  const [responses, artifacts, experience, domainView] = await Promise.all([
    preM3DataSource.getRunResponses(runId),
    preM3DataSource.getArtifacts(runId),
    preM3DataSource.getExperience(runId),
    preM3DataSource.getDomainView(),
  ]);

  return (
    <AppShell>
      <div className="flex flex-col gap-10">
        <PageHeader
          eyebrow={run.business}
          title={run.dataset_label}
          subtitle={`Run ${run.run_id}`}
          actions={<ProofDrawer artifacts={artifacts} />}
        />

        <RunTimeline currentStage={run.stage} failed={run.failed} />

        <MetricRow metrics={runMetrics(run)} />

        {responses.assessment && (
          <section className="flex flex-col gap-4">
            <SectionHeader icon={Eye} title="Assessment" />
            <ResponsePanel response={responses.assessment} />
          </section>
        )}

        {responses.feasibility && <ResponsePanel response={responses.feasibility} />}
        {responses.semanticInterview && <ResponsePanel response={responses.semanticInterview} />}
        {responses.scopeScenario && <ResponsePanel response={responses.scopeScenario} />}
        {responses.guidedRemediation && <ResponsePanel response={responses.guidedRemediation} />}
        {responses.officialMeridian && <ResponsePanel response={responses.officialMeridian} />}

        {responses.modelReady?.gate_evidence && (
          <ModelReadyCard
            title={responses.modelReady.title}
            summary={responses.modelReady.summary}
            status={responses.modelReady.status}
            gate={responses.modelReady.gate_evidence}
          />
        )}

        <section className="flex flex-col gap-4">
          <SectionHeader icon={History} title="Experience, reflection, and learning" />
          {experience ? (
            <>
              <ExperienceEpisodeCard episode={experience.episode} />
              {experience.reflection && <ReflectionCard reflection={experience.reflection} />}
            </>
          ) : (
            <EmptyState icon={History} title="No experience episode yet" description="This run has not been evaluated by MEL." />
          )}
          <DomainViewCard domainView={domainView} />
          <DomainViewDiff
            diff={null}
            fromVersion={domainView.domain_view_version}
            toVersion={domainView.domain_view_version}
          />
          {responses.learning && <ResponsePanel response={responses.learning} />}
          {responses.domainView && <ResponsePanel response={responses.domainView} />}
        </section>
      </div>
    </AppShell>
  );
}
