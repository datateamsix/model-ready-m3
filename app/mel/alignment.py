"""Precheck ↔ official Meridian EDA alignment.

Official Meridian remains authoritative. Alignment records a relationship;
it does not rewrite official severity, text, or origin.
"""

from __future__ import annotations

from typing import Any

from app.mel.models import AlignmentRecord, AlignmentRelation

DIMENSION_TO_CHECK = {
    "PARAMETER_PRESSURE": "DATA_ADEQUACY",
    "COLLINEARITY": "MULTICOLLINEARITY",
    "CHANNEL_VARIATION": "STANDARD_DEVIATION",
    "POPULATION_RELATIONSHIPS": "POPULATION_CORRELATION",
    "MEDIA_SPEND_CONSISTENCY": "COST_PER_MEDIA_UNIT",
    "HISTORY": "DATA_ADEQUACY",
    "GEO_COVERAGE": "DATA_ADEQUACY",
}


def _prem3_findings(pre_eda: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not pre_eda:
        return []
    findings = pre_eda.get("findings") or pre_eda.get("diagnostic_findings") or []
    if isinstance(findings, list):
        return [item for item in findings if isinstance(item, dict)]
    return []


def _meridian_findings(official: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not official:
        return []
    findings = official.get("findings") or []
    if isinstance(findings, list):
        return [item for item in findings if isinstance(item, dict)]
    return []


def align_precheck_and_eda(
    pre_eda: dict[str, Any] | None,
    official: dict[str, Any] | None,
) -> list[AlignmentRecord]:
    prem3 = _prem3_findings(pre_eda)
    meridian = _meridian_findings(official)
    used_meridian: set[str] = set()
    records: list[AlignmentRecord] = []

    meridian_by_check: dict[str, list[dict[str, Any]]] = {}
    for finding in meridian:
        check = str(finding.get("check_type") or finding.get("checkType") or "")
        meridian_by_check.setdefault(check, []).append(finding)

    for item in prem3:
        finding_id = str(item.get("finding_id") or "")
        dimension = str(item.get("dimension") or "")
        mapped = DIMENSION_TO_CHECK.get(dimension)
        matches = meridian_by_check.get(mapped or "", [])
        if mapped and matches:
            partner = matches[0]
            partner_id = str(partner.get("finding_id") or "")
            used_meridian.add(partner_id)
            records.append(
                AlignmentRecord(
                    prem3_finding_id=finding_id or None,
                    meridian_finding_id=partner_id or None,
                    relation=AlignmentRelation.RELATED
                    if str(partner.get("severity") or "") != "ERROR"
                    else AlignmentRelation.CONFIRMED,
                    reason=(
                        f"PreM3 dimension {dimension} maps to official check {mapped}. "
                        "This is a relationship, not a claim that PreM3 predicted Meridian."
                    ),
                )
            )
        else:
            records.append(
                AlignmentRecord(
                    prem3_finding_id=finding_id or None,
                    meridian_finding_id=None,
                    relation=AlignmentRelation.PRECHECK_ONLY,
                    reason=f"PreM3 dimension {dimension} has no official Meridian counterpart.",
                )
            )

    for finding in meridian:
        finding_id = str(finding.get("finding_id") or "")
        if finding_id in used_meridian:
            continue
        records.append(
            AlignmentRecord(
                prem3_finding_id=None,
                meridian_finding_id=finding_id or None,
                relation=AlignmentRelation.NEW_EDA_SIGNAL,
                reason="Official Meridian finding without a mapped PreM3 pre-EDA counterpart.",
            )
        )

    if not prem3 and not meridian:
        records.append(
            AlignmentRecord(
                relation=AlignmentRelation.NOT_COMPARABLE,
                reason="Missing PreM3 pre-EDA and/or official Meridian EDA evidence.",
            )
        )
    return records
