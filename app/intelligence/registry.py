"""Load machine-readable intelligence-registry calculation config.

Thresholds and heuristic factors live in the registry, not duplicated as
magic constants in calculators.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.core.errors import ValidationBlockedError

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "rules" / "intelligence_registry.yaml"


class ParameterBudgetConfig(BaseModel):
    observations_per_parameter_guidance: float = 10.0
    severe_ratio_guidance: float = 7.0
    shadow_media_complexity_factor: float = 3.0
    shadow_source: str = "Chan and Perry (2017) / foundational MMM"
    threshold_authority: str = "PREM3_ADVISORY"
    knowledge_class: str = "MMM_EVIDENCE_HEURISTIC"
    blocks_model_ready: bool = False


class HistoryConfig(BaseModel):
    preferred_geo_weekly_years: float = 2.0
    preferred_national_weekly_years: float = 3.0
    preferred_geo_weekly_periods: int = 104
    preferred_national_weekly_periods: int = 156
    knowledge_class: str = "MMM_EVIDENCE_HEURISTIC"
    blocks_model_ready: bool = False


class CollinearityConfig(BaseModel):
    official_vif: float = 1000.0
    official_pairwise_abs: float = 0.999
    prem3_advisory_vif: float = 50.0
    prem3_advisory_pairwise_abs: float = 0.95
    official_authority: str = "MERIDIAN_OFFICIAL_DEFAULT"
    prem3_authority: str = "PREM3_ADVISORY"


class SpendConfig(BaseModel):
    low_spend_share_review: float = 0.05
    knowledge_class: str = "MMM_EVIDENCE_HEURISTIC"


class IntelligenceCalculatorConfig(BaseModel):
    version: str
    intelligence_version: str
    parameter_budget: ParameterBudgetConfig = Field(default_factory=ParameterBudgetConfig)
    history: HistoryConfig = Field(default_factory=HistoryConfig)
    collinearity: CollinearityConfig = Field(default_factory=CollinearityConfig)
    spend: SpendConfig = Field(default_factory=SpendConfig)
    rules: dict[str, dict[str, Any]] = Field(default_factory=dict)


def _require_mapping(payload: Any, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationBlockedError(f"Corrupt intelligence registry: {label} is not a mapping.")
    return payload


@lru_cache(maxsize=1)
def load_intelligence_config(path: str | None = None) -> IntelligenceCalculatorConfig:
    target = Path(path) if path else REGISTRY_PATH
    if not target.is_file():
        raise ValidationBlockedError(f"Intelligence registry missing: {target}")
    try:
        raw = yaml.safe_load(target.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValidationBlockedError(f"Corrupt intelligence registry YAML: {exc}") from exc
    payload = _require_mapping(raw, "root")
    calc = _require_mapping(payload.get("calculator_config") or {}, "calculator_config")
    rules = {
        str(rule["rule_id"]): rule
        for rule in payload.get("rules") or []
        if isinstance(rule, dict) and rule.get("rule_id")
    }
    return IntelligenceCalculatorConfig(
        version=str(payload.get("version") or ""),
        intelligence_version=str(payload.get("intelligence_version") or ""),
        parameter_budget=ParameterBudgetConfig.model_validate(calc.get("parameter_budget") or {}),
        history=HistoryConfig.model_validate(calc.get("history") or {}),
        collinearity=CollinearityConfig.model_validate(calc.get("collinearity") or {}),
        spend=SpendConfig.model_validate(calc.get("spend") or {}),
        rules=rules,
    )


def rule_authority(rule_id: str) -> dict[str, Any]:
    config = load_intelligence_config()
    rule = config.rules.get(rule_id) or {}
    return {
        "rule_id": rule_id,
        "knowledge_class": rule.get("knowledge_class"),
        "decision_class": rule.get("decision_class"),
        "source_url": rule.get("source_url"),
        "source_tier": rule.get("source_tier"),
        "blocks_model_ready": bool(rule.get("blocks_model_ready")),
        "threshold_authority": rule.get("threshold_authority"),
        "human_owner": rule.get("human_owner"),
        "best_practice_guidance": rule.get("best_practice_guidance"),
        "status": rule.get("status"),
    }
