"""Human-readable PreM3 Learning Receipt. Structured evidence remains authoritative."""

from __future__ import annotations

from app.mel.models import ExperienceApplication, LearningReceiptEnum, PromotionReceipt


def render_learning_receipt_markdown(receipt: PromotionReceipt) -> str:
    return "\n".join(
        [
            "## PreM3 learned one new routing pattern",
            "",
            "A completed pre-modeling episode produced a candidate lesson that passed",
            "evidence, scope, safety and regression checks.",
            "",
            "### What changed",
            f"- DOMAIN_VIEW: {receipt.old_domain_view_version} → {receipt.new_domain_view_version}",
            f"- Lesson authority: {receipt.authority.value}",
            f"- Scope: {receipt.scope.level.value}",
            f"- Source episodes: {len(receipt.source_episode_ids)}",
            f"- Promoted claim: `{receipt.promoted_claim_id}`",
            "",
            "### What this changes",
            receipt.behavior_effect,
            "",
            "### What it does not change",
            "- Meridian rules",
            "- MODEL_READY",
            "- final model specification",
            "",
            "### Proof",
            f"- Evaluation: `{receipt.evaluation_id}`",
            f"- Fingerprint: `{receipt.new_domain_view_fingerprint}`",
        ]
    )


def render_applied_receipt_markdown(application: ExperienceApplication) -> str:
    result = (
        application.receipt_type.value
        if application.receipt_type is not None
        else LearningReceiptEnum.NOT_APPLICABLE.value
    )
    return "\n".join(
        [
            "## Learned experience applied successfully"
            if application.receipt_type is LearningReceiptEnum.EXPERIENCE_APPLIED
            else f"## Learning application result: {result}",
            "",
            "A lesson promoted from an earlier assignment was evaluated against this holdout.",
            "",
            "### Before learning",
            str(application.behavior_before),
            "",
            "### After learning",
            str(application.behavior_after),
            "",
            "### Validation",
            application.validation_result,
            "",
            f"**Result:** {result}",
        ]
    )
