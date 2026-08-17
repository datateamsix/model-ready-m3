"""Server-owned PreM3 resource identifier generation.

Provider IDs (Clerk, Stripe) must never be embedded. Generated values satisfy
``validate_resource_identifier`` so they may later appear in GCS path segments.
"""

from __future__ import annotations

from uuid import uuid4

from app.core.identifiers import validate_resource_identifier


def _opaque(prefix: str) -> str:
    # Prefix + 20 hex chars stays well under the 128-char identifier limit.
    value = f"{prefix}_{uuid4().hex[:20]}"
    return validate_resource_identifier(value, field="resource_id")


def new_tenant_id() -> str:
    return _opaque("ten")


def new_workspace_id() -> str:
    return _opaque("wsp")


def new_dataset_id() -> str:
    return _opaque("dset")


def new_entitlement_snapshot_id() -> str:
    return _opaque("ent")
