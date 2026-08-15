"""Run the Dataset A golden slice locally.

By default this executes through MODEL_READY including BigQuery publish/parity.
Pass --local-only to stop after deterministic readiness (no GCP writes).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.run_coordinator import RunCoordinator

DEFAULT_RAW = Path("tests/fixtures/music_center/dataset_a/raw")
DEFAULT_ARTIFACTS = Path("artifacts")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--local-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    coordinator = RunCoordinator(args.raw, args.artifact_root, run_id=args.run_id)
    if args.local_only:
        result = coordinator.run_local()
    else:
        result = coordinator.run()
    print(
        json.dumps(
            {
                "status": result.get("status", coordinator.stage.value),
                "summary": coordinator.summary_path,
            },
            indent=2,
            default=str,
        )
    )
    gate = result.get("gate") if isinstance(result, dict) else None
    if gate and gate.get("status") == "MODEL_READY":
        print("MODEL_READY")
        print("[x] deterministic readiness passed")
        print("[x] BigQuery model artifact published")
        print("[x] publish parity passed")
        print("[x] Meridian input contract generated")
        print("[x] provenance complete")


if __name__ == "__main__":
    main()
