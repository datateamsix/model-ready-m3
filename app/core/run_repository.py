"""Durable run persistence. Transformation logic stays in the coordinator."""

from __future__ import annotations

import json
import shutil
import tempfile
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.contracts import DurableRunState, Issue
from app.core.errors import AssignmentInitError, SafetyViolationError, ValidationBlockedError
from app.integrations.gcs import (
    blob_exists,
    download_file,
    download_prefix,
    join_gs,
    list_object_metadata,
    parse_gs_uri,
    upload_file,
)
from app.tools.artifacts import sha256_file, write_json_artifact
from app.tools.provenance import dataset_fingerprint

DATASET_A_RUNTIME_FILES = frozenset(
    {
        "google_ads_daily.csv",
        "meta_ads_weekly.csv",
        "ga4_weekly.csv",
        "shopify_weekly.csv",
        "controls_weekly.csv",
        "geo_population.csv",
        "model_intent.json",
    }
)
FORBIDDEN_PACKAGE_NAMES = ("expected_model_ready_weekly.csv",)
_SKIP_SYNC_ROOTS = frozenset({"raw", "package"})
_current_repo: ContextVar[RunRepository | None] = ContextVar("m3_run_repository", default=None)


class RunRepository:
    """Abstract durable store for run_state.json and run evidence."""

    def __init__(self, *, raw_bucket: str, artifact_bucket: str) -> None:
        self.raw_bucket = raw_bucket
        self.artifact_bucket = artifact_bucket

    def artifact_prefix(self, run_id: str) -> str:
        return join_gs(
            self.artifact_bucket,
            settings.organization_id,
            settings.workspace_id,
            "runs",
            run_id,
        )

    def run_state_uri(self, run_id: str) -> str:
        return f"{self.artifact_prefix(run_id).rstrip('/')}/run_state.json"

    def run_exists(self, run_id: str) -> bool:
        raise NotImplementedError

    def load_run(self, run_id: str) -> DurableRunState:
        raise NotImplementedError

    def save_run(self, state: DurableRunState) -> str:
        raise NotImplementedError

    def load_issues(self, run_id: str) -> list[Issue]:
        raise NotImplementedError

    def save_issues(self, run_id: str, issues: list[Issue]) -> str:
        raise NotImplementedError

    def load_json(self, run_id: str, relative: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def inventory_package(self, package_uri: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def download_package(self, package_uri: str, dest: str | Path) -> list[dict[str, Any]]:
        raise NotImplementedError

    def upload_workspace_file(self, run_id: str, local_path: str | Path, relative: str) -> str:
        raise NotImplementedError

    def sync_artifacts(self, run_id: str, workspace: str | Path) -> dict[str, str]:
        uris: dict[str, str] = {}
        root = Path(workspace)
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            top = relative.split("/", 1)[0]
            if top in _SKIP_SYNC_ROOTS:
                continue
            uris[relative] = self.upload_workspace_file(run_id, path, relative)
        return uris

    def restore_evidence(self, run_id: str, workspace: str | Path) -> Path:
        raise NotImplementedError


class LocalFilesystemRunRepository(RunRepository):
    """Fake GCS layout on local disk. Used by CI and resumability tests."""

    def __init__(self, *, root: str | Path, raw_bucket: str, artifact_bucket: str) -> None:
        super().__init__(raw_bucket=raw_bucket, artifact_bucket=artifact_bucket)
        self.root = Path(root)
        self.raw_root = self.root / "raw" / raw_bucket
        self.artifact_root = self.root / "artifacts" / artifact_bucket
        self.raw_root.mkdir(parents=True, exist_ok=True)
        self.artifact_root.mkdir(parents=True, exist_ok=True)

    def run_exists(self, run_id: str) -> bool:
        return self._artifact_path(run_id, "run_state.json").is_file()

    def load_run(self, run_id: str) -> DurableRunState:
        path = self._artifact_path(run_id, "run_state.json")
        if not path.is_file():
            raise ValidationBlockedError(f"Run {run_id} does not exist.")
        return DurableRunState.model_validate_json(path.read_text(encoding="utf-8"))

    def save_run(self, state: DurableRunState) -> str:
        path = self._artifact_path(state.run_id, "run_state.json")
        write_json_artifact(path, state.model_dump(mode="json"))
        return f"{state.artifact_prefix.rstrip('/')}/run_state.json"

    def load_issues(self, run_id: str) -> list[Issue]:
        path = self._artifact_path(run_id, "issues.json")
        if not path.is_file():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [Issue.model_validate(item) for item in payload.get("issues") or []]

    def save_issues(self, run_id: str, issues: list[Issue]) -> str:
        path = self._artifact_path(run_id, "issues.json")
        write_json_artifact(path, {"issues": [issue.model_dump(mode="json") for issue in issues]})
        return f"{self.artifact_prefix(run_id).rstrip('/')}/issues.json"

    def load_json(self, run_id: str, relative: str) -> dict[str, Any] | None:
        path = self._artifact_path(run_id, relative)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def inventory_package(self, package_uri: str) -> list[dict[str, Any]]:
        folder = self._local_for_uri(package_uri)
        if not folder.is_dir():
            raise ValidationBlockedError(f"Package does not exist: {package_uri}")
        records: list[dict[str, Any]] = []
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(folder).as_posix()
            records.append(
                {
                    "name": f"{_blob_from_uri(package_uri).rstrip('/')}/{relative}",
                    "relative": relative,
                    "generation": sha256_file(path),
                    "path": str(path),
                }
            )
        return records

    def download_package(self, package_uri: str, dest: str | Path) -> list[dict[str, Any]]:
        source = self._local_for_uri(package_uri)
        target = Path(dest)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        records: list[dict[str, Any]] = []
        for path in sorted(target.rglob("*")):
            if path.is_file():
                relative = path.relative_to(target).as_posix()
                records.append(
                    {
                        "name": f"{_blob_from_uri(package_uri).rstrip('/')}/{relative}",
                        "relative": relative,
                        "generation": sha256_file(path),
                        "path": str(path),
                    }
                )
        return records

    def upload_workspace_file(self, run_id: str, local_path: str | Path, relative: str) -> str:
        dest = self._artifact_path(run_id, relative)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest)
        return f"{self.artifact_prefix(run_id).rstrip('/')}/{relative}"

    def restore_evidence(self, run_id: str, workspace: str | Path) -> Path:
        dest = Path(workspace)
        dest.mkdir(parents=True, exist_ok=True)
        source = self._artifact_path(run_id, "")
        if not source.is_dir():
            raise ValidationBlockedError(f"Run {run_id} has no durable artifacts.")
        for path in source.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(source).as_posix()
            target = dest / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        return dest

    def _artifact_path(self, run_id: str, relative: str) -> Path:
        prefix = (
            Path(settings.organization_id) / settings.workspace_id / "runs" / run_id
        )
        return self.artifact_root / prefix / relative

    def _local_for_uri(self, uri: str) -> Path:
        bucket, blob = parse_gs_uri(uri)
        if bucket == self.raw_bucket:
            return self.raw_root / blob
        if bucket == self.artifact_bucket:
            return self.artifact_root / blob
        raise SafetyViolationError(f"URI bucket is not a configured ModelReady bucket: {bucket}")


class GcsRunRepository(RunRepository):
    """Artifact-bucket persistence used by Cloud Run."""

    def run_exists(self, run_id: str) -> bool:
        return blob_exists(self.run_state_uri(run_id))

    def load_run(self, run_id: str) -> DurableRunState:
        if not self.run_exists(run_id):
            raise ValidationBlockedError(f"Run {run_id} does not exist.")
        tmp = Path(tempfile.mkdtemp(prefix="m3-run-state-"))
        path = download_file(self.run_state_uri(run_id), tmp / "run_state.json")
        return DurableRunState.model_validate_json(path.read_text(encoding="utf-8"))

    def save_run(self, state: DurableRunState) -> str:
        tmp = Path(tempfile.mkdtemp(prefix="m3-run-save-"))
        path = tmp / "run_state.json"
        write_json_artifact(path, state.model_dump(mode="json"))
        uri = f"{state.artifact_prefix.rstrip('/')}/run_state.json"
        return upload_file(path, uri)

    def load_issues(self, run_id: str) -> list[Issue]:
        uri = f"{self.artifact_prefix(run_id).rstrip('/')}/issues.json"
        if not blob_exists(uri):
            return []
        tmp = Path(tempfile.mkdtemp(prefix="m3-issues-"))
        path = download_file(uri, tmp / "issues.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [Issue.model_validate(item) for item in payload.get("issues") or []]

    def save_issues(self, run_id: str, issues: list[Issue]) -> str:
        tmp = Path(tempfile.mkdtemp(prefix="m3-issues-save-"))
        path = tmp / "issues.json"
        write_json_artifact(path, {"issues": [issue.model_dump(mode="json") for issue in issues]})
        uri = f"{self.artifact_prefix(run_id).rstrip('/')}/issues.json"
        return upload_file(path, uri)

    def load_json(self, run_id: str, relative: str) -> dict[str, Any] | None:
        uri = f"{self.artifact_prefix(run_id).rstrip('/')}/{relative}"
        if not blob_exists(uri):
            return None
        tmp = Path(tempfile.mkdtemp(prefix="m3-json-"))
        path = download_file(uri, tmp / Path(relative).name)
        return json.loads(path.read_text(encoding="utf-8"))

    def inventory_package(self, package_uri: str) -> list[dict[str, Any]]:
        bucket, blob = parse_gs_uri(package_uri)
        prefix = blob if blob.endswith("/") else f"{blob}/"
        records = []
        for item in list_object_metadata(bucket, prefix):
            relative = item["name"][len(prefix) :].lstrip("/")
            if not relative:
                continue
            records.append({**item, "relative": relative})
        return records

    def download_package(self, package_uri: str, dest: str | Path) -> list[dict[str, Any]]:
        bucket, blob = parse_gs_uri(package_uri)
        prefix = blob if blob.endswith("/") else f"{blob}/"
        return download_prefix(bucket, prefix, dest)

    def upload_workspace_file(self, run_id: str, local_path: str | Path, relative: str) -> str:
        uri = f"{self.artifact_prefix(run_id).rstrip('/')}/{relative}"
        return upload_file(local_path, uri)

    def restore_evidence(self, run_id: str, workspace: str | Path) -> Path:
        dest = Path(workspace)
        dest.mkdir(parents=True, exist_ok=True)
        prefix = f"{settings.organization_id}/{settings.workspace_id}/runs/{run_id}/"
        download_prefix(self.artifact_bucket, prefix, dest)
        return dest


def bind_run_repository(repo: RunRepository) -> Token[RunRepository | None]:
    return _current_repo.set(repo)


def reset_run_repository(token: Token[RunRepository | None]) -> None:
    _current_repo.reset(token)


def get_run_repository() -> RunRepository:
    current = _current_repo.get()
    if current is not None:
        return current
    raw_bucket = (settings.raw_bucket or "").strip()
    artifact_bucket = (settings.artifact_bucket or "").strip()
    if raw_bucket and artifact_bucket:
        return GcsRunRepository(raw_bucket=raw_bucket, artifact_bucket=artifact_bucket)
    raise ValidationBlockedError(
        "Run repository requires MODELREADY_RAW_BUCKET and MODELREADY_ARTIFACT_BUCKET."
    )


def validate_package_uri(package_uri: str, repo: RunRepository) -> str:
    value = package_uri.strip()
    if not value:
        raise SafetyViolationError("package_uri is required.")
    lowered = value.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        raise SafetyViolationError("HTTP URLs are not accepted as dataset packages.")
    if not value.startswith("gs://"):
        raise SafetyViolationError("package_uri must be a gs:// URI in the configured raw bucket.")
    bucket, blob = parse_gs_uri(value)
    if bucket != repo.raw_bucket:
        raise SafetyViolationError("package_uri must be inside the configured raw bucket.")
    if bucket == repo.artifact_bucket:
        raise SafetyViolationError("Artifact-bucket paths cannot be used as raw packages.")
    parts = [part.lower() for part in blob.split("/") if part]
    if "truth" in parts:
        raise SafetyViolationError("Regression truth paths are not allowed in runtime packages.")
    if any(name in blob.replace("\\", "/") for name in FORBIDDEN_PACKAGE_NAMES):
        raise SafetyViolationError("Regression truth files are not allowed in runtime packages.")
    if not blob:
        raise SafetyViolationError("package_uri must include a package prefix.")
    return value if value.endswith("/") else f"{value}/"


def assert_runtime_package(records: list[dict[str, Any]]) -> list[str]:
    relatives = [
        str(item.get("relative") or item.get("name") or "").replace("\\", "/")
        for item in records
    ]
    names = {Path(relative).name for relative in relatives if relative}
    for relative in relatives:
        lowered = relative.lower()
        if "truth/" in lowered or lowered.endswith("/truth"):
            raise SafetyViolationError("Runtime package must not include truth/.")
        if Path(relative).name in FORBIDDEN_PACKAGE_NAMES:
            raise SafetyViolationError("Runtime package must not include regression truth files.")
    if "model_intent.json" not in names:
        raise AssignmentInitError(
            "Package is missing required runtime file: model_intent.json",
            reason="MISSING_REQUIRED_SOURCE",
            source="model_intent.json",
        )
    extra_forbidden = names & set(FORBIDDEN_PACKAGE_NAMES)
    if extra_forbidden:
        raise SafetyViolationError(f"Forbidden files present: {sorted(extra_forbidden)}")
    return sorted(names)


def fingerprint_package_dir(package_dir: str | Path) -> tuple[str, dict[str, str]]:
    root = Path(package_dir)
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            hashes[path.relative_to(root).as_posix()] = sha256_file(path)
    return dataset_fingerprint(hashes), hashes


def _blob_from_uri(uri: str) -> str:
    _bucket, blob = parse_gs_uri(uri)
    return blob
