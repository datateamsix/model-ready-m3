"""Synchronous PreM3 run coordinator: legal stages, evidence, fail-closed sequencing."""

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
from app.core.execution_context import current_execution_context
from app.core.meridian_eda_contracts import MeridianEDAReceipt
from app.core.model_intent import MODEL_READY_COLUMNS, load_model_intent, model_ready_columns
from app.core.model_ready_manifest import ModelReadyManifest, compile_model_ready_manifest
from app.core.product import PRODUCT_NAME
from app.core.resource_paths import artifact_object_prefix_for_execution, legacy_run_artifact_prefix
from app.core.source_inventory import (
    CanonicalRole,
    SourceInventory,
    assert_required_sources_present,
    inventory_assignment_sources,
    source_inventory_receipt,
)
from app.core.state import RunStage, assert_legal_transition
from app.core.tenancy import current_tenant, current_workspace
from app.integrations.bigquery import get_bigquery_client
from app.tools.adk_tools import (
    build_model_ready_frame_from_files,
    generate_meridian_input_contract_file,
    inventory_package,
    profile_source,
    validate_model_ready_artifact_file,
)
from app.tools.artifacts import sha256_file, write_json_artifact
from app.tools.bigquery_inspect import all_checks_passed, inspect_model_destination
from app.tools.bigquery_publish import (
    read_bigquery_table,
    sanitize_table_id,
    validate_bigquery_publish_parity,
    write_bigquery_model_table,
)
from app.tools.fingerprints import content_fingerprint
from app.tools.gate import evaluate_final_model_ready_gate
from app.tools.io import read_table
from app.tools.issues import (
    detect_assignment_issues,
    mark_issues_remediating,
    resolve_issues_from_transforms,
)
from app.tools.meridian_contract import MeridianInputContract, MeridianSource
from app.tools.meridian_eda import (
    assert_fingerprint_matches,
    execute_meridian_eda,
    resolve_eda_source,
)
from app.tools.meridian_eda_gate import (
    accept_eda_analysis,
    evaluate_meridian_eda_gate,
    render_pre_modeling_handoff,
)
from app.tools.meridian_eda_job import meridian_eda_job_configured
from app.tools.model_consumption import (
    build_confirmation_receipt,
    build_consumption_receipt,
    consumption_view_ref,
    count_registry_rows,
    fingerprint_frame,
    promote_consumption_view,
    read_registry_row,
    table_labels,
    upsert_model_ready_run,
    verify_consumption_view,
)
from app.tools.model_frame import coerce_model_frame_types
from app.tools.provenance import bind_provenance, dataset_fingerprint, to_artifact_uri
from app.tools.schema_compiler import compile_model_consumption_schema, inspect_table_schema_records
from app.tools.source_adapters import repair_source_file


def _meridian_required_fields(contract: MeridianInputContract) -> list[str]:
    required = [contract.fields.time, contract.fields.kpi, contract.fields.revenue_per_kpi]
    if contract.fields.geo:
        required.append(contract.fields.geo)
    if contract.fields.population:
        required.append(contract.fields.population)
    required.extend(contract.media.values())
    required.extend(contract.media_spend.values())
    required.extend(contract.organic_media)
    required.extend(contract.controls)
    return required


