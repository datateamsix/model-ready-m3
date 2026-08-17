"""Stage Dataset B and ask Cloud Run to initialize it.

Uses the same generic initialize path as other assignments. A FAIL because
Music Center filenames are missing is a regression.
"""

from __future__ import annotations

import json
import time

from google.cloud import storage

from app.config import settings
from app.core.run_repository import FORBIDDEN_PACKAGE_NAMES, fingerprint_package_dir
from app.synthetic.paths import DATASET_B_DIR, REPO_ROOT
from app.tools.artifacts import sha256_file
from scripts.run_cloud_dataset_a import (
    EXPECTED_APP,
    _identity_token,
    _json_request,
    _revision,
    _run_prompt,
    _service_url,
    _trajectory_from_events,
)

SOURCE = DATASET_B_DIR / "raw"
PACKAGE_ID = "dataset-b-cloud-20260817"
PROMPT = """
Initialize the supplied Stride & Field marketing package for Google Meridian.
Call initialize_dataset_run once with this package URI. Do not invent missing
source files. Do not convert unknown absence to zero. Stop after initialize
returns, whether it succeeds or fails. Do not fit the Meridian model.

Package:
{package_uri}
""".strip()


def stage_package() -> dict[str, str]:
    bucket_name = settings.raw_bucket
    if not bucket_name:
        raise SystemExit("MODELREADY_RAW_BUCKET is not configured.")
    files = [path for path in SOURCE.iterdir() if path.is_file()]
    names = {path.name for path in files}
    forbidden = names & set(FORBIDDEN_PACKAGE_NAMES)
    if forbidden:
        raise SystemExit(f"Refusing to upload regression truth files: {sorted(forbidden)}")
    prefix = f"stride-and-field/mmm-demo/dataset-b/packages/{PACKAGE_ID}"
    client = storage.Client(project=settings.project_id)
    bucket = client.bucket(bucket_name)
    hashes: dict[str, str] = {}
    for path in sorted(files, key=lambda item: item.name):
        blob = bucket.blob(f"{prefix}/{path.name}")
        blob.upload_from_filename(str(path))
        hashes[path.name] = sha256_file(path)
    fingerprint, _ = fingerprint_package_dir(SOURCE)
    return {
        "package_uri": f"gs://{bucket_name}/{prefix}/",
        "fingerprint": fingerprint,
        "file_count": str(len(hashes)),
        "files": ",".join(sorted(hashes)),
    }


def main() -> int:
    staged = stage_package()
    app_url = _service_url().rstrip("/")
    token = _identity_token()
    session_id = f"cloud_dataset_b_{int(time.time())}"
    session = _json_request(
        "POST",
        f"{app_url}/apps/{EXPECTED_APP}/users/cloud_taskmaster_user/sessions/{session_id}",
        token,
        body={},
    )
    if not isinstance(session, dict) or session.get("id") != session_id:
        raise SystemExit(f"Failed to create ADK session: {session}")
    text, events = _run_prompt(
        app_url,
        token,
        PROMPT.format(package_uri=staged["package_uri"]),
        session_id,
        timeout=300,
    )
    trajectory = _trajectory_from_events(events)
    init_events = [event for event in trajectory if event.get("tool") == "initialize_dataset_run"]
    payload = {
        "cloud_run": True,
        "revision": _revision(),
        "package_uri": staged["package_uri"],
        "dataset_fingerprint": staged["fingerprint"],
        "files": staged["files"].split(","),
        "file_count": int(staged["file_count"]),
        "session_id": session_id,
        "initialize_events": init_events,
        "agent_text_preview": " ".join(text.split())[:800],
    }
    out = REPO_ROOT / "evaluation" / "dataset_b_cloud_initialize_attempt.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(out), "initialize_count": len(init_events)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
