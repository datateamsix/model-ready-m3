import { BadgeCheck } from "lucide-react";
import type { PromotionReceipt } from "@/types/mel";

export function LearningReceiptCard({ receipt }: { receipt: PromotionReceipt }) {
  return (
    <div className="rounded-lg border border-prem3-cool-gray bg-white p-4">
      <div className="flex items-center gap-2">
        <BadgeCheck className="size-4 text-prem3-indigo" aria-hidden="true" />
        <p className="text-sm font-semibold text-prem3-navy">{receipt.receipt_type}</p>
      </div>
      <p className="mt-2 text-sm text-prem3-navy">{receipt.behavior_effect}</p>
      <dl className="mt-3 grid grid-cols-2 gap-3 text-xs text-prem3-navy/70">
        <div>
          <dt className="uppercase tracking-wide">DOMAIN_VIEW</dt>
          <dd className="mt-0.5 text-prem3-navy">
            {receipt.old_domain_view_version} → {receipt.new_domain_view_version}
          </dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">Promoted claim</dt>
          <dd className="mt-0.5 text-prem3-navy">{receipt.promoted_claim_id}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">Regression</dt>
          <dd className="mt-0.5 text-prem3-navy">{receipt.regression_result.passed ? "Passed" : "Failed"}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">Promoted at</dt>
          <dd className="mt-0.5 text-prem3-navy">{receipt.promotion_timestamp.slice(0, 10)}</dd>
        </div>
      </dl>
    </div>
  );
}
