import { ShieldCheck } from "lucide-react";
import type { AuthorityPresentation } from "@/types/response";

export function AuthorityBadge({ authority }: { authority: AuthorityPresentation }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5 rounded-md border border-prem3-cool-gray bg-white px-2.5 py-1 text-xs text-prem3-navy">
      <ShieldCheck className="size-3.5 text-prem3-indigo" aria-hidden="true" />
      {authority.knowledge_label}
      {authority.rule_id && <span className="text-prem3-navy/50">· {authority.rule_id}</span>}
      {authority.blocks_model_ready && (
        <span className="rounded bg-red-50 px-1.5 py-0.5 font-medium text-red-800">
          Blocks MODEL_READY
        </span>
      )}
    </span>
  );
}
