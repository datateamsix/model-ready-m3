"""Deterministic file inventory helpers."""

from __future__ import annotations

from pathlib import Path


def inventory_files(root: str | Path) -> list[dict[str, object]]:
    """Return a stable inventory of files beneath a local root.

    Cloud Storage adapters should normalize into the same contract rather than
    duplicating downstream logic.
    """
    base = Path(root)
    if not base.exists():
        raise FileNotFoundError(base)

    records: list[dict[str, object]] = []
    for path in sorted(p for p in base.rglob("*") if p.is_file()):
        stat = path.stat()
        records.append(
            {
                "path": str(path.relative_to(base)),
                "size_bytes": stat.st_size,
                "suffix": path.suffix.lower(),
            }
        )
    return records
