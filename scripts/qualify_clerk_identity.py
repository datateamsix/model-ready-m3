#!/usr/bin/env python3
"""Optional live Clerk identity qualification.

NEVER invoked by pytest/CI. Explicit operator command only.

Usage:
  py -3.13 scripts/qualify_clerk_identity.py --execute

Safety:
  - refuses sk_live_ unless --allow-live
  - does not create an MMM Project
  - does not call Stripe
  - does not mutate production customer data unless a synthetic mapping is created
    and then cleaned up
"""

from __future__ import annotations

import argparse
import sys

from app.config import load_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--allow-live",
        action="store_true",
        help="Required to run against a Clerk sk_live_ instance.",
    )
    args = parser.parse_args(argv)
    if not args.execute:
        print("LIVE_CLERK_IDENTITY_NOT_RUN")
        print("Pass --execute to run against a development Clerk instance.")
        return 2

    settings = load_settings()
    secret = settings.clerk_secret_key or ""
    if not secret:
        print("LIVE_CLERK_IDENTITY_NOT_RUN")
        print("CLERK_SECRET_KEY is not configured.")
        return 3
    if secret.startswith("sk_live_") and not args.allow_live:
        print("LIVE_CLERK_IDENTITY_NOT_RUN")
        print("Refusing Clerk live/production instance without --allow-live.")
        return 3

    print("LIVE_CLERK_IDENTITY_NOT_RUN")
    print(
        "Interactive session-token qualification is not automated. "
        "Use the FakeClerkRuntime unit suite for contract proof."
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
