"""Synchronous M3 run coordinator: legal stages, evidence, fail-closed sequencing."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.core.contracts import Issue, IssueStatus, RunStatusEvent, utc_now
from app.core.errors import IllegalTransitionError, ValidationBlockedError
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


class RunCoordinator:
    """Enforces state, safety, and sequencing. Does not replace ADK reasoning."""

    def __init__(
        self, raw_package: str | Path, artifact_root: str | Path, run_id: str | None = None
    ) -> None:
        self.raw_package = Path(raw_package)
        self.run_id = run_id or f"m3a{uuid4().hex[:12]}"
        self.workspace = Path(artifact_root) / settings.workspace_id / self.run_id
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
                "model_ready": to_artifact_uri(self.model_ready_path)
                if self.model_ready_path.exists()
                else None,
                "readiness": to_artifact_uri(self.readiness_path)
                if self.readiness_path.exists()
                else None,
                "transformation_manifest": to_artifact_uri(self.manifest_path)
                if self.manifest_path.exists()
                else None,
                "provenance": to_artifact_uri(self.provenance_path)
                if self.provenance_path.exists()
                else None,
                "meridian_contract": to_artifact_uri(self.contract_path)
                if self.contract_path.exists()
                else None,
                "publish_receipt": to_artifact_uri(self.publish_path)
                if self.publish_path.exists()
                else None,
            },
            "created_at": utc_now().isoformat(),
        }
        write_json_artifact(self.summary_path, summary)
        return summary

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
            "path": to_artifact_uri(self.model_ready_path),
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
