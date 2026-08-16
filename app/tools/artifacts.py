"""Artifact hashing and serialization helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_canonical_text_file(path: str | Path) -> str:
    """SHA-256 of file bytes with CRLF normalized to LF.

    Sealed dataset fingerprints were computed on LF bytes. Windows
    autocrlf working trees must compare against that canonical form.
    """
    payload = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(payload).hexdigest()


def write_json_artifact(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    return target
