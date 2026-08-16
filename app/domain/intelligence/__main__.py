"""Rebuild the committed DOMAIN_VIEW snapshot."""

from __future__ import annotations

import json

from app.domain.intelligence.builder import rebuild_and_persist, summarize_domain_view


def main() -> None:
    view = rebuild_and_persist()
    print(json.dumps(summarize_domain_view(view), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
