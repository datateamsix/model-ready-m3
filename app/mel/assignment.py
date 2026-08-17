"""Labeled assignment catalog and MEL evidence capture.

Dataset A/B/C share the manifest-driven coordinator. This module still
closes MEL episodes from verified snapshots. Dataset role comes from the
typed catalog, not from business-name heuristics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.core.contracts import DurableRunState
from app.core.model_intent import (
    DATASET_A_MODEL_INTENT,
    DATASET_B_MODEL_INTENT,
    DATASET_C_MODEL_INTENT,
    ModelIntent,
)
from app.core.run_repository import LocalFilesystemRunRepository, fingerprint_package_dir
from app.core.state import RunStage
from app.intelligence.orchestrator import run_pre_eda_diagnostics
from app.intelligence.persist import persist_intelligence_artifacts
from app.intelligence.source import (
    FixtureAdapter,
    fingerprint_frame,
    load_verified_snapshot,
    schema_fingerprint_for,
)
from app.mel.behavior import (
    DEFAULT_PRESENTATION_ORDER,
    extract_behavior_snapshot,
)
from app.mel.episode import close_experience_episode, persist_episode
from app.mel.models import DatasetRole
from app.mel.reflect import reflect_on_experience_episode
from app.response.builder import ResponseBuilder
from app.synthetic.paths import DATASET_A_DIR, DATASET_B_DIR, DATASET_C_DIR
from app.tools.artifacts import write_json_artifact
from app.tools.meridian_contract import generate_meridian_input_contract

DATASET_SPECS: dict[str, dict[str, Any]] = {
    "A": {
        "dataset_id": "dataset_a_music_center",
        "business": "Music Center",
        "role": DatasetRole.TRAINING_EXPERIENCE,
        "holdout": False,
        "root": DATASET_A_DIR,
        "intent": DATASET_A_MODEL_INTENT,
        "organization_id": "music-center",
        "package_uri": "local://datasets/music_center/dataset_a/raw/",
    },
    "B": {
        "dataset_id": "dataset_b_stride_and_field",
        "business": "Stride & Field",
        "role": DatasetRole.LEARNING_EVIDENCE,
        "holdout": False,
        "root": DATASET_B_DIR,
        "intent": DATASET_B_MODEL_INTENT,
        "organization_id": "stride-and-field",
        "package_uri": "local://datasets/stride_and_field/dataset_b/raw/",
    },
    "C": {
        "dataset_id": "dataset_c_summit_and_pine",
        "business": "Summit & Pine",
        "role": DatasetRole.SEALED_HOLDOUT,
        "holdout": True,
        "root": DATASET_C_DIR,
        "intent": DATASET_C_MODEL_INTENT,
        "organization_id": "summit-and-pine",
        "package_uri": "local://datasets/summit_and_pine/dataset_c/raw/",
    },
}


def spec_for_dataset_id(dataset_id: str) -> dict[str, Any] | None:
    for spec in DATASET_SPECS.values():
        if spec["dataset_id"] == dataset_id:
            return spec
    return None


def resolve_assignment_identity(
    *,
    dataset_id: str = "",
    dataset_role: str | None = None,
    qualification_mode: str | None = None,
) -> tuple[str, str | None, str | None]:
    """Fill typed role/mode from the assignment catalog when dataset_id is known."""
    spec = spec_for_dataset_id(dataset_id) if dataset_id else None
    if spec is None:
        return dataset_id, dataset_role, qualification_mode
    role = dataset_role or spec["role"].value
    mode = qualification_mode
    if spec["role"] is DatasetRole.SEALED_HOLDOUT and not mode:
        mode = "HOLDOUT_QUALIFICATION_ONLY"
    return dataset_id, role, mode


def capture_behavior(bundle: dict[str, Any]) -> dict[str, Any]:
    routing = bundle.get("learned_routing") or {}
    interview = bundle.get("semantic_interview") or {}
    families = [
        str(item.get("question_family") or item.get("family") or "")
        for item in interview.get("questions") or interview.get("triggers") or []
        if item.get("question_family") or item.get("family")
    ]
    if not families:
        families = list(
            ((bundle.get("receipt") or {}).get("semantic_trigger_summary") or {}).get(
                "families"
            )
            or []
        )
    assessment = ResponseBuilder().assessment(bundle)
    return extract_behavior_snapshot(
        question_families=families,
        finding_ids=[item.finding_id for item in assessment.findings],
        action_ids=[item.action_id for item in assessment.actions],
        action_owners=[item.owner.value for item in assessment.actions],
        recommended_presentation_order=list(
            routing.get("recommended_presentation_order") or DEFAULT_PRESENTATION_ORDER
        ),
        retrieved_claim_ids=list(routing.get("retrieved_claim_ids") or []),
        diagnostic_routes=[
            "run_pre_eda_diagnostics",
            "detect_semantic_question_triggers",
            "ResponseBuilder.assessment",
        ],
    )


def _snapshot(run_id: str, spec: dict[str, Any]):
    root: Path = spec["root"]
    intent: ModelIntent = spec["intent"]
    frame = pd.read_csv(root / "truth" / "expected_model_ready_weekly.csv")
    contract = generate_meridian_input_contract(
        run_id=run_id,
        intent=intent,
        frame=frame,
        project_id="fixture-project",
        dataset_id="fixture_dataset",
        table_id=f"{run_id}_table",
    )
    fp = fingerprint_frame(frame, contract)
    schema_fp = schema_fingerprint_for(frame, contract)
    adapter = FixtureAdapter(
        run_id=run_id,
        frame=frame,
        contract=contract,
        expected_fingerprint=fp,
        schema_fingerprint=schema_fp,
    )
    return load_verified_snapshot(run_id, adapter=adapter), fp, schema_fp


def run_intelligence_assignment(
    dataset_key: str,
    *,
    repo: LocalFilesystemRunRepository,
    run_id: str,
    runtime_revision: str | None = None,
) -> dict[str, Any]:
    spec = DATASET_SPECS[dataset_key]
    raw_dir: Path = spec["root"] / "raw"
    package_fp, _hashes = fingerprint_package_dir(raw_dir)
    snapshot, model_fp, schema_fp = _snapshot(run_id, spec)
    bundle = run_pre_eda_diagnostics(snapshot)
    behavior = capture_behavior(bundle)
    semantic_open = int((bundle.get("semantic_interview") or {}).get("question_count") or 0) > 0
    state = DurableRunState(
        run_id=run_id,
        organization_id=spec["organization_id"],
        workspace_id="mmm-demo",
        package_uri=spec["package_uri"],
        package_fingerprint=package_fp,
        stage=(
            RunStage.WAITING_FOR_APPROVAL if semantic_open else RunStage.FAILED
        ),
        artifact_prefix=f"local://artifacts/{spec['organization_id']}/mmm-demo/runs/{run_id}",
        physical_schema_fingerprint=model_fp,
        status="USER_REQUIRED" if semantic_open else "FAILED",
        input_file_count=len(_hashes),
    )
    repo.save_run(state)
    persist_intelligence_artifacts(repo=repo, state=state, bundle=bundle)
    write_json_artifact(
        repo._artifact_path(run_id, "intelligence/behavior_snapshot.json"),
        behavior,
    )
    write_json_artifact(
        repo._artifact_path(run_id, "response/run_response.json"),
        {
            "assessment_action_ids": behavior["action_ids"],
            "question_families": behavior["question_families"],
            "finding_ids": behavior["finding_ids"],
            "learned_routing": bundle.get("learned_routing"),
        },
    )
    episode = close_experience_episode(
        run_id,
        repo=repo,
        runtime_revision=runtime_revision,
        holdout=bool(spec["holdout"]),
        dataset_role=spec["role"],
    )
    episode.summary["business"] = spec["business"]
    episode.summary["dataset_id"] = spec["dataset_id"]
    episode.summary["assignment_mode"] = "INTELLIGENCE_EVALUATION"
    episode.summary["model_input_source"] = "GENERATED_OR_SEALED_MODEL_READY_TABLE"
    episode.summary["schema_fingerprint"] = schema_fp
    persist_episode(repo, episode)
    reflection = None
    if not spec["holdout"]:
        reflection = reflect_on_experience_episode(
            episode.episode_id, repo=repo, run_id=run_id
        )
    return {
        "dataset_key": dataset_key,
        "dataset_id": spec["dataset_id"],
        "business": spec["business"],
        "run_id": run_id,
        "package_fingerprint": package_fp,
        "model_input_fingerprint": model_fp,
        "schema_fingerprint": schema_fp,
        "episode": episode,
        "reflection": reflection,
        "bundle": bundle,
        "behavior": behavior,
        "terminal_outcome": episode.terminal_outcome.value,
        "domain_view_version": episode.domain_view_version,
        "domain_view_fingerprint": episode.domain_view_fingerprint,
    }
