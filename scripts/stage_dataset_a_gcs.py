"""Stage the Dataset A runtime package to the configured raw GCS bucket.

Uses the developer's local identity. The Cloud Run runtime account must not
upload its own raw inputs. Regression truth is never uploaded.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from google.cloud import storage

from app.config import settings
from app.core.run_repository import DATASET_A_RUNTIME_FILES, FORBIDDEN_PACKAGE_NAMES
from app.synthetic.paths import DATASET_A_DIR
from app.tools.artifacts import sha256_file
from app.tools.provenance import dataset_fingerprint

DEFAULT_SOURCE = DATASET_A_DIR / "raw"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-id", default="dataset-a-v1")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--write-manifest", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    if not source.is_dir():
        raise SystemExit(f"Source package does not exist: {source}")
    truth_dir = source / "truth"
    if truth_dir.exists():
        raise SystemExit("Refusing to stage a package that contains truth/.")
    files = [path for path in source.iterdir() if path.is_file()]
    names = {path.name for path in files}
    forbidden = names & set(FORBIDDEN_PACKAGE_NAMES)
    if forbidden:
        raise SystemExit(f"Refusing to upload regression truth files: {sorted(forbidden)}")
    if "expected_model_ready_weekly.csv" in names:
        raise SystemExit("Refusing to upload expected_model_ready_weekly.csv.")
    missing = sorted(DATASET_A_RUNTIME_FILES - names)
    if missing:
        raise SystemExit(f"Source is missing required runtime files: {missing}")
    extra = sorted(names - DATASET_A_RUNTIME_FILES)
    upload_names = sorted(DATASET_A_RUNTIME_FILES)
    bucket_name = settings.raw_bucket
    if not bucket_name:
        raise SystemExit("MODELREADY_RAW_BUCKET is not configured.")
    prefix = (
        f"{settings.organization_id}/{settings.workspace_id}/"
        f"dataset-a/packages/{args.package_id}"
    )
    client = storage.Client(project=settings.project_id)
    bucket = client.bucket(bucket_name)
    hashes: dict[str, str] = {}
    for name in upload_names:
        path = source / name
        blob = bucket.blob(f"{prefix}/{name}")
        blob.upload_from_filename(str(path))
        hashes[name] = sha256_file(path)
    uri = f"gs://{bucket_name}/{prefix}/"
    manifest = {
        "status": "DATASET_A_STAGED",
        "package_uri": uri,
        "package_id": args.package_id,
        "file_count": len(upload_names),
        "files": upload_names,
        "ignored_extra_files": extra,
        "fingerprint": dataset_fingerprint(hashes),
        "truth_excluded": True,
    }
    print("DATASET_A_STAGED")
    print(uri)
    if args.write_manifest:
        args.write_manifest.parent.mkdir(parents=True, exist_ok=True)
        args.write_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
