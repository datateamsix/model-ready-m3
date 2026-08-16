"""Typed Meridian EDA receipts. Severities and check types mirror official Meridian."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.contracts import utc_now

PINNED_GOOGLE_MERIDIAN = "1.8.0"
DEFAULT_PRIOR_N_DRAW = 500
DEFAULT_PRIOR_SEED = 0
KPI_INVARIABILITY_STD_THRESHOLD = 1e-4
PAIRWISE_CORR_THRESHOLD = 0.999
VIF_THRESHOLD = 1000.0
STD_THRESHOLD = 1e-4
EDA_MODEL_SPEC_DEFAULT = "MERIDIAN_DEFAULT"
EDA_MODEL_SPEC_GEO_TIME_INVARIANT = "EDA_ONLY_OFFICIAL_GEO_TIME_CONTROL_INVARIANT"
KNOTS_RATIONALE_SOURCE = (
    "https://developers.google.com/meridian/docs/advanced-modeling/setting-knots"
)
EDA_MODEL_SPEC_POLICY = {
    "purpose": "PRE_MODELING_EDA_ONLY",
    "default_source": EDA_MODEL_SPEC_DEFAULT,
    "enable_aks": False,
    "approved_for_final_modeling": False,
    "agent_selected": False,
    "geo_time_invariant_control_fallback": {
        "source": EDA_MODEL_SPEC_GEO_TIME_INVARIANT,
        "knots_rule": "n_time_minus_1",
        "rationale_source": KNOTS_RATIONALE_SOURCE,
    },
}
DATA_ADEQUACY_FIELDS = (
    "n_geos",
    "n_times",
    "n_knots",
    "n_controls",
    "n_treatments",
    "n_parameters",
    "n_data_points",
    "ratio",
)

OFFICIAL_EDA_CHECK_TYPES = (
    "PAIRWISE_CORRELATION",
    "STANDARD_DEVIATION",
    "MULTICOLLINEARITY",
    "KPI_INVARIABILITY",
    "COST_PER_MEDIA_UNIT",
    "VARIABLE_GEO_TIME_COLLINEARITY",
    "POPULATION_CORRELATION",
    "PRIOR_PROBABILITY",
    "DATA_ADEQUACY",
)

OFFICIAL_EDA_SEVERITIES = ("INFO", "ATTENTION", "ERROR")
OFFICIAL_FINDING_CAUSES = (
    "NONE",
    "MULTICOLLINEARITY",
    "VARIABILITY",
    "INCONSISTENT_DATA",
    "RUNTIME_ERROR",
    "OUTLIER",
)
OFFICIAL_ANALYSIS_LEVELS = ("OVERALL", "NATIONAL", "GEO")

CHECK_TYPE_TO_CATEGORY = {
    "DATA_ADEQUACY": "spend_and_media_unit",
    "COST_PER_MEDIA_UNIT": "spend_and_media_unit",
    "KPI_INVARIABILITY": "individual_variables",
    "STANDARD_DEVIATION": "individual_variables",
    "POPULATION_CORRELATION": "population_scaling",
    "PAIRWISE_CORRELATION": "variable_relationships",
    "MULTICOLLINEARITY": "variable_relationships",
    "VARIABLE_GEO_TIME_COLLINEARITY": "variable_relationships",
    "PRIOR_PROBABILITY": "prior_specifications",
}

CATEGORY_KEYS = (
    "spend_and_media_unit",
    "individual_variables",
    "population_scaling",
    "variable_relationships",
    "prior_specifications",
)

SEVERITY_RANK = {"INFO": 1, "ATTENTION": 2, "ERROR": 3}


class MeridianEDASeverity(StrEnum):
    INFO = "INFO"
    ATTENTION = "ATTENTION"
    ERROR = "ERROR"


class MeridianEDACheckType(StrEnum):
    PAIRWISE_CORRELATION = "PAIRWISE_CORRELATION"
    STANDARD_DEVIATION = "STANDARD_DEVIATION"
    MULTICOLLINEARITY = "MULTICOLLINEARITY"
    KPI_INVARIABILITY = "KPI_INVARIABILITY"
    COST_PER_MEDIA_UNIT = "COST_PER_MEDIA_UNIT"
    VARIABLE_GEO_TIME_COLLINEARITY = "VARIABLE_GEO_TIME_COLLINEARITY"
    POPULATION_CORRELATION = "POPULATION_CORRELATION"
    PRIOR_PROBABILITY = "PRIOR_PROBABILITY"
    DATA_ADEQUACY = "DATA_ADEQUACY"


class MeridianEDAFindingCause(StrEnum):
    NONE = "NONE"
    MULTICOLLINEARITY = "MULTICOLLINEARITY"
    VARIABILITY = "VARIABILITY"
    INCONSISTENT_DATA = "INCONSISTENT_DATA"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    OUTLIER = "OUTLIER"


class MeridianEDAAnalysisLevel(StrEnum):
    OVERALL = "OVERALL"
    NATIONAL = "NATIONAL"
    GEO = "GEO"


class MeridianEDAReportCategory(StrEnum):
    SPEND_AND_MEDIA_UNIT = "spend_and_media_unit"
    INDIVIDUAL_VARIABLES = "individual_variables"
    POPULATION_SCALING = "population_scaling"
    VARIABLE_RELATIONSHIPS = "variable_relationships"
    PRIOR_SPECIFICATIONS = "prior_specifications"


class MeridianInputMapping(BaseModel):
    """Field mapping for official DataFrameInputDataBuilder. Not Music Center-specific."""

    kpi_type: str
    kpi_type_derivation: str
    time_col: str
    geo_col: str | None = None
    kpi_col: str
    revenue_per_kpi_col: str
    population_col: str | None = None
    media_cols: list[str] = Field(default_factory=list)
    media_spend_cols: list[str] = Field(default_factory=list)
    media_channels: list[str] = Field(default_factory=list)
    organic_media_cols: list[str] = Field(default_factory=list)
    organic_media_channels: list[str] = Field(default_factory=list)
    control_cols: list[str] = Field(default_factory=list)
    model_scope: str

    @field_validator("kpi_type")
    @classmethod
    def _kpi_type_official(cls, value: str) -> str:
        if value not in {"revenue", "non_revenue"}:
            raise ValueError("kpi_type must be official Meridian 'revenue' or 'non_revenue'.")
        return value


class MeridianEDAPriorContext(BaseModel):
    source: str = "MERIDIAN_DEFAULT"
    used_for: str = "EDA_PRIOR_DIAGNOSTICS_ONLY"
    approved_for_final_modeling: bool = False
    n_draws_prior: int = DEFAULT_PRIOR_N_DRAW
    seed: int = DEFAULT_PRIOR_SEED


class MeridianEDAModelSpecContext(BaseModel):
    """Official ModelSpec used for EDA only. Not approved for posterior/fitting."""

    source: str = EDA_MODEL_SPEC_DEFAULT
    knots: int | str = EDA_MODEL_SPEC_DEFAULT
    n_knots: int | str = EDA_MODEL_SPEC_DEFAULT
    n_time: int | None = None
    enable_aks: bool = False
    approved_for_final_modeling: bool = False
    reason: str | None = None

    @model_validator(mode="after")
    def _eda_only_identifiable(self) -> MeridianEDAModelSpecContext:
        if self.approved_for_final_modeling:
            raise ValueError("EDA ModelSpec is not approved for final modeling.")
        if self.enable_aks:
            raise ValueError("Automatic knot selection is not part of pre-modeling EDA.")
        if self.source == EDA_MODEL_SPEC_GEO_TIME_INVARIANT:
            knots = self.knots if isinstance(self.knots, int) else self.n_knots
            if not isinstance(knots, int) or self.n_time is None or knots >= self.n_time:
                raise ValueError(
                    "Official geo-time control invariant requires knots < n_time."
                )
        return self


class MeridianEDACompatibilityEvent(BaseModel):
    """Official Meridian ModelSpec compatibility adjustment. EDA-only, not a prior."""

    event_type: str = "EDA_MODEL_SPEC_COMPATIBILITY_ADJUSTMENT"
    source: str = "OFFICIAL_MERIDIAN"
    official_error: str
    condition: dict[str, Any] = Field(default_factory=dict)
    default_model_spec: dict[str, Any] = Field(default_factory=dict)
    eda_model_spec: dict[str, Any] = Field(default_factory=dict)
    purpose: str = "PRE_MODELING_EDA_ONLY"
    approved_for_final_modeling: bool = False
    rationale_source: str = KNOTS_RATIONALE_SOURCE
    agent_selected: bool = False

    @model_validator(mode="after")
    def _eda_only(self) -> MeridianEDACompatibilityEvent:
        if self.approved_for_final_modeling or self.agent_selected:
            raise ValueError("Compatibility adjustment is EDA-only and not agent-selected.")
        if self.purpose != "PRE_MODELING_EDA_ONLY":
            raise ValueError("Compatibility adjustment purpose must be PRE_MODELING_EDA_ONLY.")
        return self


class MeridianEDADataAdequacy(BaseModel):
    """Official Meridian check_data_param_ratio scalars. M3 does not recompute them."""

    n_geos: int | float | None = None
    n_times: int | float | None = None
    n_knots: int | float | None = None
    n_controls: int | float | None = None
    n_treatments: int | float | None = None
    n_parameters: int | float | None = None
    n_data_points: int | float | None = None
    ratio: float | None = None
    source_artifact_ref: str | None = None

    def is_complete(self) -> bool:
        return all(getattr(self, field) is not None for field in DATA_ADEQUACY_FIELDS)

    def as_ints(self) -> dict[str, int | float | None]:
        return {field: getattr(self, field) for field in DATA_ADEQUACY_FIELDS}


class MeridianEDAFinding(BaseModel):
    finding_id: str
    check_type: str
    report_category: str
    severity: str
    finding_cause: str
    explanation: str
    analysis_level: str | None = None
    affected_variables: list[str] = Field(default_factory=list)
    affected_channels: list[str] = Field(default_factory=list)
    associated_artifact_ref: str | None = None

    @field_validator("severity")
    @classmethod
    def _official_severity(cls, value: str) -> str:
        if value not in OFFICIAL_EDA_SEVERITIES:
            raise ValueError(f"severity must be one of {OFFICIAL_EDA_SEVERITIES}")
        return value

    @field_validator("check_type")
    @classmethod
    def _official_check(cls, value: str) -> str:
        if value not in OFFICIAL_EDA_CHECK_TYPES:
            raise ValueError(f"check_type must be an official Meridian EDA check: {value}")
        return value


class MeridianEDACategorySummary(BaseModel):
    category: str
    applicable: bool = True
    check_types: list[str] = Field(default_factory=list)
    error_count: int = 0
    attention_count: int = 0
    info_count: int = 0
    finding_ids: list[str] = Field(default_factory=list)


class MeridianEDAReceipt(BaseModel):
    run_id: str
    target_model: str = "google_meridian"
    source: dict[str, Any] = Field(default_factory=dict)
    meridian: dict[str, Any] = Field(default_factory=dict)
    eda_config_uri: str | None = None
    html_report_uri: str | None = None
    model_input_fingerprint: str = ""
    eda_config_fingerprint: str = ""
    idempotency_key: str = ""
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    prior_context: MeridianEDAPriorContext = Field(default_factory=MeridianEDAPriorContext)
    model_spec: MeridianEDAModelSpecContext = Field(default_factory=MeridianEDAModelSpecContext)
    data_adequacy: MeridianEDADataAdequacy = Field(default_factory=MeridianEDADataAdequacy)
    compatibility_event: MeridianEDACompatibilityEvent | None = None
    purpose: str = "PRE_MODELING_EDA_ONLY"
    posterior_sampling: bool = False
    model_fitted: bool = False
    severity_summary: dict[str, Any] = Field(default_factory=dict)
    check_summary: dict[str, Any] = Field(default_factory=dict)
    categories: dict[str, Any] = Field(default_factory=dict)
    findings: list[MeridianEDAFinding] = Field(default_factory=list)
    analysis_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "EDA_COMPLETE"

    @model_validator(mode="after")
    def _no_silent_modeling(self) -> MeridianEDAReceipt:
        if self.posterior_sampling or self.model_fitted:
            raise ValueError("Pre-modeling EDA must not sample posterior or fit the model.")
        if self.prior_context.approved_for_final_modeling:
            raise ValueError("EDA priors are not approved for final modeling.")
        if self.model_spec.approved_for_final_modeling:
            raise ValueError("EDA ModelSpec is not approved for final modeling.")
        if self.prior_context.used_for != "EDA_PRIOR_DIAGNOSTICS_ONLY":
            raise ValueError("EDA prior context must be EDA_PRIOR_DIAGNOSTICS_ONLY.")
        return self


class MeridianCorrectionItem(BaseModel):
    item_id: str
    owner: str
    agent_can_fix: bool = False
    source: str
    finding_id: str | None = None
    severity: str | None = None
    official_feedback: str
    what_to_correct: str
    official_message: str | None = None
    prem3_interpretation: str | None = None
    recommended_user_action: str | None = None


class MeridianResolutionStep(BaseModel):
    step: int
    action: str
    owner: str
    evidence_required: str


class MeridianUserFeedback(BaseModel):
    run_id: str
    status: str
    meridian_accepted_input: bool
    eda_ran: bool
    user_action_required: bool
    summary: str
    corrections: list[MeridianCorrectionItem] = Field(default_factory=list)
    resolution_id: str | None = None
    resolution_status: str | None = None
    agent_can_fix: bool = False
    source_system: str = "MERIDIAN"
    source_type: str = "EDA_COMPLETE"
    source_finding_ids: list[str] = Field(default_factory=list)
    official_message: str = ""
    problem_summary: str = ""
    why_it_matters: str = ""
    recommended_steps: list[MeridianResolutionStep] = Field(default_factory=list)
    retry_condition: str = ""
    safe_to_model: bool = False
    feasibility: str = "MODEL_READY"
    fixability: str = "AGENT_FIXABLE"
    created_at: datetime = Field(default_factory=utc_now)


class M3EDARecommendation(BaseModel):
    recommendation_id: str
    priority: str
    recommendation: str
    rationale: str
    source_finding_ids: list[str] = Field(default_factory=list)
    evidence_type: str = "SOURCE_FINDING"


class M3EDAAnalysis(BaseModel):
    run_id: str
    generated_at: datetime = Field(default_factory=utc_now)
    source_eda_receipt_uri: str | None = None
    analysis_source: str = "AGENT"
    executive_summary: str
    overall_assessment: str = ""
    blocking_findings: list[str] = Field(default_factory=list)
    attention_findings: list[str] = Field(default_factory=list)
    informational_findings: list[str] = Field(default_factory=list)
    category_analysis: dict[str, Any] = Field(default_factory=dict)
    cross_category_observations: list[str] = Field(default_factory=list)
    recommendations: list[M3EDARecommendation] = Field(default_factory=list)
    modeler_review_items: list[str] = Field(default_factory=list)
    recommended_handoff_action: str = "MODEL_READY"

    def referenced_finding_ids(self) -> set[str]:
        ids = set(self.blocking_findings)
        ids.update(self.attention_findings)
        ids.update(self.informational_findings)
        for rec in self.recommendations:
            ids.update(rec.source_finding_ids)
        return {item for item in ids if item}


def max_severity(findings: list[MeridianEDAFinding] | list[dict[str, Any]]) -> str:
    rank = 0
    winner = MeridianEDASeverity.INFO.value
    for finding in findings:
        if isinstance(finding, MeridianEDAFinding):
            severity = finding.severity
        else:
            severity = finding["severity"]
        current = SEVERITY_RANK.get(severity, 0)
        if current > rank:
            rank = current
            winner = severity
    return winner


def count_severities(findings: list[MeridianEDAFinding]) -> dict[str, int]:
    counts = {"error_count": 0, "attention_count": 0, "info_count": 0, "max_severity": "INFO"}
    for finding in findings:
        if finding.severity == MeridianEDASeverity.ERROR:
            counts["error_count"] += 1
        elif finding.severity == MeridianEDASeverity.ATTENTION:
            counts["attention_count"] += 1
        else:
            counts["info_count"] += 1
    counts["max_severity"] = max_severity(findings)
    return counts


def category_for_check(check_type: str) -> str:
    if check_type not in CHECK_TYPE_TO_CATEGORY:
        raise ValueError(f"Unknown official Meridian check type: {check_type}")
    return CHECK_TYPE_TO_CATEGORY[check_type]


def canonical_json_fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def canonical_eda_config(mapping: MeridianInputMapping) -> dict[str, Any]:
    """Config identity for EDA idempotency. Does not import google-meridian."""
    return {
        "purpose": "PRE_MODELING_EDA_ONLY",
        "pinned_google_meridian": PINNED_GOOGLE_MERIDIAN,
        "n_draws_prior": DEFAULT_PRIOR_N_DRAW,
        "seed": DEFAULT_PRIOR_SEED,
        "eda_spec_source": "MERIDIAN_DEFAULT",
        "kpi_type": mapping.kpi_type,
        "mapping": mapping.model_dump(mode="json"),
        "thresholds": {
            "kpi_invariability_std": KPI_INVARIABILITY_STD_THRESHOLD,
            "pairwise_corr": PAIRWISE_CORR_THRESHOLD,
            "vif": VIF_THRESHOLD,
            "std": STD_THRESHOLD,
        },
        "posterior_sampling": False,
        "model_fitted": False,
        "model_spec_policy": EDA_MODEL_SPEC_POLICY,
    }


def eda_config_fingerprint(mapping: MeridianInputMapping) -> str:
    return canonical_json_fingerprint(canonical_eda_config(mapping))


def eda_idempotency_key(
    *,
    run_id: str,
    model_input_fingerprint: str,
    meridian_version: str,
    eda_config_fingerprint_value: str,
) -> str:
    return canonical_json_fingerprint(
        {
            "run_id": run_id,
            "model_input_fingerprint": model_input_fingerprint,
            "meridian_version": meridian_version,
            "eda_config_fingerprint": eda_config_fingerprint_value,
        }
    )
