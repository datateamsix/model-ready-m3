"""Local in-process ADK Evaluation bridge proof."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path

from google.adk.agents import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from app.control_plane.entitlements import PlanId, entitlement_for_plan
from app.control_plane.memory import InMemoryControlPlaneRepository
from app.control_plane.models import EntitlementSource, EvaluationStatus, UploadStatus
from app.core.execution_context import bind_execution, current_execution_context
from app.core.run_repository import (
    LocalFilesystemRunRepository,
    bind_run_repository,
    reset_run_repository,
)
from app.core.tenancy import AuthState, TenantContext, bind_tenant, bind_workspace
from app.service.evaluation_executor import EvaluationExecutor
from app.service.evaluation_service import EvaluationService
from app.service.execution_from_evaluation import execution_context_from_evaluation
from app.service.object_store import FakeObjectStore
from app.service.upload_config import UploadConfig
from app.service.upload_service import UploadService
from app.service.upload_signing import FakeUploadSigner
from app.synthetic.paths import DATASET_A_DIR
from app.tools.run_tools import initialize_dataset_run as _real_initialize_dataset_run

DATASET_A_RAW = DATASET_A_DIR / "raw"


class _InitializeOnlyLlm(BaseLlm):
    """Deterministic ADK model: call initialize_dataset_run once, then stop."""

    model: str = "fake-bridge-llm"

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse]:
        del stream
        has_tool_result = False
        contents = getattr(llm_request, "contents", None) or []
        for content in contents:
            for part in getattr(content, "parts", None) or []:
                if getattr(part, "function_response", None) is not None:
                    has_tool_result = True
        if not has_tool_result:
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="initialize_dataset_run", args={}
                            )
                        )
                    ],
                )
            )
            return
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="initialized")],
            )
        )


def test_local_authorized_adk_bridge_calls_initialize_without_package_arg(
    tmp_path: Path,
) -> None:
    assert DATASET_A_RAW.is_dir()

    async def _run() -> None:
        control = InMemoryControlPlaneRepository()
        tenant = control.create_tenant(display_name="Bridge")
        control.put_entitlement_snapshot(
            entitlement_for_plan(
                tenant_id=tenant.tenant_id,
                plan_id=PlanId.PROJECT,
                source=EntitlementSource.MANUAL_GRANT,
            )
        )
        workspace = control.create_workspace_with_capacity(
            tenant_id=tenant.tenant_id, name="Bridge Project"
        )
        dataset = control.create_dataset(
            tenant_id=tenant.tenant_id,
            workspace_id=workspace.workspace_id,
            name="Dataset A",
        )

        store = FakeObjectStore()
        upload_service = UploadService(
            repo=control,
            config=UploadConfig(
                raw_bucket="test-raw-bucket",
                signed_url_ttl_seconds=900,
                max_files=20,
                max_file_bytes=50 * 1024 * 1024,
                max_total_bytes=200 * 1024 * 1024,
                runtime_sa=None,
            ),
            signer=FakeUploadSigner(),
            object_store=store,
        )
        evaluation_service = EvaluationService(repo=control)
        tenant_ctx = TenantContext(
            tenant_id=tenant.tenant_id,
            user_id="bridge-user",
            auth_state=AuthState.SERVICE,
            entitlement_snapshot_id=tenant.current_entitlement_snapshot_id,
        )

        package_files = sorted(p for p in DATASET_A_RAW.rglob("*") if p.is_file())
        with bind_tenant(tenant_ctx):
            upload, _signed = upload_service.create_upload(
                workspace_id=workspace.workspace_id,
                dataset_id=dataset.dataset_id,
                files=[
                    {
                        "filename": path.name,
                        "content_type": "application/json"
                        if path.suffix.lower() == ".json"
                        else "text/csv",
                        "size_bytes": path.stat().st_size,
                    }
                    for path in package_files
                ],
            )
            run_repo = LocalFilesystemRunRepository(
                root=tmp_path / "durable",
                raw_bucket="test-raw-bucket",
                artifact_bucket="test-artifact-bucket",
            )
            for file_rec, path in zip(upload.files, package_files, strict=True):
                data = path.read_bytes()
                store.put_bytes(
                    bucket="test-raw-bucket",
                    object_name=file_rec.object_name,
                    data=data,
                    content_type=file_rec.content_type,
                )
                target = run_repo.raw_root / file_rec.object_name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)

            verified = upload_service.complete_upload(
                workspace_id=workspace.workspace_id,
                dataset_id=dataset.dataset_id,
                upload_id=upload.upload_id,
            )
            assert verified.status is UploadStatus.VERIFIED
            assert verified.package_uri.endswith(upload.object_prefix)
            # Mirror verified FakeObjectStore contents (opaque + runtime presentation
            # names + manifest) into the local run repository raw root.
            for (bucket, object_name), record in store.objects.items():
                if bucket != "test-raw-bucket":
                    continue
                if not object_name.startswith(upload.object_prefix):
                    continue
                target = run_repo.raw_root / object_name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bytes(record["data"]))

            evaluation = evaluation_service.create_evaluation(
                workspace_id=workspace.workspace_id,
                dataset_id=dataset.dataset_id,
                upload_id=verified.upload_id,
            )
            assert evaluation.status is EvaluationStatus.ACCEPTED

            observed: list[dict] = []

            def initialize_dataset_run() -> dict:
                payload = _real_initialize_dataset_run()
                observed.append(payload)
                return payload

            agent = Agent(
                name="prem3_bridge_probe",
                model=_InitializeOnlyLlm(),
                instruction="Call initialize_dataset_run with no arguments.",
                tools=[initialize_dataset_run],
            )
            executor = EvaluationExecutor(repo=control, agent=agent)
            token = bind_run_repository(run_repo)
            try:
                result = await executor.execute_evaluation(evaluation.run_id)
            finally:
                reset_run_repository(token)

        assert observed, "initialize_dataset_run was not invoked through ADK"
        assert "run_id" in observed[0], observed[0]
        assert observed[0]["run_id"] == evaluation.run_id, observed[0]
        assert current_execution_context() is None
        assert result.run_id == evaluation.run_id

        service_tenant, workspace_ctx, execution = execution_context_from_evaluation(
            repo=control, evaluation=evaluation, tenant=tenant_ctx
        )
        with bind_tenant(service_tenant), bind_workspace(workspace_ctx), bind_execution(execution):
            assert run_repo.run_exists(evaluation.run_id)

    asyncio.run(_run())
