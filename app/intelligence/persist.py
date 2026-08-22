"""Persist intelligence artifacts onto an existing run without mutating DOMAIN_VIEW."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from app.core.contracts import DurableRunState, utc_now
from app.core.run_repository import RunRepository
from app.tools.artifacts import write_json_artifact

INTEL_DIR = "intelligence"


def persist_intelligence_artifacts(
    *,
    repo: RunRepository,
    state: DurableRunState,
    bundle: dict[str, Any],
    scenarios: dict[str, Any] | None = None,
) -> dict[str, str]:
    root = Path(tempfile.mkdtemp(prefix="prem3-intel-"))
    files: dict[str, Any] = {
        f"{INTEL_DIR}/pre_eda_diagnostic_receipt.json": bundle["receipt"],
        f"{INTEL_DIR}/modeling_feasibility.json": bundle["modeling_feasibility"],
        f"{INTEL_DIR}/semantic_readiness_interview.json": bundle["semantic_interview"],
        f"{INTEL_DIR}/guided_remediation.json": {
            "run_id": state.run_id,
            "pack": "PreM3 User Resolution Pack",
            "items": bundle.get("guided_remediation") or [],
        },
        f"{INTEL_DIR}/run_intelligence_summary.json": bundle["summary"],
        f"{INTEL_DIR}/learned_routing.json": bundle.get("learned_routing")
        or bundle.get("receipt", {}).get("learned_routing")
        or {},
    }
    uris: dict[str, str] = {}
    for relative, payload in files.items():
        path = root / relative
        write_json_artifact(path, payload)
        uris[relative] = repo.upload_workspace_file(state.run_id, path, relative)
    report_path = root / f"{INTEL_DIR}/pre_eda_diagnostic_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(bundle["report_markdown"], encoding="utf-8")
    uris[report_path.relative_to(root).as_posix()] = repo.upload_workspace_file(
        state.run_id, report_path, f"{INTEL_DIR}/pre_eda_diagnostic_report.md"
    )
    interview_md = root / f"{INTEL_DIR}/semantic_readiness_interview.md"
    interview_md.write_text(bundle["semantic_interview_markdown"], encoding="utf-8")
    uris[interview_md.relative_to(root).as_posix()] = repo.upload_workspace_file(
        state.run_id, interview_md, f"{INTEL_DIR}/semantic_readiness_interview.md"
    )
    if scenarios is not None:
        scenario_path = root / f"{INTEL_DIR}/scope_scenarios.json"
        write_json_artifact(scenario_path, scenarios)
        uris[scenario_path.relative_to(root).as_posix()] = repo.upload_workspace_file(
            state.run_id, scenario_path, f"{INTEL_DIR}/scope_scenarios.json"
        )
    state.updated_at = utc_now()
    repo.save_run(state)
    return uris
