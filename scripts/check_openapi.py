"""CI-safe OpenAPI drift check. Never rewrites committed files."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.service.openapi_export import DEFAULT_OPENAPI_PATH, check_openapi


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_OPENAPI_PATH,
        help="Committed OpenAPI document to compare.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = check_openapi(args.path)
    if errors:
        print("OpenAPI drift detected:")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"OpenAPI matches {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
