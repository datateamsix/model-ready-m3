"""Synchronous M3 run coordinator: legal stages, evidence, fail-closed sequencing."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.core.contracts import Issue, RunStatusEvent, utc_now
from app.core.errors import IllegalTransitionError, ValidationBlockedError
from app.core.model_intent import load_model_intent
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
from app.tools.issues import detect_phase1_issues
from app.tools.provenance import bind_provenance, dataset_fingerprint

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
        self.dataset_fp = dataset_fingerprint(hashes)
        bind_provenance(self.run_id, self.artifact_dir)
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
        google = self._google_repairs()
        meta = self._meta_repairs()
        self.google_ready = google
        self.meta_ready = meta

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
        summary = {
            "run_id": self.run_id,
            "dataset_fingerprint": getattr(self, "dataset_fp", None),
            "stage": self.stage.value,
            "state_history": [event.model_dump(mode="json") for event in self.events],
            "detected_issues": [issue.model_dump(mode="json") for issue in self.issues],
            "artifact_uris": {
                "model_ready": str(self.model_ready_path)
                if self.model_ready_path.exists()
                else None,
                "readiness": str(self.readiness_path) if self.readiness_path.exists() else None,
                "transformation_manifest": str(self.manifest_path)
                if self.manifest_path.exists()
                else None,
                "provenance": str(self.provenance_path) if self.provenance_path.exists() else None,
                "meridian_contract": str(self.contract_path)
                if self.contract_path.exists()
                else None,
                "publish_receipt": str(self.publish_path) if self.publish_path.exists() else None,
            },
            "readiness_status": (
                json.loads(self.readiness_path.read_text(encoding="utf-8")).get("status")
                if self.readiness_path.exists()
                else None
            ),
            "publish_status": (
                json.loads(self.publish_path.read_text(encoding="utf-8")).get("parity_status")
                if self.publish_path.exists()
                else None
            ),
            "final_state": self.stage.value,
            "gate": gate,
            "created_at": utc_now().isoformat(),
        }
        write_json_artifact(self.summary_path, summary)
        return summary
