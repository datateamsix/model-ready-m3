"""Cloud-controlled first learning cycle on a frozen Cloud Run revision.

DOMAIN_VIEW v2 is activated as registry data. The application image does not
change. Dataset C behavior is compared only on predeclared effect fields.
"""

from __future__ import annotations

from typing import Any

from app.mel.behavior import (
    ExpectedBehaviorEffect,
    action_rank,
    behavior_delta,
    effect_succeeded,
)
from app.mel.models import MelError

FROZEN_REVISION = "modelready-m3-00013-c4s"
FROZEN_IMAGE_DIGEST = (
    "sha256:7dffe4904c1a3ce9e2bb7426793954608bb3d3b5c274b2dc592fcefb0246f6d6"
)
FROZEN_CODE_SHA = "1222eb6fcdabec5ea6132347c8b6df2bc907f705"
FROZEN_SERVICE = "modelready-m3"
FROZEN_REGION = "us-central1"
REGISTRY_GS_URI = (
    "gs://modelready-m3-912257136465-artifacts/experiments/"
    "cloud_first_learning_cycle_001/domain_view_registry/"
)
CLOUD_A_RUN_ID = "m3cloud653724094004"
CLOUD_B_RUN_ID = "m3cloud856c4fdede10"
CLOUD_EXPERIMENT_ID = "prem3-cloud-learning-cycle-00013-20260817"
EXPECTED_V1_VERSION = "1.0.0"
EXPECTED_V1_FINGERPRINT = (
    "b3ad518e2875848e32588e1c581ba619b9fd9e075cbbfea5eb7e7571bb8e46cf"
)
SEALED_PACKAGE_FINGERPRINT = (
    "f1bfaa5ba98b8f6d94cccb6b7a19c1e50ab8e315567e82fa3cf22129193bf18f"
)


def assert_frozen_runtime(probe: dict[str, Any]) -> None:
    runtime = probe.get("runtime") or {}
    revision = probe.get("revision") or runtime.get("revision")
    if revision != FROZEN_REVISION:
        raise MelError(
            f"learning runtime is not frozen revision {FROZEN_REVISION}: {revision}"
        )


def assert_domain_view_control(
    meta: dict[str, Any],
    *,
    version: str,
    fingerprint: str,
    promoted_lesson_count: int,
) -> None:
    loaded_version = meta.get("domain_view_version")
    loaded_fp = meta.get("domain_view_fingerprint")
    loaded_count = int(meta.get("promoted_lesson_count") or 0)
    if loaded_version != version or loaded_fp != fingerprint:
        raise MelError(
            "DOMAIN_VIEW control failed: "
            f"loaded {loaded_version}/{loaded_fp}, expected {version}/{fingerprint}"
        )
    if loaded_count != promoted_lesson_count:
        raise MelError(
            "DOMAIN_VIEW lesson count failed: "
            f"loaded {loaded_count}, expected {promoted_lesson_count}"
        )


def assert_cv1_control(behavior: dict[str, Any]) -> None:
    rank = action_rank(list(behavior.get("action_ids") or []), "modeler-questions")
    claims = list(behavior.get("retrieved_claim_ids") or [])
    if rank != 2:
        raise MelError(
            "C-v1 control failed: modeler-questions rank "
            f"was {rank}, expected 2 before promotion"
        )
    if claims:
        raise MelError(
            "C-v1 control failed: retrieved experiential claims must be empty "
            f"before promotion, found {claims}"
        )


def measure_declared_effect(
    before: dict[str, Any],
    after: dict[str, Any],
    effect: ExpectedBehaviorEffect,
) -> dict[str, Any]:
    """Compare only the predeclared effect. Do not infer additional lessons."""
    delta = behavior_delta(before, after, effect=effect)
    allowed = set(effect.allowed_change_fields)
    observed_fields = {
        "handoff_action_order": list(before.get("action_ids") or [])
        != list(after.get("action_ids") or []),
        "recommended_presentation_order": list(
            before.get("recommended_presentation_order") or []
        )
        != list(after.get("recommended_presentation_order") or []),
        "retrieved_claim_ids": list(before.get("retrieved_claim_ids") or [])
        != list(after.get("retrieved_claim_ids") or []),
    }
    undeclared = [
        name for name, changed in observed_fields.items() if changed and name not in allowed
    ]
    return {
        "delta": delta,
        "effect_succeeded": effect_succeeded(delta, effect),
        "undeclared_behavior_field_changes": undeclared,
        "inference_used": False,
    }
