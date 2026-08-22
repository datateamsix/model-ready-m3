"""Export deterministic contracts/openapi.yaml from the live FastAPI app."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.service.openapi_export import (
    DEFAULT_OPENAPI_PATH,
    check_openapi,
    sha256_bytes,
    write_openapi,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare generated OpenAPI with the committed file; do not write.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OPENAPI_PATH,
        help="Output path for contracts/openapi.yaml.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.check:
        errors = check_openapi(args.out)
        if errors:
            print("OpenAPI drift detected:")
            for error in errors:
                print(f"  {error}")
            return 1
        print(f"OpenAPI matches {args.out}")
        return 0
    payload = write_openapi(args.out)
    print(f"Wrote {args.out}  sha256={sha256_bytes(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
