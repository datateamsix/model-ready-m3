#!/usr/bin/env python3
"""Qualify Cloud signed Dataset upload + Evaluation resource creation.

NEVER invoked by pytest/CI. Explicit operator command only.

Uses m3-runtime impersonation against Firestore + GCS (synthetic control-plane
tenant). Does NOT call root_agent and does NOT use FastAPI BackgroundTasks.

Proves:
  create upload → V4 signed PUT → complete/verify → generation freeze → Evaluation
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google.auth import default as google_auth_default
from google.auth import impersonated_credentials
from google.cloud import firestore, storage

from app.control_plane.entitlements import PlanId, entitlement_for_plan
from app.control_plane.firestore_repo import FirestoreControlPlaneRepository
from app.control_plane.models import EntitlementSource, EvaluationStatus, UploadStatus
from app.core.tenancy import AuthState, TenantContext, bind_tenant
from app.service.evaluation_service import EvaluationService
from app.service.object_store import GcsObjectStore
from app.service.upload_config import UploadConfig
from app.service.upload_service import UploadService
from app.service.upload_signing import GcsV4UploadSigner

PROJECT = "modelready-m3"
RUNTIME_SA = f"m3-runtime@{PROJECT}.iam.gserviceaccount.com"
RAW_BUCKET = "modelready-m3-912257136465-raw"
REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPO_ROOT / "artifacts" / "deployment" / "prem3_api_cloud_proof.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument(
        "--impersonate-service-account",
        default=RUNTIME_SA,
        help="Service account to impersonate (empty string disables impersonation).",
    )
    args = parser.parse_args(argv)
    if not args.execute:
        print("CLOUD_SIGNED_UPLOAD_NOT_RUN")
        print("Pass --execute to qualify signed upload + Evaluation creation.")
        return 2

    source, _ = google_auth_default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    target = (args.impersonate_service_account or "").strip()
    if target:
        creds = impersonated_credentials.Credentials(
            source_credentials=source,
            target_principal=target,
            target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
            lifetime=3600,
        )
        identity = target
    else:
        creds = source
        identity = "application-default-credentials"
    print(f"identity={identity}")
    db = firestore.Client(project=PROJECT, database="(default)", credentials=creds)
    gcs = storage.Client(project=PROJECT, credentials=creds)
    repo = FirestoreControlPlaneRepository(db)
    store = GcsObjectStore(client=gcs)
    signer = GcsV4UploadSigner(client=gcs)
    runtime_sa = target or RUNTIME_SA
    upload_service = UploadService(
        repo=repo,
        config=UploadConfig(
            raw_bucket=RAW_BUCKET,
            signed_url_ttl_seconds=900,
            max_files=5,
            max_file_bytes=1024 * 1024,
            max_total_bytes=2 * 1024 * 1024,
            runtime_sa=runtime_sa,
        ),
        signer=signer,
        object_store=store,
    )
    evaluation_service = EvaluationService(repo=repo)

    tenant = None
    upload_id = None
    object_prefix = None
    run_id = None
    try:
        tenant = repo.create_tenant(display_name="Signed Upload Qualify")
        repo.put_entitlement_snapshot(
            entitlement_for_plan(
                tenant_id=tenant.tenant_id,
                plan_id=PlanId.PROJECT,
                source=EntitlementSource.MANUAL_GRANT,
            )
        )
        workspace = repo.create_workspace_with_capacity(
            tenant_id=tenant.tenant_id, name="Qualify Workspace"
        )
        dataset = repo.create_dataset(
            tenant_id=tenant.tenant_id,
            workspace_id=workspace.workspace_id,
            name="Qualify Dataset",
        )
        payload = b"date,value\n2024-01-01,1\n"
        tenant_ctx = TenantContext(
            tenant_id=tenant.tenant_id,
            user_id="qualify-operator",
            auth_state=AuthState.SERVICE,
            entitlement_snapshot_id=tenant.current_entitlement_snapshot_id,
        )
        with bind_tenant(tenant_ctx):
            upload, signed = upload_service.create_upload(
                workspace_id=workspace.workspace_id,
                dataset_id=dataset.dataset_id,
                files=[
                    {
                        "filename": "qualify.csv",
                        "content_type": "text/csv",
                        "size_bytes": len(payload),
                    }
                ],
            )
            upload_id = upload.upload_id
            object_prefix = upload.object_prefix
            assert signed and signed[0].method == "PUT"
            put_status = _put_signed(signed[0].url, payload, signed[0].headers)
            if put_status not in {200, 201}:
                raise RuntimeError(f"Signed PUT failed with HTTP {put_status}")
            verified = upload_service.complete_upload(
                workspace_id=workspace.workspace_id,
                dataset_id=dataset.dataset_id,
                upload_id=upload.upload_id,
            )
            if verified.status is not UploadStatus.VERIFIED:
                raise RuntimeError(f"Upload status={verified.status}")
            if not verified.files[0].generation:
                raise RuntimeError("Verified upload missing generation")
            evaluation = evaluation_service.create_evaluation(
                workspace_id=workspace.workspace_id,
                dataset_id=dataset.dataset_id,
                upload_id=verified.upload_id,
            )
            if evaluation.status is not EvaluationStatus.ACCEPTED:
                raise RuntimeError(f"Evaluation status={evaluation.status}")
            run_id = evaluation.run_id
            if not run_id.startswith("run_"):
                raise RuntimeError("run_id was not server-generated")

        evidence = {
            "proof": "CLOUD_SIGNED_UPLOAD",
            "at": datetime.now(UTC).isoformat(),
            "tenant_id": tenant.tenant_id,
            "upload_id": upload_id,
            "run_id": run_id,
            "generation": verified.files[0].generation,
            "package_fingerprint": verified.package_fingerprint,
            "raw_bucket": RAW_BUCKET,
            "runtime_sa": RUNTIME_SA,
            "put_status": put_status,
            "agent_executed": False,
        }
        print("CLOUD_SIGNED_UPLOAD=true")
        print(f"upload_id={upload_id}")
        print(f"run_id={run_id}")
        print(f"generation={verified.files[0].generation}")
        if args.write_evidence:
            _merge_evidence(evidence)
        return 0
    finally:
        cleaned_objects = 0
        if object_prefix:
            cleaned_objects = store.delete_prefix(bucket=RAW_BUCKET, prefix=object_prefix)
        cleaned_docs: list[str] = []
        if tenant is not None:
            cleaned_docs = repo.delete_document_tree_for_qualification(tenant.tenant_id)
        print(f"cleanup_objects={cleaned_objects}")
        print(f"cleanup_docs={len(cleaned_docs)}")


def _put_signed(url: str, body: bytes, headers: dict[str, str]) -> int:
    request = urllib.request.Request(url, data=body, method="PUT", headers=dict(headers))
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def _merge_evidence(payload: dict[str, Any]) -> None:
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if EVIDENCE_PATH.is_file():
        existing = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    existing["CLOUD_SIGNED_UPLOAD"] = payload
    EVIDENCE_PATH.write_text(json.dumps(existing, indent=2, sort_keys=True), encoding="utf-8")
    print(f"evidence={EVIDENCE_PATH}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — operator script terminal reporting
        print("CLOUD_SIGNED_UPLOAD=false")
        print(f"error={exc}")
        sys.exit(1)
