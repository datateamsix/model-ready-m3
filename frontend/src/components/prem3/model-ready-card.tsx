import { CircleCheck, CircleX } from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusHeader } from "./status-header";
import type { ModelReadyGateEvidence, PresentationStatus } from "@/types/response";

interface GateRow {
  key: keyof ModelReadyGateEvidence;
  label: string;
  render: (gate: ModelReadyGateEvidence) => { passed: boolean; text: string };
}

const GATE_ROWS: GateRow[] = [
  {
    key: "bigquery_verified",
    label: "BigQuery model artifact",
    render: (gate) => ({ passed: gate.bigquery_verified, text: gate.bigquery_verified ? "Published and verified" : "Not verified" }),
  },
  {
    key: "content_fingerprint_matched",
    label: "Publish/readback parity",
    render: (gate) => ({ passed: gate.content_fingerprint_matched, text: gate.content_fingerprint_matched ? "Fingerprint matched" : "Fingerprint mismatch" }),
  },
  {
    key: "official_meridian_eda_complete",
    label: "Official Meridian EDA",
    render: (gate) => ({ passed: gate.official_meridian_eda_complete, text: gate.official_meridian_eda_complete ? "Complete" : "Not complete" }),
  },
  {
    key: "official_error_count",
    label: "Official ERROR count",
    render: (gate) => ({ passed: gate.official_error_count === 0, text: `Official ERROR count: ${gate.official_error_count}` }),
  },
  {
    key: "handoff_persisted",
    label: "Modeler handoff",
    render: (gate) => ({ passed: gate.handoff_persisted, text: gate.handoff_persisted ? "Persisted" : "Not persisted" }),
  },
];

export interface ModelReadyCardProps {
  title: string;
  summary: string;
  status: PresentationStatus;
  gate: ModelReadyGateEvidence;
}

export function ModelReadyCard({ title, summary, status, gate }: ModelReadyCardProps) {
  return (
    <div className="flex flex-col gap-4">
      <StatusHeader title={title} summary={summary} status={status} />
      <div className="rounded-lg border border-prem3-cool-gray bg-white">
        {GATE_ROWS.map((row) => {
          const { passed, text } = row.render(gate);
          return (
            <div
              key={row.key}
              data-testid={`gate-${row.key}`}
              data-passed={passed}
              className="flex items-center justify-between gap-3 border-b border-prem3-cool-gray px-4 py-3 last:border-b-0"
            >
              <span className="text-sm text-prem3-navy">{row.label}</span>
              <span
                className={cn(
                  "flex items-center gap-1.5 text-sm font-medium",
                  passed ? "text-emerald-700" : "text-red-700",
                )}
              >
                {passed ? <CircleCheck className="size-4" aria-hidden="true" /> : <CircleX className="size-4" aria-hidden="true" />}
                {text}
              </span>
            </div>
          );
        })}
      </div>
      {gate.review_recommended && (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          Review recommended — official Meridian returned ATTENTION findings alongside zero ERROR findings.
        </p>
      )}
    </div>
  );
}
