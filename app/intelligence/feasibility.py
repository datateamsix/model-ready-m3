"""Dimensional modeling feasibility. Not a magic score. Distinct from MODEL_READY."""

from __future__ import annotations

from typing import Any

from app.intelligence.contracts import (
    AuthorityRef,
    ComputationalDimension,
    DecisionClass,
    DimensionalStatus,
    FeasibilityDimension,
    KnowledgeClass,
    Prem3DiagnosticDisposition,
    SemanticReadinessStatus,
)
from app.intelligence.snapshot import DiagnosticSnapshot


def build_computational_readiness(diagnostics: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        ComputationalDimension.DATA_CONTRACT: _contract_dimension(diagnostics),
        ComputationalDimension.HISTORY: _from_finding(diagnostics.get("history")),
        ComputationalDimension.GEO_COVERAGE: _from_finding(diagnostics.get("geo_coverage")),
        ComputationalDimension.PARAMETER_PRESSURE: _from_finding(
            diagnostics.get("parameter_budget")
        ),
        ComputationalDimension.CHANNEL_SPEND_DISTRIBUTION: _from_finding(
            diagnostics.get("spend_distribution")
        ),
        ComputationalDimension.CHANNEL_VARIATION: _from_finding(diagnostics.get("media_variation")),
        ComputationalDimension.SPEND_RANGE: _from_finding(diagnostics.get("spend_range")),
        ComputationalDimension.COLLINEARITY: _from_finding(diagnostics.get("collinearity")),
        ComputationalDimension.PRE_PERIOD_MEDIA: _from_finding(diagnostics.get("pre_period_media")),
        ComputationalDimension.MEDIA_SPEND_CONSISTENCY: _from_finding(
            diagnostics.get("media_spend_consistency")
        ),
        ComputationalDimension.POPULATION_RELATIONSHIPS: _from_finding(
            diagnostics.get("population_relationships")
        ),
        ComputationalDimension.REACH_FREQUENCY: _from_finding(diagnostics.get("reach_frequency")),
        ComputationalDimension.MISSINGNESS_EVIDENCE: _from_finding(
            diagnostics.get("missingness_evidence")
        ),
    }
    dimensions = []
    for key, item in mapping.items():
        item.dimension = key.value
        dimensions.append(item.model_dump(mode="json"))
    return {
        "score": None,
        "magic_score_forbidden": True,
        "dimensions": dimensions,
    }


def build_modeling_feasibility(
    snapshot: DiagnosticSnapshot,
    *,
    computational: dict[str, Any],
    semantic: dict[str, Any],
    official_eda: dict[str, Any] | None,
) -> dict[str, Any]:
    by_name = {item["dimension"]: item for item in computational.get("dimensions") or []}
    dimensions: list[dict[str, Any]] = []
    for name in FeasibilityDimension:
        if name is FeasibilityDimension.CAUSAL_CONTEXT:
            dimensions.append(_causal_dimension(semantic))
        elif name is FeasibilityDimension.OFFICIAL_MERIDIAN_EDA:
            dimensions.append(_official_eda_dimension(official_eda or snapshot.eda_receipt))
        else:
            source = by_name.get(name.value) or {
                "dimension": name.value,
                "disposition": Prem3DiagnosticDisposition.NOT_APPLICABLE.value,
                "observed_evidence": {},
                "why_it_matters": "Dimension not calculated.",
                "recommended_review": "None.",
                "review_recommended": False,
                "blocks_model_ready": False,
            }
            dimensions.append(source)
    return {
        "score": None,
        "magic_score_forbidden": True,
        "model_ready_is_distinct": True,
        "heuristic_cannot_override_model_ready": True,
        "dimensions": dimensions,
        "semantic_status": semantic.get("semantic_status"),
        "official_meridian_eda_status": (official_eda or snapshot.eda_receipt or {}).get("status")
        if official_eda or snapshot.eda_receipt
        else "PENDING",
    }


def _contract_dimension(diagnostics: dict[str, Any]) -> DimensionalStatus:
    endpoint = diagnostics.get("source_endpoint") or {}
    return DimensionalStatus(
        dimension=ComputationalDimension.DATA_CONTRACT.value,
        disposition=Prem3DiagnosticDisposition.PASS,
        observed_evidence={
            "resolved_source": endpoint.get("resolved_source"),
            "input_fingerprint": endpoint.get("input_fingerprint"),
            "row_count": endpoint.get("row_count"),
        },
        authority=AuthorityRef(
            knowledge_class=KnowledgeClass.MERIDIAN_NORMATIVE,
            decision_class=DecisionClass.AUTO_BLOCK,
            rule_id="MR-020",
            blocks_model_ready=True,
        ),
        why_it_matters=(
            "Diagnostics only run after the verified BigQuery model-consumption input is proven."
        ),
        recommended_review="None. Contract already verified.",
        related_finding_ids=[],
        review_recommended=False,
        blocks_model_ready=False,
    )


