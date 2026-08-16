"""Acceptance tests for PreM3 intelligence authority and policy contracts."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from app.core.contracts import RemediationClass
from app.rules.engine import load_rule_catalog
from tests.unit.test_prem3_brand import test_root_agent_tool_order_unchanged

ROOT = Path(__file__).resolve().parents[2]
BOOT = (ROOT / "docs/context/prem3_mmm_boot_context.md").read_text(encoding="utf-8")
PREP = (ROOT / "docs/context/meridian/meridian_data_prep_context.md").read_text(encoding="utf-8")
ADVISOR = (ROOT / "docs/context/meridian/meridian_advisor_playbook.md").read_text(encoding="utf-8")
PRODUCT = (ROOT / "docs/context/prem3_product_context.md").read_text(encoding="utf-8")
FEASIBILITY = (
    ROOT / "docs/context/intelligence/MODELING_FEASIBILITY_SPEC.md"
).read_text(encoding="utf-8")
REMEDIATION = (
    ROOT / "docs/context/intelligence/GUIDED_REMEDIATION_CONTRACT.md"
).read_text(encoding="utf-8")
SEMANTIC = (
    ROOT / "docs/context/intelligence/SEMANTIC_READINESS_INTERVIEW_SPEC.md"
).read_text(encoding="utf-8")
SCENARIOS = (ROOT / "docs/context/intelligence/SCOPE_SCENARIO_SPEC.md").read_text(
    encoding="utf-8"
)
DISCREPANCY = (
    ROOT / "docs/context/intelligence/SOURCE_VERIFICATION_DISCREPANCY_REPORT.md"
).read_text(encoding="utf-8")


def _registry() -> dict:
    return yaml.safe_load(
        (ROOT / "app/rules/intelligence_registry.yaml").read_text(encoding="utf-8")
    )


def test_intelligence_version_is_recorded() -> None:
    payload = json.loads(
        (ROOT / "docs/context/intelligence/intelligence_version.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["intelligence_version"] == "2.0.0"
    assert payload["runtime_behavior_change"] is False
    assert payload["status"] == "context_only"


def test_four_behaviors_are_not_synonyms_for_analyze() -> None:
    assess = "establish the current state" in PRODUCT.lower() or "What data do you have?" in PRODUCT
    advise = "distinguish requirements from heuristics" in PRODUCT
    insight = "actual computation over generic prose" in PRODUCT
    guide = "when to rerun or hand off" in PRODUCT
    assert assess and advise and insight and guide
    assert "ASSESS" in BOOT and "ADVISE" in BOOT and "INSIGHT" in BOOT and "GUIDE" in BOOT


def test_parameter_ratio_is_heuristic_not_meridian_normative() -> None:
    assert "MMM_EVIDENCE_HEURISTIC" in BOOT
    assert "cannot independently deny `MODEL_READY`" in BOOT
    assert "must reduce scope" not in PREP.lower()
    assert "review_recommended=true" in PREP
    pb001 = next(
        rule for rule in _registry()["rules"] if rule["rule_id"] == "PREM3-PB-001"
    )
    assert pb001["threshold_authority"] == "PREM3_ADVISORY"
    assert pb001["blocks_model_ready"] is False
    assert pb001["status"] == "specified_not_implemented"


def test_missing_media_is_not_automatically_zero() -> None:
    assert "Unknown absence does not equal zero" in BOOT
    assert "CONFIRMED_INACTIVE" in PREP
    assert "Fill `0` **only when source evidence supports channel inactivity" in PREP
    assert "does **not** immediately fill zero" in REMEDIATION


def test_kpi_control_imputation_is_not_auto_safe() -> None:
    assert "KPI and control imputation remain `APPROVAL_REQUIRED`" in BOOT
    assert RemediationClass.AUTO_SAFE.value != "KPI"
    catalog = load_rule_catalog(ROOT / "app/rules/meridian.yaml")
    missing = next(rule for rule in catalog["rules"] if rule["id"] == "MR-002")
    assert missing["remediation_class"] == "APPROVAL_REQUIRED"
    assert "Imputation is never AUTO_SAFE" in missing["notes"]
    miss002 = next(
        rule for rule in _registry()["rules"] if rule["rule_id"] == "PREM3-MISS-002"
    )
    assert miss002["decision_class"] == "APPROVAL_REQUIRED"
    assert miss002["agent_can_fix"] is False


def test_causal_roles_are_not_assigned_from_correlation() -> None:
    assert "Causal role is not determined by correlation" in BOOT
    combined = f"{SEMANTIC}\n{PREP}".lower()
    for trigger in (
        "were promotions scheduled independently",
        "did upper-funnel campaigns materially drive branded search",
        "remarketing",
        "high-spend weeks",
        "price changes determined independently of media",
    ):
        assert trigger in combined, f"missing causal trigger: {trigger}"
    assert "must not populate a causal-role assignment" in SEMANTIC
    assert "Never assign confounder / predictor / mediator from correlation alone." in SEMANTIC


def test_confounder_is_not_dropped_to_improve_ratio() -> None:
    assert "Never drop a confirmed confounder merely to improve a parameter ratio" in BOOT
    assert "Never drop a genuine confounder merely to improve a ratio" in PREP
    pb002 = next(
        rule for rule in _registry()["rules"] if rule["rule_id"] == "PREM3-PB-002"
    )
    assert "Never drop a confirmed confounder" in pb002["best_practice_guidance"]


def test_model_ready_can_coexist_with_parameter_pressure() -> None:
    assert "A run may still reach `MODEL_READY` while carrying `HIGH_PARAMETER_PRESSURE`" in PREP
    assert "cannot independently block `MODEL_READY`" in FEASIBILITY
    assert "broader than `MODEL_READY`" in FEASIBILITY


def test_prem3_diagnostics_are_not_official_eda() -> None:
    assert "PREM3_PRE_EDA_DIAGNOSTIC" in PREP
    assert "OFFICIAL_MERIDIAN_EDA_FINDING" in PREP
    assert "Never serialize a PreM3 diagnostic as an official Meridian finding" in BOOT
    eda001 = next(
        rule for rule in _registry()["rules"] if rule["rule_id"] == "PREM3-EDA-001"
    )
    assert "Never present a PreM3 pre-EDA result as an official Meridian EDA finding" in eda001[
        "best_practice_guidance"
    ]


def test_scope_scenarios_are_read_only() -> None:
    assert "They do not mutate production input." in SCENARIOS
    assert "must not mutate production input" in SCENARIOS.lower() or "must not mutate" in _registry()[
        "rules"
    ][-1]["best_practice_guidance"]


def test_guided_remediation_identifies_actors_and_retry() -> None:
    for section in (
        "WHAT I FOUND",
        "WHY IT MATTERS",
        "BEST PRACTICE",
        "INSIGHT FROM YOUR DATA",
        "WHAT PREM3 CAN DO",
        "WHAT YOU SHOULD DO",
        "MODELER REVIEW",
        "NEXT STEP",
    ):
        assert section in REMEDIATION
        assert section in ADVISOR
    for actor in (
        "PREM3",
        "MARKETER",
        "ANALYST",
        "DATA_ENGINEER",
        "MODELER",
        "SYSTEM_ADMIN",
    ):
        assert actor in REMEDIATION
    assert "when to rerun PreM3" in REMEDIATION.lower() or "Rerun PreM3" in REMEDIATION


def test_advisor_has_three_response_modes() -> None:
    assert "**CONCEPTUAL**" in ADVISOR
    assert "**COMPUTATIONAL**" in ADVISOR
    assert "**SEMANTIC / CAUSAL**" in ADVISOR


def test_registry_design_does_not_claim_tools_implemented() -> None:
    registry = _registry()
    assert registry["status"] == "specified_not_implemented"
    for rule in registry["rules"]:
        assert rule["status"] == "specified_not_implemented"
        for field in (
            "rule_id",
            "knowledge_class",
            "decision_class",
            "source_tier",
            "source_url",
            "last_verified",
            "blocks_model_ready",
            "agent_can_fix",
            "human_owner",
        ):
            assert field in rule


def test_runtime_remediation_enum_was_not_expanded() -> None:
    assert {item.value for item in RemediationClass} == {
        "AUTO_SAFE",
        "APPROVAL_REQUIRED",
        "BLOCKED",
    }
    catalog = load_rule_catalog(ROOT / "app/rules/meridian.yaml")
    assert {rule["id"] for rule in catalog["rules"]} >= {
        "MR-001",
        "MR-002",
        "MR-019",
        "MR-020",
    }
    missing = next(rule for rule in catalog["rules"] if rule["id"] == "MR-002")
    assert missing["remediation_class"] == "APPROVAL_REQUIRED"


def test_no_runtime_tool_order_change() -> None:
    test_root_agent_tool_order_unchanged()


def test_discrepancy_report_resolves_required_topics() -> None:
    for topic in (
        "Parameter ratio",
        "Missing media",
        "KPI / control imputation",
        "VIF / correlation",
        "Model configuration / knots",
        "Technical version claims",
    ):
        assert topic in DISCREPANCY
    assert "google-meridian==1.8.0" in DISCREPANCY
    assert "Python 3.11 or 3.12" in DISCREPANCY