class RunCoordinator:
    """Enforces state, safety, and sequencing. Does not replace ADK reasoning."""

    def __init__(
        self,
        raw_package: str | Path,
        artifact_root: str | Path,
        run_id: str | None = None,
        workspace: str | Path | None = None,
        stable_view_id: str | None = None,
        dataset_id: str = "",
        dataset_role: str | None = None,
        qualification_mode: str | None = None,
        business_name: str | None = None,
    ) -> None:
        self.raw_package = Path(raw_package)
        self.run_id = run_id or f"m3a{uuid4().hex[:12]}"
        self.workspace = (
            Path(workspace) if workspace is not None else Path(artifact_root) / self.run_id
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
        self.model_ready_manifest_path = self.artifact_dir / "model_ready_manifest.json"
        self.consumption_receipt_path = self.artifact_dir / "model_consumption_receipt.json"
        self.confirmation_path = self.artifact_dir / "model_ready_confirmation_receipt.json"
        self.eda_dir = self.artifact_dir / "eda"
        self.eda_html_path = self.eda_dir / "meridian_eda_report.html"
        self.eda_config_path = self.eda_dir / "meridian_eda_config.json"
        self.eda_receipt_path = self.eda_dir / "meridian_eda_receipt.json"
        self.eda_feedback_path = self.eda_dir / "meridian_user_feedback.json"
        self.eda_analysis_path = self.eda_dir / "m3_eda_analysis.json"
        self.eda_handoff_path = self.eda_dir / "pre_modeling_handoff.md"
        self.google_ready = ""
        self.meta_ready = ""
        self.repaired_paths: dict[str, str] = {}
        self.inventory: SourceInventory | None = None
        self.dataset_id = dataset_id
        self.dataset_role = dataset_role
        self.qualification_mode = qualification_mode
        self.business_name = business_name
        self.package_uri: str | None = None
        self.durable_prefix: str | None = None
        self.source_objects: list[dict] = []
        self.created_at = utc_now()
        self.consumption_view: str | None = None
        self.physical_schema_fingerprint: str | None = None
        self.stable_view_id = stable_view_id
        self._persisted_organization_id: str | None = None
        self._persisted_workspace_id: str | None = None

    def _owner_ids(self) -> tuple[str, str]:
        execution = current_execution_context()
        if execution is not None:
            return execution.tenant_id, execution.workspace_id
        tenant = current_tenant()
        workspace = current_workspace()
        if tenant is not None and workspace is not None:
            return tenant.tenant_id, workspace.workspace_id
        if self._persisted_organization_id and self._persisted_workspace_id:
            return self._persisted_organization_id, self._persisted_workspace_id
        return "local", "local"

    def transition(self, nxt: RunStage, message: str, progress: float) -> None:
        assert_legal_transition(self.stage, nxt)
        if nxt is RunStage.PUBLISHING and (
            not self.readiness_path.exists()
            or json.loads(self.readiness_path.read_text(encoding="utf-8")).get("status") != "PASS"
        ):
            raise IllegalTransitionError("PUBLISHING requires a PASS readiness receipt.")
        if nxt is RunStage.EXPLORING:
            if not self.publish_path.exists():
                raise IllegalTransitionError(
                    "EXPLORING requires a verified BigQuery publish receipt."
                )
            publish = json.loads(self.publish_path.read_text(encoding="utf-8"))
            if publish.get("status") != "PUBLISHED" or publish.get("parity_status") != "PASS":
                raise IllegalTransitionError(
                    "EXPLORING requires a verified BigQuery publish receipt."
                )
        if nxt is RunStage.MODEL_READY:
            required = [
                self.publish_path,
                self.contract_path,
                self.provenance_path,
                self.readiness_path,
                self.model_ready_manifest_path,
                self.consumption_receipt_path,
                self.confirmation_path,
                self.eda_receipt_path,
                self.eda_html_path,
                self.eda_handoff_path,
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
        self.transition(RunStage.MAPPING, "Loading model intent and source inventory.", 0.3)
        if not self.intent_path.exists():
            self.fail("raw/model_intent.json is required.")
        intent = load_model_intent(json.loads(self.intent_path.read_text(encoding="utf-8")))
        self.inventory = inventory_assignment_sources(
            self.raw_dir,
            intent,
            dataset_id=self.dataset_id,
            dataset_role=self.dataset_role,
            assignment_id=self.run_id,
            business_name=self.business_name,
        )
        assert_required_sources_present(self.inventory)
        write_json_artifact(
            self.artifact_dir / "source_inventory_receipt.json",
            source_inventory_receipt(self.inventory),
        )

    def assess(self) -> list[Issue]:
        self.transition(RunStage.ASSESSING, "Detecting assignment issues.", 0.4)
        intent = load_model_intent(json.loads(self.intent_path.read_text(encoding="utf-8")))
        if self.inventory is None:
            self.inventory = inventory_assignment_sources(
                self.raw_dir,
                intent,
                dataset_id=self.dataset_id,
                dataset_role=self.dataset_role,
                assignment_id=self.run_id,
                business_name=self.business_name,
            )
        self.issues = detect_assignment_issues(self.raw_dir, intent, inventory=self.inventory)
        return self.issues

    def remediate(self) -> None:
        auto_safe = [
            issue for issue in self.issues if issue.remediation_class is RemediationClass.AUTO_SAFE
        ]
        if not auto_safe:
            if any(
                issue.remediation_class is not RemediationClass.AUTO_SAFE
                and issue.status != IssueStatus.RESOLVED
                for issue in self.issues
            ):
                self.transition(
                    RunStage.WAITING_FOR_APPROVAL,
                    "No AUTO_SAFE repairs; USER_REQUIRED issues remain.",
                    0.55,
                )
                return
            return
        self.transition(RunStage.REMEDIATING, "Applying AUTO_SAFE repairs.", 0.55)
        mark_issues_remediating(auto_safe)
        self._repair_sources_for_issues(auto_safe)
        transforms = (
            json.loads(self.manifest_path.read_text(encoding="utf-8")).get("transforms") or []
        )
        resolve_issues_from_transforms(auto_safe, transforms)
        unresolved_auto = [
            issue.issue_id
            for issue in auto_safe
            if issue.status != IssueStatus.RESOLVED
        ]
        if unresolved_auto:
            self.fail(f"Remediation did not resolve AUTO_SAFE issues: {unresolved_auto}")
        if any(
            issue.remediation_class is not RemediationClass.AUTO_SAFE
            and issue.status != IssueStatus.RESOLVED
            for issue in self.issues
        ):
            self.transition(
                RunStage.WAITING_FOR_APPROVAL,
                "AUTO_SAFE repairs applied; USER_REQUIRED issues remain.",
                0.6,
            )

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
        self._repair_sources_for_issues(accepted)
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
        org_id, workspace_id = self._owner_ids()
        return DurableRunState(
            run_id=self.run_id,
            organization_id=org_id,
            workspace_id=workspace_id,
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
            model_ready_manifest_uri=self._durable_uri(
                "model_ready_manifest.json", self.model_ready_manifest_path
            ),
            model_consumption_view=self.consumption_view,
            model_consumption_receipt_uri=self._durable_uri(
                "model_consumption_receipt.json", self.consumption_receipt_path
            ),
            model_ready_confirmation_receipt_uri=self._durable_uri(
                "model_ready_confirmation_receipt.json", self.confirmation_path
            ),
            meridian_eda_receipt_uri=self._durable_uri(
                "eda/meridian_eda_receipt.json", self.eda_receipt_path
            ),
            meridian_eda_report_uri=self._durable_uri(
                "eda/meridian_eda_report.html", self.eda_html_path
            ),
            meridian_eda_config_uri=self._durable_uri(
                "eda/meridian_eda_config.json", self.eda_config_path
            ),
            meridian_user_feedback_uri=self._durable_uri(
                "eda/meridian_user_feedback.json", self.eda_feedback_path
            ),
            m3_eda_analysis_uri=self._durable_uri(
                "eda/m3_eda_analysis.json", self.eda_analysis_path
            ),
            pre_modeling_handoff_uri=self._durable_uri(
                "eda/pre_modeling_handoff.md", self.eda_handoff_path
            ),
            physical_schema_fingerprint=self.physical_schema_fingerprint,
            status=self._status_label(),
            google_ready_relpath=self._relpath(self.google_ready),
            meta_ready_relpath=self._relpath(self.meta_ready),
            repaired_relpaths={
                key: self._relpath(value) or value for key, value in self.repaired_paths.items()
            },
            dataset_role=self.dataset_role,
            qualification_mode=self.qualification_mode,
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
        if state.repaired_relpaths:
            self.repaired_paths = {
                key: str(self.workspace / relative)
                for key, relative in state.repaired_relpaths.items()
            }
        self.dataset_role = state.dataset_role
        self.qualification_mode = state.qualification_mode
        self.consumption_view = state.model_consumption_view
        self.physical_schema_fingerprint = state.physical_schema_fingerprint
        self._persisted_organization_id = state.organization_id
        self._persisted_workspace_id = state.workspace_id
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
        if self.stage is RunStage.EXPLORING:
            return "EXPLORING"
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

    def _planned_uri(self, relative: str, path: Path) -> str:
        if self.durable_prefix:
            return f"{self.durable_prefix.rstrip('/')}/{relative}"
        return to_artifact_uri(path)

    def _eda_gcs_uri(self, relative: str) -> str:
        planned = self._planned_uri(relative, self.workspace / relative)
        if planned.startswith("gs://"):
            return planned
        if not settings.artifact_bucket:
            raise ValidationBlockedError(
                "Isolated Meridian EDA job requires MODELREADY_ARTIFACT_BUCKET."
            )
        execution = current_execution_context()
        if execution is not None:
            prefix = artifact_object_prefix_for_execution(execution).rstrip("/")
        else:
            org_id, workspace_id = self._owner_ids()
            prefix = legacy_run_artifact_prefix(org_id, workspace_id, self.run_id).rstrip("/")
        return f"gs://{settings.artifact_bucket}/{prefix}/{relative}"

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
        intent = load_model_intent(json.loads(self.intent_path.read_text(encoding="utf-8")))
        if self.inventory is None:
            self.inventory = inventory_assignment_sources(
                self.raw_dir,
                intent,
                dataset_id=self.dataset_id,
                dataset_role=self.dataset_role,
                assignment_id=self.run_id,
                business_name=self.business_name,
            )
        built = build_model_ready_frame_from_files(
            google_path=self._path_for_provider("google_ads") or self.google_ready,
            meta_path=self._path_for_provider("meta_ads") or self.meta_ready,
            shopify_path=self._path_for_role(CanonicalRole.KPI)
            or str(self.raw_dir / "shopify_weekly.csv"),
            ga4_path=self._path_for_provider("ga4") or str(self.raw_dir / "ga4_weekly.csv"),
            controls_path=self._path_for_role(CanonicalRole.CONTROLS)
            or str(self.raw_dir / "controls_weekly.csv"),
            population_path=self._path_for_role(CanonicalRole.POPULATION)
            or str(self.raw_dir / "geo_population.csv"),
            intent_json_path=str(self.intent_path),
            output_path=str(self.model_ready_path),
            inventory=self.inventory,
            repaired_paths=self.repaired_paths,
            raw_dir=str(self.raw_dir),
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
        intent = load_model_intent(json.loads(self.intent_path.read_text(encoding="utf-8")))
        frame = read_table(self.model_ready_path)
        artifact_fp = content_fingerprint(
            frame, columns=model_ready_columns(intent), key_columns=["time", "geo"]
        )
        contract = generate_meridian_input_contract_file(
            artifact_path=str(self.model_ready_path),
            intent_json_path=str(self.intent_path),
            run_id=self.run_id,
            table_id=sanitize_table_id(self.run_id),
            output_path=str(self.contract_path),
        )
        contract_obj = contract["contract"]
        schema = compile_model_consumption_schema(
            intent=intent,
            columns=list(frame.columns),
            table_description=f"ModelReady Meridian model-input artifact for run {self.run_id}.",
        )
        self.physical_schema_fingerprint = schema.physical_schema_fingerprint()
        provenance = self._load_json_if_exists(self.provenance_path) or {}
        readiness = self._load_json_if_exists(self.readiness_path) or {}
        meridian = MeridianInputContract.model_validate(contract_obj)
        org_id, workspace_id = self._owner_ids()
        manifest = compile_model_ready_manifest(
            run_id=self.run_id,
            organization_id=org_id,
            workspace_id=workspace_id,
            package_uri=self.package_uri or to_artifact_uri(self.raw_package),
            package_fingerprint=self.dataset_fp or "",
            intent=intent,
            frame=frame,
            issues=self.issues,
            provenance=provenance,
            readiness=readiness,
            meridian_contract=meridian,
            canonical_artifact_uri=self._durable_uri("model_ready.csv", self.model_ready_path)
            or to_artifact_uri(self.model_ready_path),
            canonical_artifact_fingerprint=artifact_fp,
            readiness_receipt_uri=self._durable_uri("readiness_report.json", self.readiness_path),
            transformation_manifest_uri=self._durable_uri(
                "transformation_manifest.json", self.manifest_path
            ),
            provenance_uri=self._durable_uri("provenance.json", self.provenance_path),
            meridian_contract_uri=self._durable_uri(
                "meridian_input_contract.json", self.contract_path
            ),
            schema=schema,
        )
        write_json_artifact(self.model_ready_manifest_path, manifest.model_dump(mode="json"))
        client = get_bigquery_client()
        table_id = sanitize_table_id(self.run_id)
        destination = write_bigquery_model_table(
            frame,
            project_id=settings.project_id,
            dataset_id=settings.bq_models_dataset,
            table_id=table_id,
            schema=schema,
            artifact_fingerprint=artifact_fp,
            client=client,
            labels=table_labels(self.run_id),
            intent=intent,
        )
        inspect_checks = inspect_model_destination(
            table_ref=destination,
            client=client,
            manifest=manifest,
            schema=schema,
            meridian_required_fields=_meridian_required_fields(meridian),
            expected_project=settings.project_id,
            expected_dataset=settings.bq_models_dataset,
            expected_table=table_id,
            expected_frame=frame,
        )
        receipt = validate_bigquery_publish_parity(
            local_frame=frame,
            table_ref=destination,
            run_id=self.run_id,
            project_id=settings.project_id,
            dataset_id=settings.bq_models_dataset,
            table_id=table_id,
            client=client,
            meridian_contract_uri=self._durable_uri(
                "meridian_input_contract.json", self.contract_path
            )
            or str(self.contract_path),
            provenance_uri=self._durable_uri("provenance.json", self.provenance_path)
            or str(self.provenance_path),
            extra_checks=inspect_checks,
            physical_schema_fingerprint=schema.physical_schema_fingerprint(),
            partition_field=schema.partition_field,
            clustering_fields=list(schema.clustering_fields),
        )
        write_json_artifact(self.publish_path, receipt.model_dump(mode="json"))
        return {
            "publish": receipt.model_dump(mode="json"),
            "contract": contract,
            "manifest": manifest.model_dump(mode="json"),
            "schema": schema.model_dump(mode="json"),
        }

    def run_meridian_eda(self) -> dict:
        publish = self._load_json_if_exists(self.publish_path)
        manifest_payload = self._load_json_if_exists(self.model_ready_manifest_path)
        contract = self._load_json_if_exists(self.contract_path)
        readiness = self._load_json_if_exists(self.readiness_path)
        provenance = self._load_json_if_exists(self.provenance_path)
        if not publish or not manifest_payload or not contract or not readiness:
            self.fail(
                "run_meridian_eda missing publish, manifest, contract, or readiness evidence."
            )
        if (readiness or {}).get("status") != "PASS":
            self.fail("run_meridian_eda requires a PASS readiness receipt.")
        if publish.get("status") != "PUBLISHED" or publish.get("parity_status") != "PASS":
            self.fail("run_meridian_eda requires a verified BigQuery publish receipt.")
        if contract.get("status") != "COMPLETE":
            self.fail("run_meridian_eda requires a COMPLETE Meridian input contract.")
        if not provenance:
            self.fail("run_meridian_eda requires provenance.")
        if self.stage is RunStage.PUBLISHING:
            self.transition(
                RunStage.EXPLORING,
                "Running official Meridian pre-modeling EDA.",
                0.92,
            )
        elif self.stage is not RunStage.EXPLORING:
            self.fail("run_meridian_eda requires PUBLISHING or EXPLORING.")
        manifest = ModelReadyManifest.model_validate(manifest_payload)
        meridian = MeridianInputContract.model_validate(contract)
        intent = load_model_intent(json.loads(self.intent_path.read_text(encoding="utf-8")))
        versioned_table = (
            f"{publish['project_id']}.{publish['dataset_id']}.{publish['table_id']}"
        )
        source = resolve_eda_source(
            consumption_view=self.consumption_view, versioned_table=versioned_table
        )
        client = get_bigquery_client()
        frame = coerce_model_frame_types(read_bigquery_table(source, client=client))
        fingerprint = assert_fingerprint_matches(
            frame, manifest.identity.canonical_artifact_fingerprint
        )
        html_uri = self._planned_uri("eda/meridian_eda_report.html", self.eda_html_path)
        config_uri = self._planned_uri("eda/meridian_eda_config.json", self.eda_config_path)
        request_uri = None
        receipt_uri = None
        if meridian_eda_job_configured():
            html_uri = self._eda_gcs_uri("eda/meridian_eda_report.html")
            config_uri = self._eda_gcs_uri("eda/meridian_eda_config.json")
            request_uri = self._eda_gcs_uri("eda/meridian_eda_request.json")
            receipt_uri = self._eda_gcs_uri("eda/meridian_eda_receipt.json")
        executed = execute_meridian_eda(
            run_id=self.run_id,
            frame=frame,
            intent=intent,
            contract=meridian,
            output_dir=self.eda_dir,
            source_endpoint=source,
            content_fingerprint=fingerprint,
            html_uri=html_uri,
            config_uri=config_uri,
            request_uri=request_uri,
            receipt_uri=receipt_uri,
        )
        receipt = executed["receipt"]
        write_json_artifact(self.eda_receipt_path, receipt.model_dump(mode="json"))
        return executed

    def complete(self, eda_analysis: dict | None = None) -> dict:
        if self.stage is not RunStage.EXPLORING:
            raise ValidationBlockedError(
                "complete_dataset_run requires stage EXPLORING after official Meridian EDA."
            )
        intent = load_model_intent(json.loads(self.intent_path.read_text(encoding="utf-8")))
        frame = read_table(self.model_ready_path)
        manifest_payload = self._load_json_if_exists(self.model_ready_manifest_path)
        publish = self._load_json_if_exists(self.publish_path)
        contract = self._load_json_if_exists(self.contract_path)
        if not manifest_payload or not publish or not contract:
            self.fail(
                "complete_dataset_run missing manifest, publish receipt, or Meridian contract."
            )
        if not self.eda_receipt_path.is_file() or not self.eda_html_path.is_file():
            self.fail("complete_dataset_run requires run_meridian_eda evidence.")
        eda_receipt_payload = self._load_json_if_exists(self.eda_receipt_path)
        eda_gate = evaluate_meridian_eda_gate(
            receipt=eda_receipt_payload or {},
            html_path=self.eda_html_path,
        )
        if eda_gate.get("status") != "PASS":
            self.fail(
                "EDA_BLOCKED: official Meridian EDA produced ERROR findings. "
                f"finding_ids={eda_gate.get('evidence', {}).get('error_finding_ids')}"
            )
        eda_receipt = MeridianEDAReceipt.model_validate(eda_receipt_payload)
        analysis = accept_eda_analysis(
            eda_analysis,
            eda_receipt,
            source_uri=self._planned_uri(
                "eda/meridian_eda_receipt.json", self.eda_receipt_path
            ),
        )
        write_json_artifact(self.eda_analysis_path, analysis.model_dump(mode="json"))
        manifest = ModelReadyManifest.model_validate(manifest_payload)
        meridian = MeridianInputContract.model_validate(contract)
        schema = compile_model_consumption_schema(
            intent=intent,
            meridian_contract=meridian,
            columns=list(frame.columns),
            table_description=f"ModelReady Meridian model-input artifact for run {self.run_id}.",
        )
        client = get_bigquery_client()
        versioned_table = (
            f"{publish['project_id']}.{publish['dataset_id']}.{publish['table_id']}"
        )
        candidate_checks = inspect_model_destination(
            table_ref=versioned_table,
            client=client,
            manifest=manifest,
            schema=schema,
            meridian_required_fields=_meridian_required_fields(meridian),
            expected_project=publish["project_id"],
            expected_dataset=publish["dataset_id"],
            expected_table=publish["table_id"],
            expected_frame=frame,
        )
        if not all_checks_passed(candidate_checks):
            self.fail(
                "Versioned BigQuery candidate failed post-write verification: "
                f"{candidate_checks}"
            )
        org_id, workspace_id = self._owner_ids()
        view_ref, view_id = consumption_view_ref(
            view_id=self.stable_view_id,
            organization_id=org_id,
            workspace_id=workspace_id,
        )
        try:
            promote_consumption_view(
                client=client,
                view_ref=view_ref,
                versioned_table=versioned_table,
                description=(
                    f"Stable Meridian model-consumption endpoint for {org_id}/{workspace_id}."
                ),
                schema=schema,
            )
        except Exception as exc:
            self.fail(f"Stable model-consumption view promotion failed: {exc}")
        self.consumption_view = view_ref
        try:
            view_checks = verify_consumption_view(
                client=client,
                view_ref=view_ref,
                versioned_table=versioned_table,
                manifest=manifest,
                schema=schema,
                expected_frame=frame,
                meridian_required_fields=_meridian_required_fields(meridian),
            )
        except Exception as exc:
            self.fail(f"Stable view verification failed: {exc}")
        if not all_checks_passed(view_checks):
            failed = [check.name for check in view_checks if not check.passed]
            self.fail(
                "Stable model-consumption view does not match the ModelReady Manifest: "
                f"{failed}"
            )
        confirmation_uri = self._planned_uri(
            "model_ready_confirmation_receipt.json", self.confirmation_path
        )
        registry_row = {
            "organization_id": org_id,
            "workspace_id": workspace_id,
            "run_id": self.run_id,
            "target_model": intent.target.value,
            "status": "MODEL_READY",
            "versioned_table": versioned_table,
            "consumption_view": view_ref,
            "package_fingerprint": self.dataset_fp,
            "artifact_fingerprint": manifest.identity.canonical_artifact_fingerprint,
            "published_fingerprint": publish.get("published_fingerprint"),
            "logical_schema_fingerprint": publish.get("schema_fingerprint"),
            "physical_schema_fingerprint": schema.physical_schema_fingerprint(),
            "row_count": manifest.output.row_count,
            "column_count": manifest.output.column_count,
            "model_ready_manifest_uri": self._durable_uri(
                "model_ready_manifest.json", self.model_ready_manifest_path
            ),
            "readiness_receipt_uri": self._durable_uri(
                "readiness_report.json", self.readiness_path
            ),
            "publish_receipt_uri": self._durable_uri("publish_receipt.json", self.publish_path),
            "meridian_contract_uri": self._durable_uri(
                "meridian_input_contract.json", self.contract_path
            ),
            "provenance_uri": self._durable_uri("provenance.json", self.provenance_path),
            "confirmation_receipt_uri": confirmation_uri,
        }
        try:
            upsert_model_ready_run(client=client, row=registry_row)
        except Exception as exc:
            self.fail(f"model_ready_runs registry write failed: {exc}")
        recorded = read_registry_row(
            client=client,
            organization_id=org_id,
            workspace_id=workspace_id,
            run_id=self.run_id,
            target_model=intent.target.value,
        )
        registry_count = count_registry_rows(
            client=client,
            organization_id=org_id,
            workspace_id=workspace_id,
            run_id=self.run_id,
            target_model=intent.target.value,
        )
        if recorded is None or registry_count != 1:
            self.fail("model_ready_runs registry row missing or duplicated.")
        view_fp = fingerprint_frame(read_bigquery_table(view_ref, client=client))
        consumption = build_consumption_receipt(
            run_id=self.run_id,
            target_model=intent.target.value,
            versioned_table=versioned_table,
            consumption_view=view_ref,
            schema=schema,
            actual_schema=inspect_table_schema_records(client.get_table(versioned_table)),
            expected_content_fingerprint=manifest.identity.canonical_artifact_fingerprint,
            versioned_fingerprint=publish.get("published_fingerprint") or "",
            view_fingerprint=view_fp,
            row_count=manifest.output.row_count,
            verification_checks=view_checks,
            registry_recorded=True,
        )
        write_json_artifact(self.consumption_receipt_path, consumption)
        if consumption["status"] != "PROMOTION_VERIFIED":
            self.fail("Model consumption receipt is not PROMOTION_VERIFIED.")
        detected, resolved, open_count = self._issue_counts()
        self.eda_dir.mkdir(parents=True, exist_ok=True)
        self.eda_handoff_path.write_text(
            render_pre_modeling_handoff(
                run_id=self.run_id,
                data_engineering={
                    "detected": detected,
                    "resolved": resolved,
                    "open": open_count,
                },
                model_input={
                    "endpoint": view_ref,
                    "fingerprint": manifest.identity.canonical_artifact_fingerprint,
                    "rows": manifest.output.row_count,
                    "columns": manifest.output.column_count,
                },
                destination={
                    "versioned_table": versioned_table,
                    "consumption_view": view_ref,
                    "physical_schema_status": "PASS",
                },
                receipt=eda_receipt,
                analysis=analysis,
                eda_gate=eda_gate,
            ),
            encoding="utf-8",
        )
        check_map = {item.name: item.passed for item in candidate_checks}
        confirmation_checks = {
            "validated_artifact_passed": (self._load_json_if_exists(self.readiness_path) or {}).get(
                "status"
            )
            == "PASS",
            "destination_exists": check_map.get("destination_exists", False),
            "row_count_matches": check_map.get("row_count_matches", False),
            "columns_match": check_map.get("column_names_match", False),
            "physical_schema_matches": check_map.get("physical_schema_matches", False),
            "grain_matches": check_map.get("grain_unique", False),
            "keys_match": check_map.get("key_set_matches", False),
            "nulls_match": check_map.get("null_policy_matches", False),
            "content_fingerprint_matches": check_map.get("content_fingerprint_matches", False),
            "meridian_contract_matches": meridian.status == "COMPLETE",
            "stable_view_matches": all_checks_passed(view_checks),
            "registry_recorded": True,
            "provenance_complete": bool(manifest.transformations),
            "partitioning_matches": check_map.get("partitioning", False),
            "clustering_matches": check_map.get("clustering", False),
            "column_descriptions_match": check_map.get("column_descriptions_match", False),
            "meridian_eda_complete": eda_receipt.status == "EDA_COMPLETE",
            "meridian_eda_html_persisted": self.eda_html_path.is_file()
            and self.eda_html_path.stat().st_size > 0,
            "meridian_eda_zero_errors": eda_gate.get("status") == "PASS",
            "meridian_eda_model_spec_disclosed": bool(
                (eda_gate.get("evidence") or {}).get("model_spec_source")
            ),
            "meridian_eda_not_approved_for_final_modeling": (
                not eda_receipt.model_spec.approved_for_final_modeling
                and not eda_receipt.prior_context.approved_for_final_modeling
            ),
            "meridian_eda_aks_disabled": eda_receipt.model_spec.enable_aks is False,
            "meridian_eda_data_adequacy_captured": bool(
                (eda_gate.get("evidence") or {}).get("data_adequacy_captured")
            ),
            "meridian_eda_knots_identifiable": bool(
                (eda_gate.get("evidence") or {}).get("knots_identifiable")
            ),
            "pre_modeling_handoff_persisted": self.eda_handoff_path.is_file(),
        }
        confirmation = build_confirmation_receipt(
            run_id=self.run_id,
            manifest_uri=self._durable_uri(
                "model_ready_manifest.json", self.model_ready_manifest_path
            )
            or to_artifact_uri(self.model_ready_manifest_path),
            versioned_table=versioned_table,
            consumption_view=view_ref,
            checks=confirmation_checks,
            target_model=intent.target.value,
        )
        write_json_artifact(self.confirmation_path, confirmation)
        meridian.promoted_model_source = MeridianSource(
            project_id=settings.project_id,
            dataset_id=settings.bq_models_dataset,
            table_id=view_id,
            object_type="VIEW",
        )
        meridian.source = meridian.promoted_model_source
        write_json_artifact(self.contract_path, meridian.model_dump(mode="json"))
        gate = evaluate_final_model_ready_gate(
            readiness=self.readiness_path,
            publish=self.publish_path,
            meridian_contract=self.contract_path,
            provenance=self.provenance_path,
            confirmation=self.confirmation_path,
            consumption=self.consumption_receipt_path,
            eda=self.eda_receipt_path,
            html_path=self.eda_html_path,
        )
        self.transition(RunStage.MODEL_READY, "Evidence-backed MODEL_READY.", 1.0)
        summary = self._write_summary(gate)
        return {"status": "MODEL_READY", "gate": gate, "summary": summary}

    def run_local(self) -> dict:
        self.prepare_workspace()
        self.profile_and_map()
        self.assess()
        self.remediate()
        self.write_issues()
        if self.stage is RunStage.WAITING_FOR_APPROVAL:
            return self._write_summary()
        if self.validation_blockers():
            self.transition(
                RunStage.WAITING_FOR_APPROVAL,
                "Validation blocked by unresolved USER_REQUIRED issues.",
                0.6,
            )
            return self._write_summary()
        self.validate_local()
        return self._write_summary()

    def run(self) -> dict:
        self.run_local()
        self.publish()
        self.run_meridian_eda()
        return self.complete()

    def _repair_sources_for_issues(self, issues: list[Issue]) -> None:
        intent = load_model_intent(json.loads(self.intent_path.read_text(encoding="utf-8")))
        if self.inventory is None:
            self.inventory = inventory_assignment_sources(
                self.raw_dir,
                intent,
                dataset_id=self.dataset_id,
                dataset_role=self.dataset_role,
                assignment_id=self.run_id,
                business_name=self.business_name,
            )
        targets = self._source_files_for_issues(issues)
        population = self._role_frame(CanonicalRole.POPULATION)
        inactivity = self._role_frame(CanonicalRole.INACTIVITY_EVIDENCE)
        for descriptor in self.inventory.sources:
            filename = Path(descriptor.relative_path).name
            if filename not in targets and descriptor.relative_path not in targets:
                if descriptor.canonical_role is CanonicalRole.INACTIVITY_EVIDENCE:
                    continue
                if descriptor.provider_id and any(
                    issue.proposed_action.get("provider_id") == descriptor.provider_id
                    for issue in issues
                ):
                    pass
                else:
                    continue
            if descriptor.canonical_role is CanonicalRole.MODEL_INTENT:
                continue
            if descriptor.canonical_role is CanonicalRole.INACTIVITY_EVIDENCE:
                continue
            source_path = str(self.raw_dir / descriptor.relative_path)
            repaired = repair_source_file(
                source_path=source_path,
                descriptor=descriptor,
                intent=intent,
                transform_dir=self.transform_dir,
                population=population,
                inactivity=inactivity,
            )
            self.repaired_paths[descriptor.relative_path] = repaired
            if descriptor.provider_id == "google_ads":
                self.google_ready = repaired
            if descriptor.provider_id == "meta_ads" and not descriptor.channel_hint:
                self.meta_ready = repaired
            elif descriptor.provider_id == "meta_ads" and not self.meta_ready:
                self.meta_ready = repaired

    def _source_files_for_issues(self, issues: list[Issue]) -> set[str]:
        names: set[str] = set()
        for issue in issues:
            evidence = issue.evidence or {}
            if evidence.get("file"):
                names.add(str(evidence["file"]))
            for filename in evidence.get("files") or []:
                names.add(str(filename))
            if issue.proposed_action.get("file"):
                names.add(str(issue.proposed_action["file"]))
        return names

    def _path_for_provider(self, provider_id: str) -> str | None:
        if self.inventory is None:
            return None
        for descriptor in self.inventory.sources_for_provider(provider_id):
            if descriptor.relative_path in self.repaired_paths:
                return self.repaired_paths[descriptor.relative_path]
            return str(self.raw_dir / descriptor.relative_path)
        return None

    def _path_for_role(self, role: CanonicalRole) -> str | None:
        if self.inventory is None:
            return None
        sources = self.inventory.sources_for_role(role)
        if not sources:
            return None
        descriptor = sources[0]
        if descriptor.relative_path in self.repaired_paths:
            return self.repaired_paths[descriptor.relative_path]
        return str(self.raw_dir / descriptor.relative_path)

    def _role_frame(self, role: CanonicalRole):
        path = self._path_for_role(role)
        if path is None:
            return None
        return read_table(path)

    def _write_summary(self, gate: dict | None = None) -> dict:
        detected, resolved, open_count = self._issue_counts()
        readiness = self._load_json_if_exists(self.readiness_path)
        publish = self._load_json_if_exists(self.publish_path)
        contract = self._load_json_if_exists(self.contract_path)
        provenance = self._load_json_if_exists(self.provenance_path)
        records = (provenance or {}).get("records") or (provenance or {}).get("transforms") or []
        summary = {
            "product": PRODUCT_NAME,
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
            "model_consumption": self._model_consumption_summary(publish),
            "meridian_eda": self._meridian_eda_summary(),
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
                "model_ready_manifest": self._durable_uri(
                    "model_ready_manifest.json", self.model_ready_manifest_path
                ),
                "model_consumption_receipt": self._durable_uri(
                    "model_consumption_receipt.json", self.consumption_receipt_path
                ),
                "model_ready_confirmation": self._durable_uri(
                    "model_ready_confirmation_receipt.json", self.confirmation_path
                ),
                "meridian_eda_receipt": self._durable_uri(
                    "eda/meridian_eda_receipt.json", self.eda_receipt_path
                ),
                "meridian_eda_report": self._durable_uri(
                    "eda/meridian_eda_report.html", self.eda_html_path
                ),
                "m3_eda_analysis": self._durable_uri(
                    "eda/m3_eda_analysis.json", self.eda_analysis_path
                ),
                "pre_modeling_handoff": self._durable_uri(
                    "eda/pre_modeling_handoff.md", self.eda_handoff_path
                ),
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
        columns = (
            list(MODEL_READY_COLUMNS)
            if all(column in frame.columns for column in MODEL_READY_COLUMNS)
            else list(frame.columns)
        )
        return {
            "path": self._durable_uri("model_ready.csv", self.model_ready_path),
            "row_count": int(len(frame)),
            "column_count": int(len(frame.columns)),
            "fingerprint": content_fingerprint(
                frame, columns=columns, key_columns=["time", "geo"]
            ),
        }

    def _meridian_eda_summary(self) -> dict:
        receipt = self._load_json_if_exists(self.eda_receipt_path) or {}
        severity = receipt.get("severity_summary") or {}
        return {
            "status": receipt.get("status"),
            "max_severity": severity.get("max_severity"),
            "error_count": severity.get("error_count"),
            "attention_count": severity.get("attention_count"),
            "info_count": severity.get("info_count"),
            "html_uri": self._durable_uri("eda/meridian_eda_report.html", self.eda_html_path),
            "receipt_uri": self._durable_uri(
                "eda/meridian_eda_receipt.json", self.eda_receipt_path
            ),
            "handoff_uri": self._durable_uri("eda/pre_modeling_handoff.md", self.eda_handoff_path),
            "review_recommended": bool((severity.get("attention_count") or 0) > 0),
            "model_spec": receipt.get("model_spec") or {},
            "data_adequacy": receipt.get("data_adequacy") or {},
            "user_feedback": self._load_json_if_exists(self.eda_feedback_path) or {},
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

    def _model_consumption_summary(self, publish: dict | None) -> dict:
        confirmation = self._load_json_if_exists(self.confirmation_path) or {}
        consumption = self._load_json_if_exists(self.consumption_receipt_path) or {}
        checks = {
            item.get("name"): item.get("passed")
            for item in (publish or {}).get("parity_checks") or []
        }
        return {
            "target": "google_meridian",
            "versioned_table": self._publish_destination(publish),
            "stable_view": self.consumption_view or consumption.get("consumption_view"),
            "physical_schema_status": "PASS" if checks.get("physical_schema_matches") else None,
            "content_status": "PASS" if checks.get("content_fingerprint_matches") else None,
            "stable_view_status": consumption.get("status"),
            "registry_status": "PASS" if consumption.get("registry_recorded") else None,
            "confirmation_status": confirmation.get("status"),
        }
