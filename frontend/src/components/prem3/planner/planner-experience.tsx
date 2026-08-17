"use client";

import { useEffect, useState } from "react";
import { generatePlannerResult } from "@/lib/planner/decision-engine";
import { BUSINESS_MODELS, CHANNEL_CATEGORIES, EXPORT_STATUSES, WAREHOUSE_LOCATIONS } from "@/lib/planner/manifest";
import { providersInCategory } from "@/lib/planner/provider-snapshot";
import { clearPlannerState, loadPlannerState, savePlannerState } from "@/lib/planner/storage";
import { trackPlannerEvent } from "@/lib/planner/analytics";
import { EMPTY_PLANNER_INTAKE, type PlannerIntake, type PlannerResult } from "@/lib/planner/types";
import { PlannerConversionCta } from "./planner-conversion-cta";

const SECTION_LABELS = ["About your business", "Channels & platforms", "Data readiness", "Your goal"] as const;
const LAST_SECTION_INDEX = SECTION_LABELS.length - 1;

function toggleInArray(list: string[], value: string): string[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

export function PlannerExperience() {
  const [intake, setIntake] = useState<PlannerIntake>(EMPTY_PLANNER_INTAKE);
  const [result, setResult] = useState<PlannerResult | null>(null);
  const [sectionIndex, setSectionIndex] = useState(0);
  const [started, setStarted] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  // Local-storage hydration only, never a PreM3/GCP call. This is the
  // documented exception to react-hooks/set-state-in-effect: localStorage is
  // an external system unavailable during SSR, so it cannot be read during
  // render (would either throw or desync from the server-rendered HTML) --
  // reading it post-mount and rendering null until `hydrated` is exactly
  // the pattern React's own hydration-mismatch guidance recommends, not a
  // same-render derivation of state from props/state that the rule targets.
  useEffect(() => {
    const stored = loadPlannerState();
    if (stored) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIntake(stored.intake);
      setResult(stored.result);
      if (stored.result) setStarted(true);
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    // Skip persisting a still-empty draft -- otherwise startOver()'s
    // clearPlannerState() gets immediately undone by this effect re-saving
    // the freshly-reset (but empty) state right after.
    const isEmpty = result === null && JSON.stringify(intake) === JSON.stringify(EMPTY_PLANNER_INTAKE);
    if (isEmpty) return;
    savePlannerState(intake, result);
  }, [hydrated, intake, result]);

  function update<K extends keyof PlannerIntake>(key: K, value: PlannerIntake[K]) {
    setIntake((current) => ({ ...current, [key]: value }));
  }

  function begin() {
    if (!started) trackPlannerEvent("planner_started");
    setStarted(true);
  }

  function goNext() {
    trackPlannerEvent("planner_section_completed", { sectionId: SECTION_LABELS[sectionIndex] });
    if (sectionIndex < LAST_SECTION_INDEX) {
      setSectionIndex((index) => index + 1);
    } else {
      const generated = generatePlannerResult(intake);
      setResult(generated);
      trackPlannerEvent("planner_result_viewed", { channelCategoryCount: intake.channelCategoryIds.length });
    }
  }

  function goBack() {
    setSectionIndex((index) => Math.max(0, index - 1));
  }

  function startOver() {
    clearPlannerState();
    setIntake(EMPTY_PLANNER_INTAKE);
    setResult(null);
    setSectionIndex(0);
    setStarted(false);
  }

  if (!hydrated) return null;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-6 py-10">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold text-prem3-navy">
          Planning an MMM? Find out what data you&apos;ll need before you start collecting it.
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          A free, deterministic planning brief. No account required, no data leaves your browser.
        </p>
      </div>

      {!started && (
        <button
          type="button"
          onClick={begin}
          className="w-fit rounded-md bg-prem3-indigo px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90"
        >
          Start planning
        </button>
      )}

      {started && !result && (
        <IntakeWizard
          intake={intake}
          sectionIndex={sectionIndex}
          onUpdate={update}
          onNext={goNext}
          onBack={goBack}
        />
      )}

      {result && (
        <>
          <PlannerResultView result={result} />
          <PlannerConversionCta />
          <button
            type="button"
            onClick={startOver}
            className="w-fit text-sm text-muted-foreground underline-offset-4 hover:underline"
          >
            Start over
          </button>
        </>
      )}
    </div>
  );
}

