"""Synchronous M3 run coordinator: legal stages, evidence, fail-closed sequencing."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.core.contracts import (
    DurableRunState,
    Issue,
    IssueStatus,
    RemediationClass,
    RunStatusEvent,
    utc_now,
)
from app.core.errors import IllegalTransitionError, SafetyViolationError, ValidationBlockedError
from app.core.model_intent import MODEL_READY_COLUMNS, load_model_intent
from app.core.state import RunStage, assert_legal_transition
from app.tools.adk_tools import (
    aggregate_campaign_to_channel_in_file,
    aggregate_file_to_week,
    build_model_ready_frame_from_files,
    canonicalize_channel_labels_in_file,
    evaluate_model_ready_gate_from_files,
    generate_meridian_input_contract_file,
    inventory_package,
    normalize_dates_in_file,
    normalize_numeric_values_in_file,
    profile_source,
    publish_model_ready_table,
    remove_exact_duplicates_from_file,
    validate_bigquery_publish_parity_for_run,
    validate_model_ready_artifact_file,
)
from app.tools.artifacts import sha256_file, write_json_artifact
from app.tools.fingerprints import content_fingerprint
from app.tools.io import read_table
from app.tools.issues import (
    detect_phase1_issues,
    mark_issues_remediating,
    resolve_issues_from_transforms,
)
from app.tools.provenance import bind_provenance, dataset_fingerprint, to_artifact_uri

META_CHANNEL_ALIASES = {
    "Meta": "paid_social",
    "Paid Social": "paid_social",
    "paid_social": "paid_social",
}
GOOGLE_ISSUE_IDS = frozenset({"MC-A-001", "MC-A-003"})
META_ISSUE_IDS = frozenset({"MC-A-002", "MC-A-004", "MC-A-005"})


class RunCoordinator:
    """Enforces state, safety, and sequencing. Does not replace ADK reasoning."""

    def __init__(
        self,
        raw_package: str | Path,
        artifact_root: str | Path,
        run_id: str | None = None,
        workspace: str | Path | None = None,
    ) -> None:
        self.raw_package = Path(raw_package)
        self.run_id = run_id or f"m3a{uuid4().hex[:12]}"
        self.workspace = (
            Path(workspace)
            if workspace is not None
            else Path(artifact_root) / settings.workspace_id / self.run_id
        )
        self.raw_dir = self.workspace / "raw"
        self.transform_dir = self.workspace / "transforms"
        self.artifact_dir = self.workspace
        self.stage = RunStage.NEW
        self.events: list[RunStatusEvent] = []
        self.issues: list[Issue] = []
        self.input_file_count = 0
        self.dataset_fp: str | None = None
        self.intent_path = self.raw_dir / "model_intent.json"
        self.model_ready_path = self.artifact_dir / "model_ready.csv"
        self.readiness_path = self.artifact_dir / "readiness_report.json"
        self.manifest_path = self.artifact_dir / "transformation_manifest.json"
        self.provenance_path = self.artifact_dir / "provenance.json"
        self.contract_path = self.artifact_dir / "meridian_input_contract.json"
        self.publish_path = self.artifact_dir / "publish_receipt.json"
        self.summary_path = self.artifact_dir / "run_summary.json"
        self.issues_path = self.artifact_dir / "issues.json"
        self.google_ready = ""
        self.meta_ready = ""
        self.package_uri: str | None = None
        self.durable_prefix: str | None = None
        self.source_objects: list[dict] = []
        self.created_at = utc_now()

    def transition(self, nxt: RunStage, message: str, progress: float) -> None:
        assert_legal_transition(self.stage, nxt)
        if nxt is RunStage.PUBLISHING and (
            not self.readiness_path.exists()
            or json.loads(self.readiness_path.read_text(encoding="utf-8")).get("status") != "PASS"
        ):
            raise IllegalTransitionError("PUBLISHING requires a PASS readiness receipt.")
        if nxt is RunStage.MODEL_READY:
            required = [
                self.publish_path,
                self.contract_path,
                self.provenance_path,
                self.readiness_path,
            ]
            missing = [str(path) for path in required if not path.exists()]
            if missing:
                raise IllegalTransitionError(f"MODEL_READY missing evidence files: {missing}")
        self.stage = nxt
        event = RunStatusEvent(
            run_id=self.run_id,
            stage=nxt,
            status="RUNNING" if nxt is not RunStage.MODEL_READY else "MODEL_READY",
            message=message,
            progress=progress,
        )
        self.events.append(event)

    def fail(self, message: str) -> None:
        if self.stage is not RunStage.FAILED:
            try:
                assert_legal_transition(self.stage, RunStage.FAILED)
            except IllegalTransitionError:
                pass
            self.stage = RunStage.FAILED
        self.events.append(
            RunStatusEvent(
                run_id=self.run_id,
                stage=RunStage.FAILED,
                status="FAILED",
                message=message,
                progress=1.0,
            )
        )
        self._write_summary()
        raise ValidationBlockedError(message)

    def prepare_workspace(self) -> None:
        if self.raw_dir.exists():
            shutil.rmtree(self.raw_dir)
        self.transform_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.raw_package, self.raw_dir)
        inventory = inventory_package(str(self.raw_dir))
        hashes = {
            item["path"]: sha256_file(self.raw_dir / str(item["path"]))
            for item in inventory["files"]
        }
        self.input_file_count = len(inventory["files"])
        self.dataset_fp = dataset_fingerprint(hashes)
        bind_provenance(self.run_id, self.artifact_dir, dataset_fingerprint=self.dataset_fp)
        self.transition(RunStage.DISCOVERING, "Raw package copied; truth excluded.", 0.1)

    def profile_and_map(self) -> None:
        self.transition(RunStage.PROFILING, "Profiling raw sources.", 0.2)
        for item in inventory_package(str(self.raw_dir))["files"]:
            path = self.raw_dir / str(item["path"])
            if path.suffix.lower() in {".csv", ".parquet"}:
                profile_source(str(path))
        self.transition(RunStage.MAPPING, "Loading model intent and provider context.", 0.3)
        if not self.intent_path.exists():
            self.fail("raw/model_intent.json is required.")
        load_model_intent(json.loads(self.intent_path.read_text(encoding="utf-8")))

    def assess(self) -> list[Issue]:
        self.transition(RunStage.ASSESSING, "Detecting Phase 1 issues.", 0.4)
        intent = load_model_intent(json.loads(self.intent_path.read_text(encoding="utf-8")))
        self.issues = detect_phase1_issues(self.raw_dir, intent)
        return self.issues

    def remediate(self) -> None:
        if any(issue.remediation_class.value != "AUTO_SAFE" for issue in self.issues):
            self.fail("Phase 1 golden slice expected only AUTO_SAFE issues.")
        self.transition(RunStage.REMEDIATING, "Applying AUTO_SAFE repairs.", 0.55)
        mark_issues_remediating(self.issues)
        google = self._google_repairs()
        meta = self._meta_repairs()
        self.google_ready = google
        self.meta_ready = meta
        transforms = (
            json.loads(self.manifest_path.read_text(encoding="utf-8")).get("transforms") or []
        )
        resolve_issues_from_transforms(self.issues, transforms)
        unresolved = [
            issue.issue_id for issue in self.issues if issue.status != IssueStatus.RESOLVED
        ]
        if unresolved:
            self.fail(f"Remediation did not resolve issues: {unresolved}")

    def remediate_selected(self, issue_ids: list[str]) -> dict:
        """Execute deterministic plans for requested AUTO_SAFE issues only.

        Gemini supplies issue IDs. Transform parameters come from registered plans.
        """
        accepted, rejected = self.authorize_remediations(issue_ids)
        if rejected:
            raise SafetyViolationError(
                "apply_safe_remediations rejected unauthorized issue ids: "
                + json.dumps(rejected)
            )
        if not accepted:
            raise SafetyViolationError("No authorized AUTO_SAFE issues were requested.")
        already_resolved = all(issue.status is IssueStatus.RESOLVED for issue in accepted)
        if already_resolved:
            return {
                "resolved": [
                    {
                        "issue_id": issue.issue_id,
                        "action_ids": issue.resolution_action_ids,
                    }
                    for issue in accepted
                ],
                "rejected": [],
                "replayed": True,
            }
        if self.stage is RunStage.ASSESSING:
            self.transition(RunStage.REMEDIATING, "Applying selected AUTO_SAFE repairs.", 0.55)
        elif self.stage is not RunStage.REMEDIATING:
            raise IllegalTransitionError(
                f"apply_safe_remediations is illegal at stage {self.stage.value}."
            )
        mark_issues_remediating(accepted)
        selected_ids = {issue.issue_id for issue in accepted}
        google_weekly = self.transform_dir / "google_weekly.csv"
        meta_weekly = self.transform_dir / "meta_weekly.csv"
        if selected_ids & GOOGLE_ISSUE_IDS:
            if google_weekly.is_file():
                self.google_ready = str(google_weekly)
            else:
                self.google_ready = self._google_repairs()
        if selected_ids & META_ISSUE_IDS:
            if meta_weekly.is_file():
                self.meta_ready = str(meta_weekly)
            else:
                self.meta_ready = self._meta_repairs()
        transforms = (
            json.loads(self.manifest_path.read_text(encoding="utf-8")).get("transforms") or []
        )
        resolve_issues_from_transforms(accepted, transforms)
        unresolved = [
            issue.issue_id for issue in accepted if issue.status != IssueStatus.RESOLVED
        ]
        if unresolved:
            self.fail(f"Remediation did not resolve requested issues: {unresolved}")
        self.write_issues()
        return {
            "resolved": [
                {"issue_id": issue.issue_id, "action_ids": issue.resolution_action_ids}
                for issue in accepted
            ],
            "rejected": [],
            "replayed": False,
        }

    def authorize_remediations(
        self, issue_ids: list[str]
    ) -> tuple[list[Issue], list[dict]]:
        by_id = {issue.issue_id: issue for issue in self.issues}
        accepted: list[Issue] = []
        rejected: list[dict] = []
        seen: set[str] = set()
        for issue_id in issue_ids:
            if issue_id in seen:
                continue
            seen.add(issue_id)
            issue = by_id.get(issue_id)
            if issue is None:
                rejected.append({"issue_id": issue_id, "reason": "unknown_issue"})
                continue
            if issue.remediation_class is not RemediationClass.AUTO_SAFE:
                rejected.append(
                    {
                        "issue_id": issue_id,
                        "reason": "not_auto_safe",
                        "remediation_class": issue.remediation_class.value,
                    }
                )
                continue
            if issue.status not in {
                IssueStatus.OPEN,
                IssueStatus.REMEDIATING,
                IssueStatus.RESOLVED,
            }:
                rejected.append(
                    {
                        "issue_id": issue_id,
                        "reason": f"illegal_status:{issue.status.value}",
                    }
                )
                continue
            accepted.append(issue)
        return accepted, rejected

    def write_issues(self) -> Path:
        write_json_artifact(
            self.issues_path,
            {"issues": [issue.model_dump(mode="json") for issue in self.issues]},
        )
        return self.issues_path

    def load_issues_file(self) -> list[Issue]:
        if not self.issues_path.is_file():
            return []
        payload = json.loads(self.issues_path.read_text(encoding="utf-8"))
        self.issues = [Issue.model_validate(item) for item in payload.get("issues") or []]
        return self.issues

    def to_durable_state(self) -> DurableRunState:
        detected_ids = [issue.issue_id for issue in self.issues]
        resolved_ids = [
            issue.issue_id for issue in self.issues if issue.status is IssueStatus.RESOLVED
        ]
        open_ids = [issue_id for issue_id in detected_ids if issue_id not in resolved_ids]
        prefix = (self.durable_prefix or to_artifact_uri(self.workspace)).rstrip("/")
        publish = self._load_json_if_exists(self.publish_path)
        return DurableRunState(
            run_id=self.run_id,
            organization_id=settings.organization_id,
            workspace_id=settings.workspace_id,
            package_uri=self.package_uri or to_artifact_uri(self.raw_package),
            package_fingerprint=self.dataset_fp or "",
            stage=self.stage,
            created_at=self.created_at,
            updated_at=utc_now(),
            detected_issue_ids=detected_ids,
            resolved_issue_ids=resolved_ids,
            open_issue_ids=open_ids,
            artifact_prefix=prefix + "/",
            model_artifact_uri=self._durable_uri("model_ready.csv", self.model_ready_path),
            readiness_uri=self._durable_uri("readiness_report.json", self.readiness_path),
            provenance_uri=self._durable_uri("provenance.json", self.provenance_path),
            manifest_uri=self._durable_uri("transformation_manifest.json", self.manifest_path),
            publish_receipt_uri=self._durable_uri("publish_receipt.json", self.publish_path),
            meridian_contract_uri=self._durable_uri(
                "meridian_input_contract.json", self.contract_path
            ),
            run_summary_uri=self._durable_uri("run_summary.json", self.summary_path),
            bigquery_table=self._publish_destination(publish),
            status=self._status_label(),
            google_ready_relpath=self._relpath(self.google_ready),
            meta_ready_relpath=self._relpath(self.meta_ready),
            source_objects=list(self.source_objects),
            scratch_dir=str(self.workspace),
            input_file_count=self.input_file_count,
        )

    def restore_from_durable(self, state: DurableRunState, issues: list[Issue]) -> None:
        self.stage = state.stage
        self.dataset_fp = state.package_fingerprint
        self.package_uri = state.package_uri
        self.durable_prefix = state.artifact_prefix
        self.issues = issues
        self.input_file_count = state.input_file_count
        self.created_at = state.created_at
        self.source_objects = list(state.source_objects)
        if state.google_ready_relpath:
            self.google_ready = str(self.workspace / state.google_ready_relpath)
        if state.meta_ready_relpath:
            self.meta_ready = str(self.workspace / state.meta_ready_relpath)
        bind_provenance(self.run_id, self.artifact_dir, dataset_fingerprint=self.dataset_fp)

    def validation_blockers(self) -> list[str]:
        blockers: list[str] = []
        if not self.dataset_fp:
            blockers.append("package_fingerprint_missing")
        if self.stage not in {RunStage.ASSESSING, RunStage.REMEDIATING, RunStage.VALIDATING}:
            blockers.append(f"illegal_stage:{self.stage.value}")
        for issue in self.issues:
            if (
                issue.remediation_class is RemediationClass.BLOCKED
                and issue.status != IssueStatus.RESOLVED
            ):
                blockers.append(f"blocked_issue:{issue.issue_id}")
            elif (
                issue.remediation_class is RemediationClass.APPROVAL_REQUIRED
                and issue.status != IssueStatus.RESOLVED
            ):
                blockers.append(f"approval_required:{issue.issue_id}")
            elif (
                issue.remediation_class is RemediationClass.AUTO_SAFE
                and issue.status != IssueStatus.RESOLVED
            ):
                blockers.append(f"unresolved_auto_safe:{issue.issue_id}")
        return blockers

    def _status_label(self) -> str:
        if self.stage is RunStage.MODEL_READY:
            return "MODEL_READY"
        if self.stage is RunStage.FAILED:
            return "FAILED"
        if self.stage is RunStage.COMPLETE:
            return "COMPLETE"
        return "IN_PROGRESS"

    def _durable_uri(self, relative: str, path: Path) -> str | None:
        if not path.exists():
            return None
        if self.durable_prefix:
            return f"{self.durable_prefix.rstrip('/')}/{relative}"
        return to_artifact_uri(path)

    def _relpath(self, value: str) -> str | None:
        if not value:
            return None
        path = Path(value)
        try:
            return path.resolve().relative_to(self.workspace.resolve()).as_posix()
        except ValueError:
            return Path(value).name

    def validate_local(self) -> None:
        self.transition(RunStage.VALIDATING, "Assembling and validating model frame.", 0.7)
        built = build_model_ready_frame_from_files(
            google_path=self.google_ready,
            meta_path=self.meta_ready,
            shopify_path=str(self.raw_dir / "shopify_weekly.csv"),
            ga4_path=str(self.raw_dir / "ga4_weekly.csv"),
            controls_path=str(self.raw_dir / "controls_weekly.csv"),
            population_path=str(self.raw_dir / "geo_population.csv"),
            intent_json_path=str(self.intent_path),
            output_path=str(self.model_ready_path),
        )
        receipt = validate_model_ready_artifact_file(
            path=built["output_path"],
            intent_json_path=str(self.intent_path),
            provenance_path=str(self.manifest_path),
            run_id=self.run_id,
        )
        write_json_artifact(self.readiness_path, receipt)
        if receipt["status"] != "PASS":
            self.fail(f"Readiness receipt FAIL: {receipt}")

    def publish(self) -> dict:
        self.transition(RunStage.PUBLISHING, "Publishing validated artifact to BigQuery.", 0.85)
        written = publish_model_ready_table(str(self.model_ready_path), self.run_id)
        contract = generate_meridian_input_contract_file(
            artifact_path=str(self.model_ready_path),
            intent_json_path=str(self.intent_path),
            run_id=self.run_id,
            table_id=written["table_id"],
            output_path=str(self.contract_path),
        )
        receipt = validate_bigquery_publish_parity_for_run(
            artifact_path=str(self.model_ready_path),
            run_id=self.run_id,
            table_id=written["table_id"],
            provenance_uri=str(self.provenance_path),
            meridian_contract_uri=str(self.contract_path),
        )
        write_json_artifact(self.publish_path, receipt)
        return {"publish": receipt, "contract": contract}

    def complete(self) -> dict:
        gate = evaluate_model_ready_gate_from_files(
            str(self.readiness_path),
            str(self.publish_path),
            str(self.contract_path),
            str(self.provenance_path),
        )
        self.transition(RunStage.MODEL_READY, "Evidence-backed MODEL_READY.", 1.0)
        summary = self._write_summary(gate)
        return {"status": "MODEL_READY", "gate": gate, "summary": summary}

    def run_local(self) -> dict:
        self.prepare_workspace()
        self.profile_and_map()
        self.assess()
        self.remediate()
        self.validate_local()
        return self._write_summary()

    def run(self) -> dict:
        self.run_local()
        self.publish()
        return self.complete()

    def _google_repairs(self) -> str:
        dated = str(self.transform_dir / "google_dates.csv")
        normalize_dates_in_file(
            str(self.raw_dir / "google_ads_daily.csv"),
            "date",
            dated,
            "YYYY-MM-DD",
        )
        deduped = str(self.transform_dir / "google_deduped.csv")
        remove_exact_duplicates_from_file(dated, deduped)
        channeled = str(self.transform_dir / "google_channel.csv")
        aggregate_campaign_to_channel_in_file(
            deduped,
            ["date", "geo", "channel"],
            ["impressions", "clicks", "cost"],
            channeled,
            provider_id="google_ads",
        )
        weekly = str(self.transform_dir / "google_weekly.csv")
        aggregate_file_to_week(
            channeled,
            "date",
            ["geo", "channel"],
            ["impressions", "clicks", "cost"],
            weekly,
            provider_id="google_ads",
        )
        return weekly

    def _meta_repairs(self) -> str:
        dated = str(self.transform_dir / "meta_dates.csv")
        normalize_dates_in_file(
            str(self.raw_dir / "meta_ads_weekly.csv"),
            "week_start",
            dated,
            "MM/DD/YYYY",
        )
        numeric = str(self.transform_dir / "meta_numeric.csv")
        normalize_numeric_values_in_file(dated, "amount_spent", numeric)
        labeled = str(self.transform_dir / "meta_channels.csv")
        canonicalize_channel_labels_in_file(numeric, "channel", META_CHANNEL_ALIASES, labeled)
        weekly = str(self.transform_dir / "meta_weekly.csv")
        aggregate_campaign_to_channel_in_file(
            labeled,
            ["week_start", "geo", "channel"],
            ["impressions", "clicks", "amount_spent"],
            weekly,
            provider_id="meta_ads",
        )
        return weekly

    def _write_summary(self, gate: dict | None = None) -> dict:
        detected, resolved, open_count = self._issue_counts()
        readiness = self._load_json_if_exists(self.readiness_path)
        publish = self._load_json_if_exists(self.publish_path)
        contract = self._load_json_if_exists(self.contract_path)
        provenance = self._load_json_if_exists(self.provenance_path)
        records = (provenance or {}).get("records") or (provenance or {}).get("transforms") or []
        summary = {
            "run_id": self.run_id,
            "dataset_fingerprint": self.dataset_fp,
            "final_state": self.stage.value,
            "input_file_count": self.input_file_count,
            "detected_issue_count": detected,
            "resolved_issue_count": resolved,
            "open_issue_count": open_count,
            "transformation_count": len(records),
            "issues": [
                {
                    "issue_id": issue.issue_id,
                    "rule_id": issue.rule_id,
                    "status": issue.status.value,
                    "resolution_action_ids": issue.resolution_action_ids,
                    "resolution_evidence": issue.resolution_evidence,
                }
                for issue in self.issues
            ],
            "package_uri": self.package_uri,
            "artifact_prefix": self.durable_prefix,
            "scratch_dir": str(self.workspace),
            "model_artifact": self._model_artifact_summary(),
            "readiness": {"status": (readiness or {}).get("status")},
            "publish": {
                "status": (publish or {}).get("status"),
                "parity_status": (publish or {}).get("parity_status"),
                "destination": self._publish_destination(publish),
            },
            "meridian_contract": {"status": (contract or {}).get("status")},
            "provenance": {
                "status": self._provenance_status(gate, readiness),
                "record_count": len(records),
            },
            "state_history": [event.model_dump(mode="json") for event in self.events],
            "gate": gate,
            "artifact_uris": {
                "model_ready": self._durable_uri("model_ready.csv", self.model_ready_path),
                "readiness": self._durable_uri("readiness_report.json", self.readiness_path),
                "transformation_manifest": self._durable_uri(
                    "transformation_manifest.json", self.manifest_path
                ),
                "provenance": self._durable_uri("provenance.json", self.provenance_path),
                "meridian_contract": self._durable_uri(
                    "meridian_input_contract.json", self.contract_path
                ),
                "publish_receipt": self._durable_uri("publish_receipt.json", self.publish_path),
                "run_state": self._durable_uri("run_state.json", self.workspace / "run_state.json"),
                "issues": self._durable_uri("issues.json", self.issues_path),
            },
            "created_at": utc_now().isoformat(),
        }
        write_json_artifact(self.summary_path, summary)
        return summary

    def write_summary(self, gate: dict | None = None) -> dict:
        return self._write_summary(gate)

    def issue_counts(self) -> tuple[int, int, int]:
        return self._issue_counts()

    def _issue_counts(self) -> tuple[int, int, int]:
        detected = len(self.issues)
        resolved = sum(issue.status == IssueStatus.RESOLVED for issue in self.issues)
        open_count = detected - resolved
        return detected, resolved, open_count

    def _model_artifact_summary(self) -> dict:
        if not self.model_ready_path.exists():
            return {"path": None, "row_count": None, "column_count": None, "fingerprint": None}
        frame = read_table(self.model_ready_path)
        return {
            "path": self._durable_uri("model_ready.csv", self.model_ready_path),
            "row_count": int(len(frame)),
            "column_count": int(len(frame.columns)),
            "fingerprint": content_fingerprint(
                frame, columns=MODEL_READY_COLUMNS, key_columns=["time", "geo"]
            ),
        }

    def _load_json_if_exists(self, path: Path) -> dict | None:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _publish_destination(self, publish: dict | None) -> str | None:
        if not publish:
            return None
        project_id = publish.get("project_id")
        dataset_id = publish.get("dataset_id")
        table_id = publish.get("table_id")
        if project_id and dataset_id and table_id:
            return f"{project_id}.{dataset_id}.{table_id}"
        return table_id

    def _provenance_status(self, gate: dict | None, readiness: dict | None) -> str | None:
        if gate and gate.get("evidence"):
            return "PASS" if gate["evidence"].get("provenance_pass") else "FAIL"
        checks = (readiness or {}).get("checks") or []
        mr018 = next((check for check in checks if check.get("rule_id") == "MR-018"), None)
        if mr018 is None:
            return None
        return "PASS" if mr018.get("passed") else "FAIL"
