"""Generic PreM3 assignment runner. Dataset A/B/C use the same coordinator.

Cloud mode obtains a short-lived identity token and does not persist tokens.
Dataset A golden proof remains available via scripts/run_cloud_dataset_a.py.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from google.cloud import storage

from app.config import settings
from app.core.run_coordinator import RunCoordinator
from app.core.run_repository import FORBIDDEN_PACKAGE_NAMES, fingerprint_package_dir
from app.core.source_inventory import EXPECTED_CONTRACT_FILENAMES
from app.mel.assignment import DATASET_SPECS
from app.mel.models import DatasetRole
from app.response.run_bundle import (
    build_run_presentation_bundle,
    load_run_presentation_bundle,
)
from app.tools.artifacts import sha256_file, write_json_artifact
from scripts.run_cloud_dataset_a import (
    EXPECTED_APP,
    _discover_run_id,
    _identity_token,
    _json_request,
    _load_gcs_json,
    _revision,
    _run_prompt,
    _service_url,
    _trajectory_from_events,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

DATASET_BY_ID = {
    spec["dataset_id"]: {**spec, "key": key} for key, spec in DATASET_SPECS.items()
}

TASK_PROMPT = """
Prepare the supplied marketing dataset for Google Meridian. Inspect the package
and its readiness issues. You may autonomously execute only deterministic
AUTO_SAFE remediation. Stop rather than guessing if approval or missing evidence
is required. Publish only after deterministic readiness passes. After the
BigQuery model input is confirmed, run PreM3 pre-EDA diagnostics, then official
Meridian pre-modeling EDA, interpret the structured findings, and report
MODEL_READY only if the evidence-backed final gate passes. Do not fit the
Meridian model.

Package:
{package_uri}