function IntakeWizard({
  intake,
  sectionIndex,
  onUpdate,
  onNext,
  onBack,
}: {
  intake: PlannerIntake;
  sectionIndex: number;
  onUpdate: <K extends keyof PlannerIntake>(key: K, value: PlannerIntake[K]) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onNext();
      }}
      className="flex flex-col gap-6 rounded-lg border border-prem3-cool-gray bg-white p-6"
    >
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <span>
          Step {sectionIndex + 1} of {SECTION_LABELS.length}
        </span>
        <span aria-hidden="true">·</span>
        <span>{SECTION_LABELS[sectionIndex]}</span>
      </div>

      {sectionIndex === 0 && <AboutBusinessSection intake={intake} onUpdate={onUpdate} />}
      {sectionIndex === 1 && <ChannelsSection intake={intake} onUpdate={onUpdate} />}
      {sectionIndex === 2 && <DataReadinessSection intake={intake} onUpdate={onUpdate} />}
      {sectionIndex === 3 && <GoalSection intake={intake} onUpdate={onUpdate} />}

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          disabled={sectionIndex === 0}
          className="rounded-md border border-prem3-cool-gray px-4 py-2 text-sm font-medium text-prem3-navy disabled:cursor-not-allowed disabled:opacity-40"
        >
          Back
        </button>
        <button
          type="submit"
          className="rounded-md bg-prem3-indigo px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-prem3-indigo/90"
        >
          {sectionIndex === LAST_SECTION_INDEX ? "Show my brief" : "Next"}
        </button>
      </div>
    </form>
  );
}

type SectionProps = {
  intake: PlannerIntake;
  onUpdate: <K extends keyof PlannerIntake>(key: K, value: PlannerIntake[K]) => void;
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="font-medium text-prem3-navy">{label}</span>
      {children}
    </label>
  );
}

const INPUT_CLASSES = "rounded-md border border-prem3-cool-gray px-3 py-2 text-sm text-prem3-navy";

