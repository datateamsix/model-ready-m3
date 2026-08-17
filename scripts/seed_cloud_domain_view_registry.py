"""Seed a cloud experiment DOMAIN_VIEW registry at bootstrap v1.0.0.

Uploads versioned data only. Does not rebuild the application image.
Does not activate the local experiment registry (v1.0.1).
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from app.config import settings
from app.mel.promote import (
    CLOUD_EXPERIMENT_ID,
    publish_registry,
    seed_bootstrap_registry,
)
from app.tools.artifacts import write_json_artifact

DEFAULT_PREFIX = (
    f"gs://{settings.artifact_bucket}/experiments/{CLOUD_EXPERIMENT_ID}/"
    "domain_view_registry/"
    if settings.artifact_bucket
    else None
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gs-prefix",
        default=DEFAULT_PREFIX,
        help="GCS prefix for domain_view_registry.json and versioned views.",
    )
    parser.add_argument(
        "--write-manifest",
        default=None,
        help="Optional local JSON proof path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.gs_prefix:
        raise SystemExit("MODELREADY_ARTIFACT_BUCKET / --gs-prefix is required.")
    root = Path(tempfile.mkdtemp(prefix="prem3-domain-view-seed-"))
    view = seed_bootstrap_registry(root)
    uploaded = publish_registry(root, args.gs_prefix)
    proof = {
        "status": "DOMAIN_VIEW_REGISTRY_SEEDED",
        "experiment_id": CLOUD_EXPERIMENT_ID,
        "gs_prefix": args.gs_prefix.rstrip("/") + "/",
        "active_version": view.domain_view_version,
        "active_fingerprint": view.content_fingerprint,
        "promoted_lesson_count": int(view.promoted_lesson_count),
        "uploaded": uploaded,
    }
    print("DOMAIN_VIEW_REGISTRY_SEEDED")
    print(proof["gs_prefix"])
    print(view.domain_view_version)
    print(view.content_fingerprint)
    if args.write_manifest:
        write_json_artifact(args.write_manifest, proof)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
