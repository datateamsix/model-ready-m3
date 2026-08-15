"""Local pre-cloud deployment checks. Does not deploy anything."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import google.auth

from app.agent import root_agent
from app.config import settings
from app.core.contracts import Issue, SourceArtifactEvidence, TransformationEvidence
from app.core.run_coordinator import RunCoordinator
from app.core.state import SUCCESS_MILESTONES, TERMINAL_STAGES, RunStage
from app.tools.adk_tools import PHASE1_ADK_TOOLS
from app.tools.gate import evaluate_model_ready_gate

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = REPO_ROOT / ".env.example"
DATASET_A_RAW = REPO_ROOT / "tests" / "fixtures" / "music_center" / "dataset_a" / "raw"
DATASET_A_TRUTH = (
    REPO_ROOT / "tests" / "fixtures" / "music_center" / "dataset_a" / "truth"
)


@dataclass(frozen=True, slots=True)
class PrecloudCheck:
    name: str
    passed: bool
    detail: str


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def collect_checks(*, live: bool = False) -> list[PrecloudCheck]:
    example = parse_env_file(ENV_EXAMPLE)
    checks = [
        _check_project(example),
        _check_vertex_location(),
        _check_cloud_region(),
        _check_location_split(),
        _check_runtime_sa(example),
        _check_raw_bucket(example),
        _check_artifact_bucket(example),
        _check_bq_models_dataset(),
        _check_gemini_model(),
        _check_no_committed_key(),
        _check_adk_import(),
        _check_dataset_a_isolation(),
        _check_phase1_contracts(),
    ]
    if live:
        checks.append(_check_adc())
    return checks


def all_required_passed(checks: list[PrecloudCheck]) -> bool:
    return all(check.passed for check in checks)


def format_report(checks: list[PrecloudCheck]) -> str:
    lines = ["MODELREADY PRE-CLOUD CHECK", ""]
    for check in checks:
        mark = "[x]" if check.passed else "[ ]"
        lines.append(f"{mark} {check.name}: {check.detail}")
    lines.append("")
    ready = "READY_FOR_CLOUD_RUN" if all_required_passed(checks) else "NOT_READY_FOR_CLOUD_RUN"
    lines.append(ready)
    return "\n".join(lines)


def _configured(value: str | None, example: dict[str, str], key: str) -> str:
    return (value or "").strip() or example.get(key, "").strip()


def _check_project(example: dict[str, str]) -> PrecloudCheck:
    project_id = settings.project_id or example.get("GOOGLE_CLOUD_PROJECT", "")
    return PrecloudCheck("project", bool(project_id), project_id or "missing")


def _check_vertex_location() -> PrecloudCheck:
    location = settings.vertex_location
    return PrecloudCheck("Vertex endpoint", location == "global", location or "missing")


def _check_cloud_region() -> PrecloudCheck:
    region = settings.cloud_region
    return PrecloudCheck(
        "cloud region",
        bool(region) and region != "global",
        region or "missing",
    )


def _check_location_split() -> PrecloudCheck:
    vertex = settings.vertex_location
    region = settings.cloud_region
    passed = bool(vertex) and bool(region) and vertex != region and region != "global"
    detail = f"Vertex={vertex} region={region}"
    if region == "global":
        detail = "cloud region must not be global"
    elif vertex == region:
        detail = "Vertex location must not equal Cloud Run region"
    return PrecloudCheck("Vertex vs cloud region split", passed, detail)


def _check_runtime_sa(example: dict[str, str]) -> PrecloudCheck:
    identity = _configured(settings.runtime_sa, example, "M3_RUNTIME_SA")
    return PrecloudCheck("runtime identity configured", bool(identity), identity or "missing")


def _check_raw_bucket(example: dict[str, str]) -> PrecloudCheck:
    bucket = _configured(settings.raw_bucket, example, "MODELREADY_RAW_BUCKET")
    return PrecloudCheck(
        "raw bucket configured",
        bool(bucket),
        "configured" if bucket else "missing",
    )


def _check_artifact_bucket(example: dict[str, str]) -> PrecloudCheck:
    bucket = _configured(settings.artifact_bucket, example, "MODELREADY_ARTIFACT_BUCKET")
    return PrecloudCheck(
        "artifact bucket configured",
        bool(bucket),
        "configured" if bucket else "missing",
    )


def _check_bq_models_dataset() -> PrecloudCheck:
    dataset_id = settings.bq_models_dataset
    return PrecloudCheck("BigQuery model dataset", bool(dataset_id), dataset_id or "missing")


def _check_gemini_model() -> PrecloudCheck:
    model = settings.gemini_model
    return PrecloudCheck("M3 Gemini model", bool(model), model or "missing")


def _check_no_committed_key() -> PrecloudCheck:
    configured = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not configured:
        return PrecloudCheck("ADC (no committed key)", True, "GOOGLE_APPLICATION_CREDENTIALS unset")
    path = Path(configured)
    try:
        inside_repo = path.resolve().is_relative_to(REPO_ROOT.resolve())
    except (OSError, ValueError):
        inside_repo = False
    passed = not inside_repo
    detail = (
        "GOOGLE_APPLICATION_CREDENTIALS points inside the repo" if not passed else configured
    )
    return PrecloudCheck("ADC (no committed key)", passed, detail)


def _check_adk_import() -> PrecloudCheck:
    names = agent_tool_names(root_agent)
    expected = {fn.__name__ for fn in PHASE1_ADK_TOOLS}
    missing = sorted(expected - names)
    passed = root_agent is not None and not missing
    detail = "root_agent + Phase 1 tools" if passed else f"missing tools: {missing}"
    return PrecloudCheck("ADK root agent imports", passed, detail)


def _check_dataset_a_isolation() -> PrecloudCheck:
    if not DATASET_A_RAW.is_dir():
        return PrecloudCheck("Dataset A runtime isolation", False, "raw fixture missing")
    leaked = [
        str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        for path in DATASET_A_RAW.rglob("*")
        if path.is_file() and "expected_model_ready" in path.name
    ]
    truth = DATASET_A_TRUTH / "expected_model_ready_weekly.csv"
    passed = not leaked and truth.is_file()
    if leaked:
        detail = f"truth leaked into raw: {leaked}"
    elif not truth.is_file():
        detail = "regression truth missing from truth/"
    else:
        detail = "raw excludes regression truth"
    return PrecloudCheck("Dataset A runtime isolation", passed, detail)


def _check_phase1_contracts() -> PrecloudCheck:
    passed = (
        Issue is not None
        and SourceArtifactEvidence is not None
        and TransformationEvidence is not None
        and RunCoordinator is not None
        and evaluate_model_ready_gate is not None
        and RunStage.MODEL_READY in SUCCESS_MILESTONES
        and RunStage.MODEL_READY not in TERMINAL_STAGES
    )
    return PrecloudCheck(
        "Phase 1 contracts available",
        passed,
        "Issue/provenance/gate/state contracts importable",
    )


def _check_adc() -> PrecloudCheck:
    try:
        credentials, _project = google.auth.default()
        passed = credentials is not None
        return PrecloudCheck("live ADC", passed, "credentials available" if passed else "no ADC")
    except Exception as exc:
        return PrecloudCheck("live ADC", False, str(exc))


def agent_tool_names(agent: object) -> set[str]:
    names: set[str] = set()
    tools = getattr(agent, "tools", None) or []
    for tool in tools:
        for attr in ("name", "__name__"):
            value = getattr(tool, attr, None)
            if isinstance(value, str) and value:
                names.add(value)
        func = getattr(tool, "func", None) or getattr(tool, "_func", None)
        if callable(func):
            names.add(getattr(func, "__name__", ""))
        if callable(tool):
            names.add(getattr(tool, "__name__", ""))
    return {name for name in names if name}
