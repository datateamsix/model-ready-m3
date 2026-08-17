"""Trusted test binders for repository operations. Not a registered ADK tool."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from app.core.execution_context import bind_service_execution


@contextmanager
def bind_run_authority(
    *,
    tenant_id: str,
    run_id: str,
    workspace_id: str = "mmm-demo",
    package_uri: str = "gs://raw/internal/package/",
    dataset_id: str = "internal-dataset",
) -> Iterator[None]:
    with bind_service_execution(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        run_id=run_id,
        dataset_id=dataset_id,
        package_uri=package_uri,
    ):
        yield
