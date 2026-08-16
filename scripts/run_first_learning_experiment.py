"""Run the first controlled PreM3 experiential-learning experiment locally.

Writes machine-readable artifacts under experience/ and evaluation/.
Does not modify frontend/. Does not rewrite promoted_lessons.yaml by hand.
"""

from __future__ import annotations

import json
import os
import subprocess

from app.core.run_repository import LocalFilesystemRunRepository, fingerprint_package_dir
from app.domain.intelligence.builder import load_current_domain_view
from app.mel.assignment import run_intelligence_assignment
from app.mel.behavior import ExpectedBehaviorEffect, semantic_question_routing_effect
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
from app.mel.promote import load_active_view
from app.mel.routing_apply import retrieve_routing_hints
from app.synthetic.paths import DATASET_A_DIR, DATASET_B_DIR, DATASET_C_DIR, REPO_ROOT

OUT_EXPERIENCE = REPO_ROOT / "experience"
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


def main() -> int:
    os.environ.pop("MODELREADY_DOMAIN_VIEW_REGISTRY_DIR", None)
    view_v1 = load_current_domain_view()
    if view_v1 is None:
        raise SystemExit("DOMAIN_VIEW v1 is missing")
    dataset_a_fp, _ = fingerprint_package_dir(DATASET_A_DIR / "raw")
    dataset_b_fp, _ = fingerprint_package_dir(DATASET_B_DIR / "raw")
    dataset_c_fp, _ = fingerprint_package_dir(DATASET_C_DIR / "raw")
    manifest = build_experiment_manifest(
        baseline_git_sha=_git_sha(),
        domain_view=view_v1,
        dataset_a_fingerprint=dataset_a_fp,
        dataset_b_fingerprint=dataset_b_fp,
        dataset_c_fingerprint=dataset_c_fp,
    )
    manifest_fp = write_json(OUT_EXPERIENCE / "first_learning_experiment_manifest.json", manifest)
    manifest["manifest_fingerprint"] = manifest_fp
    write_json(OUT_EXPERIENCE / "first_learning_experiment_manifest.json", manifest)

    work = REPO_ROOT / "artifacts" / "first_learning_experiment"
    repo = LocalFilesystemRunRepository(
        root=work / "repo", raw_bucket="raw", artifact_bucket="artifacts"
    )
    ledger = work / "ledger"
    registry = work / "registry"

    c_v1 = run_intelligence_assignment("C", repo=repo, run_id="dataset-c-v1")
    write_json(
        OUT_EVAL / "dataset_c_v1_cloud_baseline.json",
        {
            "run_id": c_v1["run_id"],
            "cloud_run": False,
            "dataset_fingerprint": c_v1["package_fingerprint"],
            "model_input_fingerprint": c_v1["model_input_fingerprint"],
            "domain_view_version": c_v1["domain_view_version"],
            "domain_view_fingerprint": c_v1["domain_view_fingerprint"],
            "behavior": c_v1["behavior"],
            "behavior_fingerprint": fingerprint_payload(c_v1["behavior"]),
            "terminal_state": c_v1["terminal_outcome"],
            "evaluation_only": True,
        },
    )

    a_run = run_intelligence_assignment("A", repo=repo, run_id="dataset-a")
    b_run = run_intelligence_assignment("B", repo=repo, run_id="dataset-b")
    write_json(
        OUT_EXPERIENCE / "experience_episode_a.json",
        a_run["episode"].model_dump(mode="json"),
    )
    write_json(
        OUT_EXPERIENCE / "experience_reflection_a.json",
        a_run["reflection"].model_dump(mode="json"),
    )
    write_json(
        OUT_EXPERIENCE / "experience_episode_b.json",
        b_run["episode"].model_dump(mode="json"),
    )
    write_json(
        OUT_EXPERIENCE / "experience_reflection_b.json",
        b_run["reflection"].model_dump(mode="json"),
    )

    outcome = evaluate_ab_candidates(
        episode_a=a_run["episode"],
        reflection_a=a_run["reflection"],
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
            OUT_EXPERIENCE / "first_learning_status.json",
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
        experiment_id=EXPERIMENT_ID,
        lesson_id=candidate.candidate_lesson_id,
        dataset_c_fingerprint=dataset_c_fp,
        domain_view_v1_fingerprint=view_v1.content_fingerprint,
        domain_view_v2_fingerprint=promoted["new_fingerprint"],
        effect=effect,
    )
    write_json(OUT_EXPERIENCE / "application_test_plan.json", plan)

    os.environ["MODELREADY_DOMAIN_VIEW_REGISTRY_DIR"] = str(registry)
    c_v2 = run_intelligence_assignment("C", repo=repo, run_id="dataset-c-v2")
    write_json(
        OUT_EVAL / "dataset_c_v2_application_run.json",
        {
            "run_id": c_v2["run_id"],
            "domain_view_version": c_v2["domain_view_version"],
            "domain_view_fingerprint": c_v2["domain_view_fingerprint"],
            "dataset_fingerprint": c_v2["package_fingerprint"],
            "model_input_fingerprint": c_v2["model_input_fingerprint"],
            "behavior": c_v2["behavior"],
            "behavior_fingerprint": fingerprint_payload(c_v2["behavior"]),
        },
    )
    comparison = dump_behavior_comparison(c_v1["behavior"], c_v2["behavior"], effect)
    write_json(OUT_EVAL / "holdout_behavior_diff.json", comparison)

    v2 = load_active_view(registry)
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
        ),
    )
    ledger_record_application(ledger, holdout["application"])
    write_json(
        OUT_EXPERIENCE / "experience_applied_receipt.json",
        holdout["application"].model_dump(mode="json"),
    )
    write_json(
        OUT_EVAL / "invariant_report.json",
        holdout["comparison"],
    )
    write_json(
        OUT_EVAL / "negative_control_report.json",
        {
            "negative_controls_total": holdout["negative_controls_total"],
            "negative_controls_passed": holdout["negative_controls_passed"],
            "negative_controls_failed": holdout["negative_controls_failed"],
        },
    )
    write_json(
        OUT_EXPERIENCE / "first_learning_status.json",
        {
            "status": (
                "EXPERIENCE_APPLIED" if holdout["applied"] else holdout["application"].receipt_type
            ),
            "experience_learned": True,
            "experience_applied": holdout["applied"],
            "gates": holdout["gates"],
        },
    )
    print(json.dumps(holdout["gates"], indent=2))
    print("EXPERIENCE_APPLIED" if holdout["applied"] else holdout["application"].receipt_type)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
