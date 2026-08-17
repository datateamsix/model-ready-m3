"""Factory helpers for prem3-api tests. No GCP, Clerk, or Stripe."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.control_plane.entitlements import PlanId, entitlement_for_plan
from app.control_plane.memory import InMemoryControlPlaneRepository
from app.control_plane.models import (
    EntitlementSource,
    IdentityProvider,
    IdentityProviderOrganizationMapping,
    MembershipProjection,
    MembershipStatus,
)
from app.service.app import create_app
from app.service.auth import FakeIdentityVerifier, VerifiedIdentity
from app.service.billing import UnavailableBillingGateway
from app.service.catalog import build_plan_catalog


def now() -> datetime:
    return datetime.now(UTC)


def seed_tenant(
    repo: InMemoryControlPlaneRepository,
    *,
    display_name: str = "Acme",
    provider_org: str = "org_acme",
    provider_user: str = "user_acme",
    plan_id: str = PlanId.PLANNER,
    membership_status: MembershipStatus = MembershipStatus.ACTIVE,
):
    mapping = IdentityProviderOrganizationMapping(
        provider=IdentityProvider.CLERK,
        provider_organization_id=provider_org,
        tenant_id="placeholder",
        created_at=now(),
        updated_at=now(),
    )
    tenant = repo.create_tenant(display_name=display_name, identity_mapping=mapping)
    if plan_id != PlanId.PLANNER:
        repo.put_entitlement_snapshot(
            entitlement_for_plan(
                tenant_id=tenant.tenant_id,
                plan_id=plan_id,
                source=EntitlementSource.MANUAL_GRANT,
            )
        )
    repo.upsert_membership_projection(
        MembershipProjection(
            tenant_id=tenant.tenant_id,
            provider=IdentityProvider.CLERK,
            provider_user_id=provider_user,
            provider_organization_id=provider_org,
            role="member",
            status=membership_status,
            updated_at=now(),
        )
    )
    identity = VerifiedIdentity(
        provider="clerk",
        provider_user_id=provider_user,
        provider_organization_id=provider_org,
    )
    return tenant, identity


def make_client(
    *,
    repo: InMemoryControlPlaneRepository | None = None,
    identity: VerifiedIdentity | None = None,
    identities: dict[str, VerifiedIdentity] | None = None,
    billing=None,
    catalog=None,
    unconfigured_auth: bool = False,
) -> tuple[TestClient, InMemoryControlPlaneRepository]:
    repository = repo or InMemoryControlPlaneRepository()
    if unconfigured_auth:
        verifier = None
    else:
        verifier = FakeIdentityVerifier(default=identity, identities=identities)
    app = create_app(
        control_plane_repository=repository,
        identity_verifier=verifier,
        billing_gateway=billing if billing is not None else UnavailableBillingGateway(),
        plan_catalog=catalog or build_plan_catalog(checkout_eligible=False),
    )
    return TestClient(app, raise_server_exceptions=False), repository


def auth_header(token: str = "test-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
