import { Eye } from "lucide-react";
import type { ExperienceReflection, ReflectionItem } from "@/types/mel";

const SURFACE_GROUPS: { key: keyof ExperienceReflection; label: string }[] = [
  { key: "observed", label: "Observed" },
  { key: "determined", label: "Determined" },
  { key: "believed", label: "Believed" },
  { key: "confirmed", label: "Confirmed" },
  { key: "missed", label: "Missed" },
  { key: "surprises", label: "Surprises" },
  { key: "possible_improvements", label: "Possible improvements" },
];

export function ReflectionCard({ reflection }: { reflection: ExperienceReflection }) {
  const groups = SURFACE_GROUPS.filter((group) => (reflection[group.key] as ReflectionItem[]).length > 0);

  return (
    <div className="rounded-lg border border-prem3-cool-gray bg-white p-4">
      <div className="flex items-center gap-2">
        <Eye className="size-4 text-prem3-indigo" aria-hidden="true" />
        <p className="text-sm font-semibold text-prem3-navy">Reflection</p>
      </div>

      <p className="mt-2 rounded-md border border-prem3-cool-gray bg-prem3-light-gray px-3 py-2 text-xs text-prem3-navy/70">
        Reflection is evidence, not a decision. It has no operational authority — it never sets
        MODEL_READY, promotes a lesson, or changes DOMAIN_VIEW.
      </p>

      <p className="mt-3 text-sm text-prem3-navy">{reflection.reflection_summary}</p>

      <div className="mt-3 flex flex-col gap-3">
        {groups.map((group) => (
          <div key={group.key}>
            <p className="text-xs font-semibold uppercase tracking-wide text-prem3-navy/70">{group.label}</p>
            <ul className="mt-1 list-inside list-disc text-sm text-prem3-navy">
              {(reflection[group.key] as ReflectionItem[]).map((item) => (
                <li key={item.item_id}>{item.statement}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