def _from_finding(payload: dict[str, Any] | None) -> DimensionalStatus:
    finding = (payload or {}).get("finding") or {}
    return DimensionalStatus(
        dimension=str(finding.get("dimension") or "UNKNOWN"),
        disposition=Prem3DiagnosticDisposition(
            finding.get("disposition") or Prem3DiagnosticDisposition.NOT_APPLICABLE.value
        ),
        observed_evidence=finding.get("observed_evidence") or {},
        authority=AuthorityRef.model_validate(finding["source_authority"])
        if finding.get("source_authority")
        else None,
        why_it_matters=str(finding.get("why_it_matters") or ""),
        recommended_review=str(finding.get("recommended_action") or ""),
        related_finding_ids=[finding["finding_id"]] if finding.get("finding_id") else [],
        review_recommended=bool(finding.get("review_recommended")),
        blocks_model_ready=False,
    )


def _causal_dimension(semantic: dict[str, Any]) -> dict[str, Any]:
    status = semantic.get("semantic_status") or SemanticReadinessStatus.CLEAR.value
    disposition = Prem3DiagnosticDisposition.PASS
    if status == SemanticReadinessStatus.USER_CONTEXT_REQUIRED.value:
        disposition = Prem3DiagnosticDisposition.USER_CONTEXT_REQUIRED
    elif status != SemanticReadinessStatus.CLEAR.value:
        disposition = Prem3DiagnosticDisposition.REVIEW_RECOMMENDED
    return DimensionalStatus(
        dimension=FeasibilityDimension.CAUSAL_CONTEXT.value,
        disposition=disposition,
        observed_evidence={
            "question_count": semantic.get("question_count"),
            "semantic_status": status,
            "causal_roles_assigned": False,
        },
        authority=AuthorityRef(
            knowledge_class=KnowledgeClass.MMM_JUDGMENT,
            decision_class=DecisionClass.MODELER_REVIEW_REQUIRED,
            rule_id="PREM3-SEM-001",
            blocks_model_ready=False,
        ),
        why_it_matters="Some causal/business questions cannot be calculated from the table.",
        recommended_review="Answer triggered semantic questions. Do not infer causal roles.",
        related_question_ids=[
            item.get("question_id")
            for item in semantic.get("questions") or []
            if item.get("question_id")
        ],
        review_recommended=status != SemanticReadinessStatus.CLEAR.value,
        blocks_model_ready=False,
    ).model_dump(mode="json")


def _official_eda_dimension(eda: dict[str, Any] | None) -> dict[str, Any]:
    if not eda:
        return DimensionalStatus(
            dimension=FeasibilityDimension.OFFICIAL_MERIDIAN_EDA.value,
            disposition=Prem3DiagnosticDisposition.NOT_APPLICABLE,
            observed_evidence={"status": "PENDING"},
            authority=AuthorityRef(
                knowledge_class=KnowledgeClass.MERIDIAN_NORMATIVE,
                decision_class=DecisionClass.AUTO_BLOCK,
                rule_id="PREM3-EDA-001",
                blocks_model_ready=True,
            ),
            why_it_matters=(
                "Official Meridian EDA has not run yet. PreM3 diagnostics do not replace it."
            ),
            recommended_review="Run official Meridian EDA against the same verified input.",
            review_recommended=False,
            blocks_model_ready=False,
        ).model_dump(mode="json")
    errors = int((eda.get("severity_counts") or {}).get("ERROR") or eda.get("error_count") or 0)
    disposition = (
        Prem3DiagnosticDisposition.CONTRACT_FAILURE if errors else Prem3DiagnosticDisposition.PASS
    )
    return DimensionalStatus(
        dimension=FeasibilityDimension.OFFICIAL_MERIDIAN_EDA.value,
        disposition=disposition,
        observed_evidence={
            "status": eda.get("status") or "COMPLETE",
            "error_count": errors,
            "attention_count": (eda.get("severity_counts") or {}).get("ATTENTION")
            or eda.get("attention_count"),
        },
        authority=AuthorityRef(
            knowledge_class=KnowledgeClass.MERIDIAN_NORMATIVE,
            decision_class=DecisionClass.AUTO_BLOCK,
            rule_id="PREM3-EDA-001",
            blocks_model_ready=True,
        ),
        why_it_matters="Official Meridian ERROR remains authoritative for the official EDA gate.",
        recommended_review=(
            "If ERROR exists, follow the User Resolution Pack. PreM3 cannot outvote Meridian."
        ),
        review_recommended=errors == 0 and bool(eda.get("attention_count")),
        blocks_model_ready=bool(errors),
    ).model_dump(mode="json")