Assignment:
dataset_id={dataset_id}
dataset_role={dataset_role}
qualification_mode={qualification_mode}
{holdout_clause}
""".strip()

HOLDOUT_CLAUSE = """
This assignment is SEALED_HOLDOUT. Qualification mode is HOLDOUT_QUALIFICATION_ONLY.
Do not extract CandidateLesson. Do not promote. Do not claim EXPERIENCE_APPLIED.
Do not change DOMAIN_VIEW.
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-id",
        required=True,
        choices=sorted(DATASET_BY_ID),
        help="Canonical assignment id from the dataset catalog.",
    )
    parser.add_argument("--package-uri", default=None)
    parser.add_argument("--local", action="store_true", help="Run the coordinator locally.")
    parser.add_argument(
        "--stage",
        action="store_true",
        help="Upload the assignment raw package to GCS before invoking cloud.",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument(
        "--app-url",
        default=None,
        help="Cloud Run URL. Defaults to the service URL of modelready-m3.",
    )
    parser.add_argument(
        "--qualification-mode",
        default=None,
        help="Optional run mode. Use HOLDOUT_QUALIFICATION_ONLY for Dataset C.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    spec = DATASET_BY_ID[args.dataset_id]
    role = spec["role"]
    qualification_mode = args.qualification_mode
    if role is DatasetRole.SEALED_HOLDOUT and not qualification_mode:
        qualification_mode = "HOLDOUT_QUALIFICATION_ONLY"
    if args.local:
        return _run_local(spec, args.output_dir, qualification_mode)
    package_uri = args.package_uri
    if args.stage or not package_uri:
        staged = _stage_package(spec)
        package_uri = staged["package_uri"]
        print(json.dumps({"staged": staged}, indent=2))
    if not str(package_uri).startswith("gs://"):
        raise SystemExit("Cloud mode requires a gs:// package-uri or --stage.")
    return _run_cloud(spec, package_uri, qualification_mode, args)


def _run_local(spec: dict, output_dir: Path | None, qualification_mode: str | None) -> int:
    raw = Path(spec["root"]) / "raw"
    artifacts = output_dir or (REPO_ROOT / "artifacts" / "local" / spec["dataset_id"])
    coordinator = RunCoordinator(
        raw,
        artifacts,
        dataset_id=spec["dataset_id"],
        dataset_role=spec["role"].value,
        qualification_mode=qualification_mode,
        business_name=spec["business"],
    )
    summary = coordinator.run_local()
    bundle = load_run_presentation_bundle(coordinator.workspace)
    write_json_artifact(coordinator.workspace / "run_presentation_bundle.json", bundle)
    print(
        json.dumps(
            {
                "status": "LOCAL_RUN_COMPLETE",
                "dataset_id": spec["dataset_id"],
                "dataset_role": spec["role"].value,
                "qualification_mode": qualification_mode,
                "final_state": summary.get("final_state"),
                "detected_issue_count": summary.get("detected_issue_count"),
                "resolved_issue_count": summary.get("resolved_issue_count"),
                "open_issue_count": summary.get("open_issue_count"),
                "workspace": str(coordinator.workspace),
            },
            indent=2,
        )
    )
    return 0


def _stage_package(spec: dict[str, Any]) -> dict[str, str]:
    bucket_name = settings.raw_bucket
    if not bucket_name:
        raise SystemExit("MODELREADY_RAW_BUCKET is not configured.")
    source = Path(spec["root"]) / "raw"
    files = [
        path
        for path in source.iterdir()
        if path.is_file()
        and path.name not in FORBIDDEN_PACKAGE_NAMES
        and path.name not in EXPECTED_CONTRACT_FILENAMES
    ]
    prefix = f"{spec['organization_id']}/{spec['dataset_id']}/packages/v1"
    client = storage.Client(project=settings.project_id)
    bucket = client.bucket(bucket_name)
    hashes: dict[str, str] = {}
    for path in sorted(files, key=lambda item: item.name):
        blob = bucket.blob(f"{prefix}/{path.name}")
        blob.upload_from_filename(str(path))
        hashes[path.name] = sha256_file(path)
    fingerprint, _ = fingerprint_package_dir(source)
    return {
        "package_uri": f"gs://{bucket_name}/{prefix}/",
        "fingerprint": fingerprint,
        "file_count": str(len(hashes)),
        "files": ",".join(sorted(hashes)),
    }


def _run_cloud(
    spec: dict[str, Any],
    package_uri: str,
    qualification_mode: str | None,
    args: argparse.Namespace,
) -> int:
    role = spec["role"]
    holdout_clause = HOLDOUT_CLAUSE if role is DatasetRole.SEALED_HOLDOUT else ""
    prompt = TASK_PROMPT.format(
        package_uri=package_uri,
        dataset_id=spec["dataset_id"],
        dataset_role=role.value if isinstance(role, DatasetRole) else role,
        qualification_mode=qualification_mode or "",
        holdout_clause=holdout_clause,
    )
    app_url = (args.app_url or _service_url()).rstrip("/")
    token = _identity_token()
    session_id = args.session_id or f"cloud_{spec['dataset_id']}_{int(time.time())}"
    session = _json_request(
        "POST",
        f"{app_url}/apps/{EXPECTED_APP}/users/cloud_taskmaster_user/sessions/{session_id}",
        token,
        body={},
    )
    if not isinstance(session, dict) or session.get("id") != session_id:
        raise SystemExit(f"Failed to create ADK session: {session}")
    text, events = _run_prompt(app_url, token, prompt, session_id, timeout=args.timeout)
    trajectory = _trajectory_from_events(events)
    run_id = _discover_run_id(trajectory, text)
    summary = None
    inventory = None
    issues_doc = None
    confirmation = None
    eda = None
    publish = None
    if run_id:
        prefix = (
            f"gs://{settings.artifact_bucket}/{settings.organization_id}/"
            f"{settings.workspace_id}/runs/{run_id}/"
        )
        summary = _load_gcs_json(f"{prefix}run_summary.json")
        inventory = _load_gcs_json(f"{prefix}source_inventory_receipt.json")
        issues_doc = _load_gcs_json(f"{prefix}issues.json")
        confirmation = _load_gcs_json(f"{prefix}model_ready_confirmation_receipt.json")
        eda = _load_gcs_json(f"{prefix}eda/meridian_eda_receipt.json")
        publish = _load_gcs_json(f"{prefix}publish_receipt.json")
        bundle = build_run_presentation_bundle(
            summary=summary,
            issues=(issues_doc or {}).get("issues") or [],
            source_inventory=inventory,
            publish=publish,
            confirmation=confirmation,
            eda=eda,
        )
        demo_dir = REPO_ROOT / "artifacts" / "demo"
        demo_dir.mkdir(parents=True, exist_ok=True)
        write_json_artifact(demo_dir / f"{spec['dataset_id']}_cloud_run_bundle.json", bundle)
        write_json_artifact(
            REPO_ROOT / "evaluation" / f"{spec['dataset_id']}_cloud_run_bundle.json",
            bundle,
        )
    payload = {
        "status": "CLOUD_RUN_COMPLETE" if run_id else "CLOUD_RUN_INCOMPLETE",
        "dataset_id": spec["dataset_id"],
        "dataset_role": role.value if isinstance(role, DatasetRole) else role,
        "qualification_mode": qualification_mode,
        "revision": _revision(),
        "session_id": session_id,
        "run_id": run_id,
        "package_uri": package_uri,
        "final_state": (summary or {}).get("final_state"),
        "detected_issue_count": (summary or {}).get("detected_issue_count"),
        "resolved_issue_count": (summary or {}).get("resolved_issue_count"),
        "open_issue_count": (summary or {}).get("open_issue_count"),
        "providers": (inventory or {}).get("providers"),
        "missing_required_sources": (inventory or {}).get("missing_required_sources"),
        "confirmation_status": (confirmation or {}).get("status"),
        "publish_parity": (publish or {}).get("parity_status"),
        "eda_status": (eda or {}).get("status"),
        "agent_text_preview": " ".join(text.split())[:800],
        "tools": [event.get("tool") for event in trajectory if event.get("tool")],
    }
    out = REPO_ROOT / "evaluation" / f"{spec['dataset_id']}_cloud_qualification.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"Wrote {out}")
    print("Frozen Dataset A golden scorecard remains scripts/run_cloud_dataset_a.py.")
    return 0 if run_id else 1


if __name__ == "__main__":
    sys.exit(main())
