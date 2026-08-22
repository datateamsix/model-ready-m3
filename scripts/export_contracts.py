"""Export deterministic JSON Schema artifacts for public PreM3 backend contracts."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.tools.schema_export import (
    DEFAULT_SCHEMA_DIR,
    check_schema_artifacts,
    sha256_bytes,
    write_schema_artifacts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare generated schemas with committed artifacts; do not write.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_SCHEMA_DIR,
        help="Output directory for generated schema artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dest = args.out
    if args.check:
        errors = check_schema_artifacts(dest)
        if errors:
            print("Contract schema drift detected:")
            for error in errors:
                print(f"  {error}")
            return 1
        print(f"Contract schemas match {dest}")
        return 0
    artifacts = write_schema_artifacts(dest)
    print(f"Wrote {len(artifacts)} contract artifacts to {dest}")
    for name in sorted(artifacts):
        print(f"  {name}  sha256={sha256_bytes(artifacts[name])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
