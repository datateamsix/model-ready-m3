"""Rule catalog loading boundary.

The implementation deliberately separates rule metadata from executable Python
checks so rule IDs, sources, applicability, and remediation policy stay auditable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_rule_catalog(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if "version" not in payload or "rules" not in payload:
        raise ValueError("Rule catalog must contain version and rules")
    return payload