function AboutBusinessSection({ intake, onUpdate }: SectionProps) {
  return (
    <div className="flex flex-col gap-4">
      <Field label="What kind of business is this?">
        <select
          value={intake.businessModel ?? ""}
          onChange={(event) => onUpdate("businessModel", (event.target.value || null) as PlannerIntake["businessModel"])}
          className={INPUT_CLASSES}
        >
          <option value="">Choose one</option>
          {BUSINESS_MODELS.map((model) => (
            <option key={model.id} value={model.id}>
              {model.label}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Industry (optional)">
        <input
          type="text"
          value={intake.industryLabel}
          onChange={(event) => onUpdate("industryLabel", event.target.value)}
          className={INPUT_CLASSES}
          placeholder="e.g. Outdoor apparel"
        />
      </Field>
      <Field label="Primary outcome you want to model">
        <input
          type="text"
          value={intake.primaryOutcome}
          onChange={(event) => onUpdate("primaryOutcome", event.target.value)}
          className={INPUT_CLASSES}
          placeholder="e.g. Revenue, signups, bookings"
        />
      </Field>
      <Field label="Markets / geographies (comma-separated)">
        <input
          type="text"
          value={intake.markets.join(", ")}
          onChange={(event) =>
            onUpdate(
              "markets",
              event.target.value
                .split(",")
                .map((market) => market.trim())
                .filter(Boolean),
            )
          }
          className={INPUT_CLASSES}
          placeholder="e.g. US, Canada"
        />
      </Field>
      <Field label="Months of marketing history available">
        <input
          type="number"
          min={0}
          value={intake.historyLengthMonths ?? ""}
          onChange={(event) => onUpdate("historyLengthMonths", event.target.value === "" ? null : Number(event.target.value))}
          className={INPUT_CLASSES}
        />
      </Field>
    </div>
  );
}

function ChannelsSection({ intake, onUpdate }: SectionProps) {
  return (
    <div className="flex flex-col gap-4">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm font-medium text-prem3-navy">Which channel categories do you use?</legend>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {CHANNEL_CATEGORIES.map((category) => (
            <label key={category.id} className="flex items-center gap-2 text-sm text-prem3-navy">
              <input
                type="checkbox"
                checked={intake.channelCategoryIds.includes(category.id)}
                onChange={() => onUpdate("channelCategoryIds", toggleInArray(intake.channelCategoryIds, category.id))}
              />
              {category.label}
            </label>
          ))}
        </div>
      </fieldset>

      {intake.channelCategoryIds.length > 0 && (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-sm font-medium text-prem3-navy">Specific platforms (optional)</legend>
          <div className="flex flex-col gap-3">
            {intake.channelCategoryIds.map((categoryId) => {
              const providers = providersInCategory(categoryId);
              if (providers.length === 0) return null;
              return (
                <div key={categoryId} className="flex flex-col gap-1.5">
                  <p className="text-xs font-medium text-muted-foreground">
                    {CHANNEL_CATEGORIES.find((c) => c.id === categoryId)?.label}
                  </p>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {providers.map((provider) => (
                      <label key={provider.providerId} className="flex items-center gap-2 text-sm text-prem3-navy">
                        <input
                          type="checkbox"
                          checked={intake.providerIds.includes(provider.providerId)}
                          onChange={() => onUpdate("providerIds", toggleInArray(intake.providerIds, provider.providerId))}
                        />
                        {provider.displayName}
                      </label>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </fieldset>
      )}
    </div>
  );
}

function BooleanField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean | null;
  onChange: (value: boolean | null) => void;
}) {
  return (
    <fieldset className="flex items-center justify-between gap-4">
      <legend className="text-sm text-prem3-navy">{label}</legend>
      <div className="flex gap-2">
        {[
          { label: "Yes", value: true },
          { label: "No", value: false },
        ].map((option) => (
          <button
            key={String(option.value)}
            type="button"
            onClick={() => onChange(option.value)}
            className={`rounded-md border px-3 py-1 text-xs font-medium ${
              value === option.value
                ? "border-prem3-indigo bg-prem3-indigo text-white"
                : "border-prem3-cool-gray text-prem3-navy"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

function DataReadinessSection({ intake, onUpdate }: SectionProps) {
  return (
    <div className="flex flex-col gap-4">
      <BooleanField
        label="Do you have an online outcome data source (e.g. web/app analytics)?"
        value={intake.hasOnlineOutcomeSource}
        onChange={(value) => onUpdate("hasOnlineOutcomeSource", value)}
      />
      <BooleanField
        label="Do you have an offline outcome data source (e.g. POS, bookings)?"
        value={intake.hasOfflineOutcomeSource}
        onChange={(value) => onUpdate("hasOfflineOutcomeSource", value)}
      />
      <Field label="Where does your marketing data land today?">
        <select
          value={intake.warehouseLocation ?? ""}
          onChange={(event) =>
            onUpdate("warehouseLocation", (event.target.value || null) as PlannerIntake["warehouseLocation"])
          }
          className={INPUT_CLASSES}
        >
          <option value="">Choose one</option>
          {WAREHOUSE_LOCATIONS.map((location) => (
            <option key={location.id} value={location.id}>
              {location.label}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Export status for your platforms">
        <select
          value={intake.exportStatus ?? ""}
          onChange={(event) => onUpdate("exportStatus", (event.target.value || null) as PlannerIntake["exportStatus"])}
          className={INPUT_CLASSES}
        >
          <option value="">Choose one</option>
          {EXPORT_STATUSES.map((status) => (
            <option key={status.id} value={status.id}>
              {status.label}
            </option>
          ))}
        </select>
      </Field>
      <BooleanField
        label="Do you have promotion/pricing/seasonality data?"
        value={intake.hasPromoPricingSeasonality}
        onChange={(value) => onUpdate("hasPromoPricingSeasonality", value)}
      />
      <BooleanField
        label="Do you have first-party/CRM data available?"
        value={intake.hasFirstPartyCrm}
        onChange={(value) => onUpdate("hasFirstPartyCrm", value)}
      />
    </div>
  );
}

function GoalSection({ intake, onUpdate }: SectionProps) {
  return (
    <div className="flex flex-col gap-4">
      <Field label="What do you want to use the MMM for?">
        <textarea
          value={intake.desiredUseCase}
          onChange={(event) => onUpdate("desiredUseCase", event.target.value)}
          className={`${INPUT_CLASSES} min-h-24`}
          placeholder="e.g. Rebalance channel budget for next quarter"
        />
      </Field>
    </div>
  );
}

function PlannerResultView({ result }: { result: PlannerResult }) {
  return (
    <div className="flex flex-col gap-6">
      <p className="rounded-md bg-prem3-light-gray px-3 py-2 text-xs font-medium text-prem3-navy">
        {result.disclaimer}
      </p>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-prem3-navy">
          {result.blueprint.title}
        </h2>
        <p className="mt-2 text-sm text-prem3-navy/80">{result.blueprint.summary}</p>
        <ul className="mt-3 flex flex-wrap gap-2">
          {result.blueprint.highlights.map((highlight) => (
            <li key={highlight} className="rounded-full bg-prem3-light-gray px-3 py-1 text-xs text-prem3-navy">
              {highlight}
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-prem3-navy">
          Data Acquisition Map
        </h2>
        <div className="mt-3 flex flex-col gap-4">
          {result.dataAcquisitionMap.length === 0 && (
            <p className="text-sm text-muted-foreground">No channels selected yet.</p>
          )}
          {result.dataAcquisitionMap.map((entry) => (
            <div key={entry.channelCategoryId} className="rounded-md border border-prem3-cool-gray/60 p-3">
              <p className="text-sm font-medium text-prem3-navy">{entry.channelLabel}</p>
              <ul className="mt-1 list-inside list-disc text-sm text-prem3-navy/80">
                {entry.requiredDataPoints.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-muted-foreground">
                Likely sources: {entry.likelyProviders.map((p) => p.displayName).join(", ") || "none identified"}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-prem3-navy">
          Likely Source Exports
        </h2>
        <ul className="mt-3 flex flex-col gap-1.5">
          {result.likelySourceExports.map((source) => (
            <li key={source.providerId} className="text-sm text-prem3-navy/80">
              {source.displayName} — {source.exportFormats.join(", ")}
            </li>
          ))}
          {result.likelySourceExports.length === 0 && (
            <li className="text-sm text-muted-foreground">None identified yet.</li>
          )}
        </ul>
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-prem3-navy">
          Meridian Preparation Checklist
        </h2>
        <ul className="mt-3 list-inside list-disc text-sm text-prem3-navy/80">
          {result.meridianPrepChecklist.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-prem3-navy">
          Known Gaps / Unknowns
        </h2>
        <ul className="mt-3 list-inside list-disc text-sm text-prem3-navy/80">
          {result.knownGaps.length === 0 && <li className="list-none text-muted-foreground">No gaps flagged.</li>}
          {result.knownGaps.map((gap) => (
            <li key={gap}>{gap}</li>
          ))}
        </ul>
      </section>

      <section className="rounded-lg border border-prem3-cool-gray bg-white p-5">
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold text-prem3-navy">
          Your Next Actions
        </h2>
        <ol className="mt-3 list-inside list-decimal text-sm text-prem3-navy/80">
          {result.nextActions.map((action) => (
            <li key={action}>{action}</li>
          ))}
        </ol>
      </section>
    </div>
  );
}
