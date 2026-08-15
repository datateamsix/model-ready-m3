"""Validate ModelReady pre-cloud prerequisites. Does not deploy Cloud Run."""

from __future__ import annotations

import argparse

from app.tools.precloud import all_required_passed, collect_checks, format_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Also verify Application Default Credentials. Not required for CI.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checks = collect_checks(live=args.live)
    print(format_report(checks))
    return 0 if all_required_passed(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
