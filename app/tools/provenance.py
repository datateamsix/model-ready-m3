"""Automatic transformation provenance. Tools emit evidence; Gemini does not."""

from __future__ import annotations

import hashlib
import json
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.contracts import TransformationEvidence, utc_now
from app.tools.artifacts import sha256_file, write_json_artifact

_current_run: ContextVar[ProvenanceSink | None] = ContextVar("m3_provenance_sink", default=None)


@dataclass(slots=True)
class ProvenanceSink:
    run_id: str
    artifact_dir: Path

    @property
    def manifest_path(self) -> Path:
        return self.artifact_dir / "transformation_manifest.json"

    @property
    def provenance_path(self) -> Path:
        return self.artifact_dir / "provenance.json"


def bind_provenance(run_id: str, artifact_dir: str | Path) -> ProvenanceSink:
    sink = ProvenanceSink(run_id=run_id, artifact_dir=Path(artifact_dir))
    sink.artifact_dir.mkdir(parents=True, exist_ok=True)
    _current_run.set(sink)
    return sink


def current_provenance() -> ProvenanceSink | None:
    return _current_run.get()


def record_transform(
    *,
    tool: str,
    rule_id: str,
    source_uri: str,
    output_uri: str,
    input_rows: int,
    output_rows: int,
    parameters: dict[str, Any],
    reason: str,
    run_id: str | None = None,
) -> dict[str, Any]:
    sink = current_provenance()
    resolved_run_id = run_id or (sink.run_id if sink else "unbound")
    source_path = Path(source_uri)
    output_path = Path(output_uri)
    evidence = TransformationEvidence(
        action_id=f"act_{uuid4().hex[:12]}",
        run_id=resolved_run_id,
        rule_id=rule_id,
        tool=tool,
        source_uri=str(source_path),
        output_uri=str(output_path),
        source_sha256=sha256_file(source_path) if source_path.is_file() else "",
        output_sha256=sha256_file(output_path) if output_path.is_file() else "",
        input_rows=input_rows,
        output_rows=output_rows,
        parameters=parameters,
        reason=reason,
        status="APPLIED",
        timestamp=utc_now(),
    )
    payload = evidence.model_dump(mode="json")
    if sink is not None:
        _append_json_list(sink.manifest_path, payload, key="transforms")
        _append_json_list(sink.provenance_path, payload, key="records")
    return payload


def dataset_fingerprint(file_hashes: dict[str, str]) -> str:
    payload = json.dumps(file_hashes, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _append_json_list(path: Path, item: dict[str, Any], *, key: str) -> None:
    if path.exists():
        document = json.loads(path.read_text(encoding="utf-8"))
    else:
        document = {"run_id": item.get("run_id"), key: []}
    document.setdefault(key, []).append(item)
    write_json_artifact(path, document)
