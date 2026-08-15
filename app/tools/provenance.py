"""Automatic transformation provenance. Tools emit evidence; Gemini does not."""

from __future__ import annotations

import hashlib
import json
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.contracts import SourceArtifactEvidence, TransformationEvidence, utc_now
from app.tools.artifacts import sha256_file, write_json_artifact

_current_run: ContextVar[ProvenanceSink | None] = ContextVar("m3_provenance_sink", default=None)

FRAME_SOURCE_ROLES = (
    "google_media",
    "meta_media",
    "kpi_revenue",
    "organic_media",
    "controls",
    "population",
    "model_intent",
)


def to_artifact_uri(path: str | Path) -> str:
    """URI-shaped identifier. Preserves gs://; local paths use posix separators."""
    return str(path).replace("\\", "/")


@dataclass(slots=True)
class ProvenanceSink:
    run_id: str
    artifact_dir: Path
    dataset_fingerprint: str | None = None

    @property
    def manifest_path(self) -> Path:
        return self.artifact_dir / "transformation_manifest.json"

    @property
    def provenance_path(self) -> Path:
        return self.artifact_dir / "provenance.json"


def bind_provenance(
    run_id: str,
    artifact_dir: str | Path,
    dataset_fingerprint: str | None = None,
) -> ProvenanceSink:
    sink = ProvenanceSink(
        run_id=run_id,
        artifact_dir=Path(artifact_dir),
        dataset_fingerprint=dataset_fingerprint,
    )
    sink.artifact_dir.mkdir(parents=True, exist_ok=True)
    _ensure_provenance_document(
        sink.provenance_path,
        run_id=run_id,
        dataset_fingerprint=dataset_fingerprint,
        key="records",
    )
    _ensure_provenance_document(
        sink.manifest_path,
        run_id=run_id,
        dataset_fingerprint=dataset_fingerprint,
        key="transforms",
    )
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
    sources: list[dict[str, str]] | None = None,
    source_role: str = "source",
) -> dict[str, Any]:
    sink = current_provenance()
    resolved_run_id = run_id or (sink.run_id if sink else "unbound")
    source_records = _build_sources(source_uri, sources, source_role)
    output_path = Path(output_uri)
    primary = (
        source_records[0]
        if source_records
        else SourceArtifactEvidence(role=source_role, uri="", sha256="")
    )
    evidence = TransformationEvidence(
        action_id=f"act_{uuid4().hex[:12]}",
        run_id=resolved_run_id,
        rule_id=rule_id,
        tool=tool,
        source_uri=primary.uri,
        output_uri=to_artifact_uri(output_path),
        source_sha256=primary.sha256,
        output_sha256=sha256_file(output_path) if output_path.is_file() else "",
        sources=source_records,
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


def _build_sources(
    source_uri: str,
    sources: list[dict[str, str]] | None,
    source_role: str,
) -> list[SourceArtifactEvidence]:
    if sources:
        records: list[SourceArtifactEvidence] = []
        for item in sources:
            uri = to_artifact_uri(item["uri"])
            digest = item.get("sha256") or ""
            path = Path(item["uri"])
            if not digest and path.is_file():
                digest = sha256_file(path)
            records.append(SourceArtifactEvidence(role=item["role"], uri=uri, sha256=digest))
        return records
    path = Path(source_uri)
    digest = sha256_file(path) if path.is_file() else ""
    return [SourceArtifactEvidence(role=source_role, uri=to_artifact_uri(path), sha256=digest)]


def _ensure_provenance_document(
    path: Path, *, run_id: str, dataset_fingerprint: str | None, key: str
) -> None:
    if path.exists():
        document = json.loads(path.read_text(encoding="utf-8"))
        document["run_id"] = run_id
        if dataset_fingerprint:
            document["dataset_fingerprint"] = dataset_fingerprint
        document.setdefault(key, [])
        write_json_artifact(path, document)
        return
    write_json_artifact(
        path,
        {"run_id": run_id, "dataset_fingerprint": dataset_fingerprint, key: []},
    )


def _append_json_list(path: Path, item: dict[str, Any], *, key: str) -> None:
    if path.exists():
        document = json.loads(path.read_text(encoding="utf-8"))
    else:
        document = {"run_id": item.get("run_id"), key: []}
    document.setdefault(key, []).append(item)
    write_json_artifact(path, document)
