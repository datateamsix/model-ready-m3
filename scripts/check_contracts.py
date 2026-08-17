"""CI-safe contract schema drift check. Never rewrites committed files."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.tools.schema_export import DEFAULT_SCHEMA_DIR, check_schema_artifacts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_SCHEMA_DIR,
        help="Committed schema directory to compare against generated output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = check_schema_artifacts(args.dir)
    if errors:
        print("Contract schema drift detected:")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"Contract schemas match {args.dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
