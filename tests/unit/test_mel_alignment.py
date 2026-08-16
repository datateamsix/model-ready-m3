"""Precheck ↔ official Meridian alignment tests."""

from __future__ import annotations

from app.mel.alignment import align_precheck_and_eda
from app.mel.models import AlignmentRelation


def test_alignment_maps_related_and_new_and_precheck_only() -> None:
    records = align_precheck_and_eda(
        {
            "findings": [
                {"finding_id": "PRE-PARAM", "dimension": "PARAMETER_PRESSURE"},
                {"finding_id": "PRE-MISS", "dimension": "MISSINGNESS_EVIDENCE"},
            ]
        },
        {
            "findings": [
                {
                    "finding_id": "EDA-DA",
                    "check_type": "DATA_ADEQUACY",
                    "severity": "ATTENTION",
                },
                {
                    "finding_id": "EDA-NEW",
                    "check_type": "PRIOR_PROBABILITY",
                    "severity": "INFO",
                },
            ]
        },
    )
    relations = {item.relation for item in records}
    assert AlignmentRelation.RELATED in relations
    assert AlignmentRelation.PRECHECK_ONLY in relations
    assert AlignmentRelation.NEW_EDA_SIGNAL in relations
    assert all(item.proposed_by == "DETERMINISTIC" for item in records)
