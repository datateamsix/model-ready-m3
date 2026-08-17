"""Run the cloud-controlled A/B → DOMAIN_VIEW v2 → Dataset C application.

Freezes Cloud Run revision modelready-m3-00013-c4s. Captures C-v1 first.
Activates DOMAIN_VIEW v2 as GCS registry data only. Does not rebuild the image.
Does not modify frontend/. Does not use Dataset C as training evidence.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from app.core.run_repository import (
    GcsRunRepository,
    LocalFilesystemRunRepository,
    fingerprint_package_dir,
)
from app.mel.assignment import run_intelligence_assignment
from app.mel.behavior import ExpectedBehaviorEffect, semantic_question_routing_effect
from app.mel.cloud_learning import (
    CLOUD_A_RUN_ID,
    CLOUD_B_RUN_ID,
    CLOUD_EXPERIMENT_ID,
    EXPECTED_V1_FINGERPRINT,
    EXPECTED_V1_VERSION,
    FROZEN_CODE_SHA,
    FROZEN_IMAGE_DIGEST,
    FROZEN_REGION,
    FROZEN_REVISION,
    FROZEN_SERVICE,
    REGISTRY_GS_URI,
    SEALED_PACKAGE_FINGERPRINT,
    assert_cv1_control,
    assert_domain_view_control,
    assert_frozen_runtime,
    measure_declared_effect,
)
from app.mel.episode import load_episode, persist_episode
from app.mel.experiment import (
    EXPERIMENT_ID,
    application_plan,
    build_experiment_manifest,
    dump_behavior_comparison,
    evaluate_ab_candidates,
    promote_selected,
    routing_regression_for,
    write_json,
)
from app.mel.fingerprint import fingerprint_payload
from app.mel.holdout_evaluate import evaluate_holdout_application
from app.mel.ledger import record_application as ledger_record_application
from app.mel.models import DatasetRole, ExperienceEpisode, MelError
from app.mel.promote import (
    REGISTRY_CACHE_ENV,
    REGISTRY_DIR_ENV,
    REGISTRY_GS_ENV,
    active_domain_view_meta,
    load_active_view,
    seed_bootstrap_registry,
)
from app.mel.reflect import reflect_on_experience_episode
from app.mel.routing_apply import retrieve_routing_hints
from app.synthetic.paths import DATASET_A_DIR, DATASET_B_DIR, DATASET_C_DIR, REPO_ROOT
from scripts.smoke_cloud_run import (
    CLOUD_RUN_ENV,
    EXPECTED_APP,
    PROBE_PROMPT,
    _extract_probe,
    _identity_token,
    _json_request,
    _run_prompt,
    _service_url,
)

OUT_EXPERIENCE = REPO_ROOT / "experience" / "cloud_learning"
OUT_EVAL = REPO_ROOT / "evaluation"


def _git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _bind_gcs_registry(cache_dir: Path) -> None:
    os.environ.pop(REGISTRY_DIR_ENV, None)
    os.environ[REGISTRY_GS_ENV] = REGISTRY_GS_URI
    os.environ[REGISTRY_CACHE_ENV] = str(cache_dir)


def _probe_cloud_run() -> dict[str, Any]:
    app_url = _service_url().rstrip("/")
    token = _identity_token(app_url)
    session_id = f"cloud_learning_probe_{int(time.time())}"
    session = _json_request(
        "POST",
        f"{app_url}/apps/{EXPECTED_APP}/users/cloud_test_user/sessions/{session_id}",
        token,
        body={},
    )
    if not isinstance(session, dict) or session.get("id") != session_id:
        raise MelError(f"Cloud Run probe session failed: {session}")
    text, events = _run_prompt(app_url, token, PROBE_PROMPT, session_id)
    probe = _extract_probe(events, text)
    if not isinstance(probe, dict):
        raise MelError("Cloud Run probe did not return structured cloud_runtime_probe output")
    runtime = probe.get("runtime") or {}
    details = probe.get("details") or {}
    return {
        "revision": runtime.get("revision"),
        "runtime": runtime,
        "domain_view": details.get("domain_view") or {},
        "checks": probe.get("checks"),
        "raw": probe,
    }


def _copy_cloud_episode(local_repo: LocalFilesystemRunRepository, run_id: str) -> ExperienceEpisode:
    cloud_repo = GcsRunRepository(
        raw_bucket=CLOUD_RUN_ENV["MODELREADY_RAW_BUCKET"],
        artifact_bucket=CLOUD_RUN_ENV["MODELREADY_ARTIFACT_BUCKET"],
    )
    episode = load_episode(cloud_repo, run_id)
    if episode is None:
        raise MelError(f"cloud episode missing for {run_id}")
    persist_episode(local_repo, episode)
    return episode


def _annotate_training_episode(episode: ExperienceEpisode) -> ExperienceEpisode:
    summary = dict(episode.summary or {})
    summary["business"] = "Music Center"
    summary["dataset_id"] = "dataset_a_music_center"
    summary["assignment_mode"] = "CLOUD_TASKMASTER"
    summary["cloud_run_id"] = CLOUD_A_RUN_ID
    return episode.model_copy(
        update={
            "dataset_role": DatasetRole.TRAINING_EXPERIENCE,
            "runtime_revision": FROZEN_REVISION,
            "summary": summary,
        }
    )


def main() -> int:
    cache_v1 = Path(tempfile.mkdtemp(prefix="prem3-dv-v1-"))
    _bind_gcs_registry(cache_v1)
    probe_v1 = _probe_cloud_run()
    assert_frozen_runtime(probe_v1)
    dv_v1 = probe_v1["domain_view"]
    assert_domain_view_control(
        dv_v1,
        version=EXPECTED_V1_VERSION,
        fingerprint=EXPECTED_V1_FINGERPRINT,
        promoted_lesson_count=0,
    )
    meta_v1 = active_domain_view_meta()
    assert_domain_view_control(
        meta_v1,
        version=EXPECTED_V1_VERSION,
        fingerprint=EXPECTED_V1_FINGERPRINT,
        promoted_lesson_count=0,
    )

    view_v1 = load_active_view()
    dataset_a_fp, _ = fingerprint_package_dir(DATASET_A_DIR / "raw")
    dataset_b_fp, _ = fingerprint_package_dir(DATASET_B_DIR / "raw")
    dataset_c_fp, _ = fingerprint_package_dir(DATASET_C_DIR / "raw")
    sealed = json.loads((DATASET_C_DIR / "package_manifest.json").read_text(encoding="utf-8"))
    if sealed["package_fingerprint"] != SEALED_PACKAGE_FINGERPRINT:
        raise MelError("Dataset C sealed package fingerprint changed before C-v1")

    freeze = {
        "frozen": True,
        "service": FROZEN_SERVICE,
        "region": FROZEN_REGION,
        "revision": FROZEN_REVISION,
        "image_digest": FROZEN_IMAGE_DIGEST,
        "code_sha": FROZEN_CODE_SHA,
        "branch_sha": _git_sha(),
        "domain_view_registry_gs_uri": REGISTRY_GS_URI,
        "expected_loaded_domain_view_version": EXPECTED_V1_VERSION,
        "note": (
            "Any application-code change requires a new revision and a restart of "
            "C-v1/C-v2. DOMAIN_VIEW pointer updates on this GCS prefix do not."
        ),
        "probe": {
            "revision": probe_v1["revision"],
            "domain_view": dv_v1,
        },
    }
    write_json(OUT_EVAL / "cloud_learning_revision_freeze.json", freeze)

    work = REPO_ROOT / "artifacts" / "cloud_learning_experiment"
    repo = LocalFilesystemRunRepository(
        root=work / "repo", raw_bucket="raw", artifact_bucket="artifacts"
    )
    ledger = work / "ledger"
    registry = work / "registry"
    seed_bootstrap_registry(registry)

    c_v1 = run_intelligence_assignment(
        "C", repo=repo, run_id="dataset-c-v1-cloud-00013", runtime_revision=FROZEN_REVISION
    )
    assert_cv1_control(c_v1["behavior"])
    if c_v1["domain_view_version"] != EXPECTED_V1_VERSION:
        raise MelError("C-v1 did not load DOMAIN_VIEW 1.0.0")
    write_json(
        OUT_EVAL / "dataset_c_v1_cloud_baseline.json",
        {
            "run_id": c_v1["run_id"],
            "cloud_run": True,
            "cloud_run_revision": FROZEN_REVISION,
            "assignment_mode": "INTELLIGENCE_EVALUATION",
            "dataset_fingerprint": c_v1["package_fingerprint"],
            "sealed_package_fingerprint": SEALED_PACKAGE_FINGERPRINT,
            "model_input_fingerprint": c_v1["model_input_fingerprint"],
            "domain_view_version": c_v1["domain_view_version"],
            "domain_view_fingerprint": c_v1["domain_view_fingerprint"],
            "behavior": c_v1["behavior"],
            "behavior_fingerprint": fingerprint_payload(c_v1["behavior"]),
            "terminal_state": c_v1["terminal_outcome"],
            "evaluation_only": True,
            "captured_before_promotion": True,
        },
    )

    cloud_a = _annotate_training_episode(_copy_cloud_episode(repo, CLOUD_A_RUN_ID))
    persist_episode(repo, cloud_a)
    reflection_a = reflect_on_experience_episode(
        cloud_a.episode_id, repo=repo, run_id=CLOUD_A_RUN_ID
    )
    b_run = run_intelligence_assignment(
        "B", repo=repo, run_id="dataset-b-cloud-learning-00013", runtime_revision=FROZEN_REVISION
    )
    if b_run["reflection"] is None:
        raise MelError("Dataset B reflection missing")
    write_json(OUT_EXPERIENCE / "experience_episode_a.json", cloud_a.model_dump(mode="json"))
    write_json(
        OUT_EXPERIENCE / "experience_reflection_a.json",
        reflection_a.model_dump(mode="json"),
    )
    write_json(
        OUT_EXPERIENCE / "experience_episode_b.json",
        b_run["episode"].model_dump(mode="json"),
    )
    write_json(
        OUT_EXPERIENCE / "experience_reflection_b.json",
        b_run["reflection"].model_dump(mode="json"),
    )
    write_json(
        OUT_EXPERIENCE / "dataset_b_cloud_map_mend_context.json",
        {
            "cloud_run_id": CLOUD_B_RUN_ID,
            "revision": FROZEN_REVISION,
            "episode_closed_on_cloud": False,
            "durable_stage": "REMEDIATING",
            "learning_reflection_source": "INTELLIGENCE_EVALUATION",
            "note": (
                "Dataset B Map/Mend on 00013 remains USER_REQUIRED/non-terminal. "
                "The B reflection used for candidates is intelligence evaluation "
                "of the same Dataset B package under the frozen revision's "
                "DOMAIN_VIEW v1."
            ),
        },
    )

    outcome = evaluate_ab_candidates(
        episode_a=cloud_a,
        reflection_a=reflection_a,
        episode_b=b_run["episode"],
        reflection_b=b_run["reflection"],
        view=view_v1,
        ledger_dir=ledger,
    )
    write_json(OUT_EXPERIENCE / "candidate_lessons.json", {"candidates": outcome["candidates"]})
    write_json(
        OUT_EXPERIENCE / "candidate_evaluations.json",
        {
            "eligible_count": outcome["eligible_count"],
            "ranking_rule": outcome["ranking_rule"],
            "isolation_fingerprint": outcome["isolation_fingerprint"],
            "selected_candidate_id": None
            if outcome["selected"] is None
            else outcome["selected"]["candidate"].candidate_lesson_id,
            "candidates": outcome["candidates"],
        },
    )
    if outcome["selected"] is None:
        write_json(
            OUT_EXPERIENCE / "cloud_learning_status.json",
            {
                "status": "NO_SAFE_PROMOTABLE_LESSON",
                "experience_learned": False,
                "experience_applied": False,
            },
        )
        print("NO_SAFE_PROMOTABLE_LESSON")
        return 0

    candidate = outcome["selected"]["candidate"]
    evaluation = outcome["selected"]["evaluation"]
    regression = routing_regression_for(candidate, view_v1)
    promoted = promote_selected(
        candidate=candidate,
        evaluation=evaluation,
        view=view_v1,
        registry_dir=registry,
        ledger_dir=ledger,
        regression=regression,
    )
    write_json(
        OUT_EXPERIENCE / "experience_learned_receipt.json",
        promoted["receipt"].model_dump(mode="json"),
    )
    write_json(OUT_EXPERIENCE / "domain_view_diff.json", promoted["diff"])

    effect = ExpectedBehaviorEffect.model_validate(
        candidate.expected_behavior_effect or semantic_question_routing_effect().model_dump()
    )
    plan = application_plan(
        experiment_id=CLOUD_EXPERIMENT_ID,
        lesson_id=candidate.candidate_lesson_id,
        dataset_c_fingerprint=dataset_c_fp,
        domain_view_v1_fingerprint=view_v1.content_fingerprint,
        domain_view_v2_fingerprint=promoted["new_fingerprint"],
        effect=effect,
    )
    write_json(OUT_EXPERIENCE / "application_test_plan.json", plan)

    cache_v2 = Path(tempfile.mkdtemp(prefix="prem3-dv-v2-"))
    _bind_gcs_registry(cache_v2)
    probe_v2: dict[str, Any] | None = None
    last_error: MelError | None = None
    for _attempt in range(3):
        probe_v2 = _probe_cloud_run()
        assert_frozen_runtime(probe_v2)
        if probe_v2["revision"] != probe_v1["revision"]:
            raise MelError("C-v2 Cloud Run revision diverged from the frozen C-v1 revision")
        try:
            assert_domain_view_control(
                probe_v2["domain_view"],
                version=promoted["new_version"],
                fingerprint=promoted["new_fingerprint"],
                promoted_lesson_count=1,
            )
            last_error = None
            break
        except MelError as exc:
            last_error = exc
            time.sleep(5)
    if last_error is not None or probe_v2 is None:
        raise last_error or MelError("Cloud Run DOMAIN_VIEW v2 probe failed")
    dv_v2 = probe_v2["domain_view"]

    c_v2 = run_intelligence_assignment(
        "C", repo=repo, run_id="dataset-c-v2-cloud-00013", runtime_revision=FROZEN_REVISION
    )
    sealed_after = json.loads((DATASET_C_DIR / "package_manifest.json").read_text(encoding="utf-8"))
    if sealed_after["package_fingerprint"] != SEALED_PACKAGE_FINGERPRINT:
        raise MelError("Dataset C sealed package fingerprint changed after C-v2")
    if c_v2["package_fingerprint"] != c_v1["package_fingerprint"]:
        raise MelError("C-v2 package fingerprint diverged from C-v1")
    if c_v2["model_input_fingerprint"] != c_v1["model_input_fingerprint"]:
        raise MelError("C-v2 model-input fingerprint diverged from C-v1")

    declared = measure_declared_effect(c_v1["behavior"], c_v2["behavior"], effect)
    comparison = dump_behavior_comparison(c_v1["behavior"], c_v2["behavior"], effect)
    comparison["declared_measurement"] = declared
    write_json(OUT_EVAL / "cloud_holdout_behavior_diff.json", comparison)
    write_json(
        OUT_EVAL / "dataset_c_v2_cloud_application.json",
        {
            "run_id": c_v2["run_id"],
            "cloud_run": True,
            "cloud_run_revision": FROZEN_REVISION,
            "assignment_mode": "INTELLIGENCE_EVALUATION",
            "domain_view_version": c_v2["domain_view_version"],
            "domain_view_fingerprint": c_v2["domain_view_fingerprint"],
            "dataset_fingerprint": c_v2["package_fingerprint"],
            "model_input_fingerprint": c_v2["model_input_fingerprint"],
            "behavior": c_v2["behavior"],
            "behavior_fingerprint": fingerprint_payload(c_v2["behavior"]),
        },
    )

    v2 = load_active_view()
    retrieval = retrieve_routing_hints(
        v2,
        observed_conditions=list(candidate.applicability_conditions),
        fallback_conditions=list(candidate.applicability_conditions),
    )
    holdout = evaluate_holdout_application(
        baseline_run=c_v1,
        learned_run=c_v2,
        lesson={"lesson_id": candidate.candidate_lesson_id},
        application_plan=plan,
        promotion=promoted["receipt"],
        retrieval=retrieval,
        retrieved_claims=retrieval.get("retrieved_claims") or [],
        regression_pass=regression.passed,
        controlled_comparison=(
            c_v1["package_fingerprint"] == c_v2["package_fingerprint"]
            and c_v1["model_input_fingerprint"] == c_v2["model_input_fingerprint"]
            and probe_v1["revision"] == probe_v2["revision"]
        ),
    )
    ledger_record_application(ledger, holdout["application"])
    write_json(
        OUT_EXPERIENCE / "experience_applied_receipt.json",
        holdout["application"].model_dump(mode="json"),
    )
    write_json(OUT_EVAL / "cloud_invariant_report.json", holdout["comparison"])
    write_json(
        OUT_EVAL / "cloud_negative_control_report.json",
        {
            "negative_controls_total": holdout["negative_controls_total"],
            "negative_controls_passed": holdout["negative_controls_passed"],
            "negative_controls_failed": holdout["negative_controls_failed"],
        },
    )
    manifest = build_experiment_manifest(
        baseline_git_sha=_git_sha(),
        domain_view=view_v1,
        dataset_a_fingerprint=dataset_a_fp,
        dataset_b_fingerprint=dataset_b_fp,
        dataset_c_fingerprint=dataset_c_fp,
        cloud_runtime_revision=FROZEN_REVISION,
        cloud_image_digest=FROZEN_IMAGE_DIGEST,
    )
    manifest["experiment_id"] = CLOUD_EXPERIMENT_ID
    manifest["local_experiment_id"] = EXPERIMENT_ID
    manifest["cloud_a_run_id"] = CLOUD_A_RUN_ID
    manifest["cloud_b_run_id"] = CLOUD_B_RUN_ID
    write_json(OUT_EXPERIENCE / "cloud_learning_experiment_manifest.json", manifest)
    status = {
        "status": (
            "EXPERIENCE_APPLIED" if holdout["applied"] else holdout["application"].receipt_type
        ),
        "experience_learned": True,
        "experience_applied": holdout["applied"],
        "gates": holdout["gates"],
        "frozen_revision": FROZEN_REVISION,
        "image_digest": FROZEN_IMAGE_DIGEST,
        "probe_v1": dv_v1,
        "probe_v2": dv_v2,
        "declared_effect_succeeded": declared["effect_succeeded"],
        "undeclared_behavior_field_changes": declared["undeclared_behavior_field_changes"],
        "inference_used": False,
    }
    write_json(OUT_EXPERIENCE / "cloud_learning_status.json", status)
    write_json(OUT_EVAL / "cloud_first_learning_status.json", status)
    print(json.dumps(status, indent=2, sort_keys=True))
    print(status["status"])
    return 0 if holdout["applied"] and declared["effect_succeeded"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
