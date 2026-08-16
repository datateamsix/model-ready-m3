"""PreM3 rebrand inventory/audit scanner. Not a runtime dependency."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "artifacts",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
}
SKIP_FILES = {
    "scripts/_extract_eda_review.py",
    "scripts/_prem3_rebrand_scan.py",
    "scripts/prem3_rebrand_audit.py",
}
PATTERNS = [
    ("ModelReady", re.compile(r"ModelReady")),
    ("M3 Agent", re.compile(r"(?<!Pre)M3 [Aa]gent")),
    ("Map. Mend. Model-Ready.", re.compile(r"Map\. Mend\. Model-Ready\.")),
    ("ModelReady Experience Loop", re.compile(r"ModelReady Experience Loop")),
    ("M3 Learning Receipt", re.compile(r"(?<!Pre)M3 Learning Receipt")),
    ("model-ready-m3", re.compile(r"model-ready-m3")),
]
EXTS = {".md", ".py", ".toml", ".yml", ".yaml", ".json", ".txt", ".svg"}


def classify(row: dict[str, object]) -> str:
    path = str(row["file"])
    term = str(row["term"])
    text = str(row["text"])
    if term == "model-ready-m3":
        return "C"
    if "ModelReadyManifest" in text or "ModelReadyError" in text or "class ModelReady" in text:
        return "C"
    machine_tokens = (
        "modelready-m3",
        "modelready_m3",
        "modelready_ops",
        "modelready_models",
        "modelready_experience",
        "MODELREADY_",
        "M3_AGENT_NAME",
        "M3_GEMINI",
        "M3_RUNTIME",
    )
    if any(token in text for token in machine_tokens):
        return "C"
    if path.endswith(".svg") or "diagrams/modelready" in path:
        return "G"
    if path.endswith("01_PRODUCT_SPEC_MODELREADY.md"):
        return "G"
    if path.startswith("tests/"):
        return "E"
    if path in {
        "docs/context/08_DECISION_LOG.md",
        "docs/brand/PREM3_BRAND_AND_NAMING.md",
        "docs/context/SOURCE_UPDATE_MANIFEST.md",
        "docs/context/03_EXPERIENTIAL_LEARNING_FRAMEWORK.md",
        "docs/context/01_PRODUCT_SPEC_PREM3.md",
    }:
        return "D"
    if path.endswith((".py", ".toml", ".yml", ".yaml")):
        lowered = text.lower()
        if any(
            token in lowered
            for token in ("you are m3", "rerun modelready", "m3 agent", "modelready's")
        ):
            return "A"
        return "C"
    if path.endswith(".md"):
        if "working name ModelReady" in text or "deprecated" in text.lower():
            return "D"
        return "A"
    return "F"


def scan() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file() or path.suffix.lower() not in EXTS:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel in SKIP_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for name, pattern in PATTERNS:
            for line_no, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    rows.append(
                        {
                            "file": rel,
                            "line": line_no,
                            "term": name,
                            "text": line.strip()[:240],
                        }
                    )
    for row in rows:
        row["classification"] = classify(row)
    by_term: dict[str, int] = defaultdict(int)
    by_class: dict[str, int] = defaultdict(int)
    by_file: dict[str, int] = defaultdict(int)
    for row in rows:
        by_term[str(row["term"])] += 1
        by_class[str(row["classification"])] += 1
        by_file[str(row["file"])] += 1
    return {
        "total_occurrences": len(rows),
        "counts_by_term": dict(by_term),
        "counts_by_classification": dict(by_class),
        "counts_by_file": dict(sorted(by_file.items())),
        "classification_legend": {
            "A": "CURRENT USER-FACING PRODUCT NAME — should be gone",
            "B": "CURRENT DOCUMENTATION / ARCHITECTURE",
            "C": "STABLE MACHINE IDENTIFIER",
            "D": "HISTORICAL EVIDENCE / MIGRATION NOTE",
            "E": "TEST/FIXTURE EXPECTATION",
            "F": "OBSOLETE COPY",
            "G": "FILE NAME / ASSET",
        },
        "occurrences": rows,
    }


def main() -> None:
    destination = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else ROOT / "artifacts" / "deployment" / "prem3_rebrand_audit.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = scan()
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(destination),
                "total": payload["total_occurrences"],
                "by_term": payload["counts_by_term"],
                "by_class": payload["counts_by_classification"],
                "files": len(payload["counts_by_file"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
