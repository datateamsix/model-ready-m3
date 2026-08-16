"""Load structured DOMAIN_VIEW inputs from existing catalogs and claim files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from app.domain.intelligence.models import (
    ClaimScope,
    DomainViewClaim,
    DomainViewSourceVersions,
    KnowledgeClass,
    LearnedAuthority,
    PromotedLessonInput,
    ScopeLevel,
    SourceType,
)
from app.domain.intelligence.validate import layer_for_class
from app.rules.engine import load_rule_catalog

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_MERIDIAN_CATALOG = REPO_ROOT / "app" / "rules" / "meridian.yaml"
DEFAULT_INTELLIGENCE_REGISTRY = REPO_ROOT / "app" / "rules" / "intelligence_registry.yaml"
DEFAULT_BASE_CLAIMS = DATA_DIR / "base_claims.yaml"
DEFAULT_PROMOTED_LESSONS = DATA_DIR / "promoted_lessons.yaml"
DEFAULT_INTELLIGENCE_VERSION = (
    REPO_ROOT / "docs" / "context" / "intelligence" / "intelligence_version.json"
)


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")
    return payload


def load_source_versions(path: Path | None = None) -> DomainViewSourceVersions:
    payload = json.loads((path or DEFAULT_INTELLIGENCE_VERSION).read_text(encoding="utf-8"))
    meridian = load_rule_catalog(DEFAULT_MERIDIAN_CATALOG)
    intelligence = _load_yaml(DEFAULT_INTELLIGENCE_REGISTRY)
    return DomainViewSourceVersions(
        intelligence_version=str(payload["intelligence_version"]),
        product_context_version=str(payload["product_context_version"]),
        mmm_boot_context_version=str(payload["mmm_boot_context_version"]),
        rule_registry_version=str(meridian.get("version", "unknown")),
        intelligence_registry_version=str(intelligence.get("version", "unknown")),
        source_verification_date=str(payload["last_verified"]),
        meridian_worker_pin=str(payload["meridian_worker_pin"]),
    )


def _authority_from_decision(decision_class: str | None) -> LearnedAuthority:
    if decision_class in {"ADVISORY"}:
        return LearnedAuthority.ADVISORY
    return LearnedAuthority.NONE


def _source_type_from_class(knowledge_class: KnowledgeClass, source_tier: str | None) -> SourceType:
    if knowledge_class is KnowledgeClass.MERIDIAN_NORMATIVE:
        return SourceType.OFFICIAL_SOURCE
    if knowledge_class in {
        KnowledgeClass.PREM3_POLICY,
        KnowledgeClass.PREM3_POLICY_BLOCKER,
    }:
        return SourceType.PREM3_POLICY
    if source_tier == "TIER_3_CROSS_FRAMEWORK":
        return SourceType.CROSS_FRAMEWORK_EVIDENCE
    return SourceType.FOUNDATIONAL_EVIDENCE


def _claim_from_rule(rule: dict[str, Any], *, prefix: str, catalog_version: str) -> DomainViewClaim:
    rule_id = str(rule.get("id") or rule.get("rule_id"))
    knowledge_class = KnowledgeClass(str(rule.get("knowledge_class", "PREM3_POLICY")))
    notes = str(rule.get("notes") or rule.get("best_practice_guidance") or "").strip()
    name = str(rule.get("name", rule_id)).replace("_", " ")
    statement = notes or f"{name} is an active PreM3/Meridian operational rule."
    last_verified = str(rule.get("last_verified") or "")
    return DomainViewClaim(
        claim_id=f"{prefix}-{rule_id}",
        statement=statement,
        knowledge_class=knowledge_class,
        layer=layer_for_class(knowledge_class),
        authority=_authority_from_decision(rule.get("decision_class")),
        scope=ClaimScope(level=ScopeLevel.GLOBAL),
        source_type=_source_type_from_class(knowledge_class, rule.get("source_tier")),
        source_refs=[str(rule.get("source") or rule.get("source_url") or "")],
        source_version=catalog_version,
        evidence=[f"rule:{rule_id}"],
        last_validated_at=last_verified or None,
        first_added_at=last_verified or None,
        prohibited_overrides=["MERIDIAN_NORMATIVE"]
        if knowledge_class is not KnowledgeClass.MERIDIAN_NORMATIVE
        else [],
    )


def claims_from_rule_catalogs(
    meridian_path: Path | None = None,
    intelligence_path: Path | None = None,
) -> list[DomainViewClaim]:
    meridian = load_rule_catalog(meridian_path or DEFAULT_MERIDIAN_CATALOG)
    intelligence = _load_yaml(intelligence_path or DEFAULT_INTELLIGENCE_REGISTRY)
    claims = [
        _claim_from_rule(rule, prefix="DV", catalog_version=str(meridian.get("version", "")))
        for rule in meridian.get("rules", [])
    ]
    claims.extend(
        _claim_from_rule(
            rule,
            prefix="DV",
            catalog_version=str(intelligence.get("version", "")),
        )
        for rule in intelligence.get("rules", [])
    )
    return claims


def claims_from_base_file(path: Path | None = None) -> list[DomainViewClaim]:
    payload = _load_yaml(path or DEFAULT_BASE_CLAIMS)
    claims: list[DomainViewClaim] = []
    for raw in payload.get("claims", []):
        knowledge_class = KnowledgeClass(str(raw["knowledge_class"]))
        scope_raw = raw.get("scope") or {"level": "GLOBAL"}
        claims.append(
            DomainViewClaim(
                claim_id=str(raw["claim_id"]),
                statement=str(raw["statement"]),
                knowledge_class=knowledge_class,
                layer=layer_for_class(knowledge_class),
                authority=LearnedAuthority(str(raw.get("authority", "NONE"))),
                scope=ClaimScope(
                    level=ScopeLevel(str(scope_raw.get("level", "GLOBAL"))),
                    value=scope_raw.get("value"),
                ),
                source_type=SourceType(str(raw["source_type"])),
                source_refs=list(raw.get("source_refs") or []),
                source_version=str(raw.get("source_version") or payload.get("version") or ""),
                evidence=list(raw.get("evidence") or []),
                behavior_effect=raw.get("behavior_effect"),
                first_added_at=raw.get("first_added_at"),
                last_validated_at=raw.get("last_validated_at"),
                prohibited_overrides=list(raw.get("prohibited_overrides") or []),
            )
        )
    return claims


def load_promoted_lessons(path: Path | None = None) -> tuple[str, list[PromotedLessonInput]]:
    payload = _load_yaml(path or DEFAULT_PROMOTED_LESSONS)
    version = str(payload.get("version", "0.0.0"))
    lessons: list[PromotedLessonInput] = []
    for raw in payload.get("promoted_lessons") or []:
        scope_raw = raw.get("scope") or {"level": "GLOBAL"}
        lessons.append(
            PromotedLessonInput(
                lesson_id=str(raw["lesson_id"]),
                statement=str(raw["statement"]),
                knowledge_class=KnowledgeClass(
                    str(raw.get("knowledge_class", "VALIDATED_EXPERIENCE_PATTERN"))
                ),
                authority=LearnedAuthority(str(raw["authority"])),
                scope=ClaimScope(
                    level=ScopeLevel(str(scope_raw.get("level", "GLOBAL"))),
                    value=scope_raw.get("value"),
                ),
                source_refs=list(raw.get("source_refs") or []),
                evidence=list(raw.get("evidence") or []),
                regression_status=str(raw.get("regression_status", "PASSED")),
                behavior_effect=raw.get("behavior_effect"),
                promotion_status=raw.get("promotion_status", "PROMOTED"),
                last_validated_at=raw.get("last_validated_at"),
            )
        )
    return version, lessons
