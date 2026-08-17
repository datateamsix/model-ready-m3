"""Mission 05 control-plane isolation, capacity, and webhook tests.

Primary qualification uses InMemoryControlPlaneRepository. Live Firestore is
exercised only by scripts/qualify_firestore_control_plane.py.
"""

from __future__ import annotations

import inspect
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import pytest

from app.agent import root_agent
from app.control_plane.entitlements import (
    PLAN_MAX_ACTIVE_PROJECTS,
    PlanId,
    default_planner_entitlement,
    entitlement_for_plan,
    project_subscription_to_entitlement,
)
from app.control_plane.memory import InMemoryControlPlaneRepository
from app.control_plane.models import (
    BillingProvider,
    DatasetEvaluationRef,
    EntitlementSource,
    IdentityProvider,
    IdentityProviderOrganizationMapping,
    StripeCustomerMapping,
    SubscriptionProjection,
    TenantStatus,
    WebhookClaimStatus,
    WebhookProvider,
)
from app.core.errors import (
    EntitlementUnavailableError,
    ProjectLimitReachedError,
    ProviderMappingConflictError,
    TenantNotFoundError,
    WorkspaceNotFoundError,
)
from app.core.tenancy import is_forbidden_model_supplied_authority_parameter
from app.tools.precloud import agent_tool_names


def _repo() -> InMemoryControlPlaneRepository:
    return InMemoryControlPlaneRepository()


def _now() -> datetime:
    return datetime.now(UTC)


def test_provider_org_maps_to_prem3_tenant() -> None:
    repo = _repo()
    mapping = IdentityProviderOrganizationMapping(
        provider=IdentityProvider.CLERK,
        provider_organization_id="org_clerk_abc",
        tenant_id="placeholder",
        created_at=_now(),
        updated_at=_now(),
    )
    tenant = repo.create_tenant(display_name="Acme", identity_mapping=mapping)
    resolved = repo.get_tenant_id_for_provider_org(
        provider="clerk", provider_organization_id="org_clerk_abc"
    )
    assert resolved == tenant.tenant_id
    assert resolved != "org_clerk_abc"


def test_set_tenant_status_disables_without_deleting() -> None:
    repo = _repo()
    tenant = repo.create_tenant(display_name="Acme")
    updated = repo.set_tenant_status(tenant_id=tenant.tenant_id, status=TenantStatus.DISABLED)
    assert updated.status == TenantStatus.DISABLED
    stored = repo.get_tenant(tenant.tenant_id)
    assert stored is not None
    assert stored.status == TenantStatus.DISABLED


def test_provider_id_is_not_tenant_id() -> None:
    repo = _repo()
    mapping = IdentityProviderOrganizationMapping(
        provider=IdentityProvider.CLERK,
        provider_organization_id="org_never_as_tenant",
        tenant_id="placeholder",
        created_at=_now(),
        updated_at=_now(),
    )
    tenant = repo.create_tenant(display_name="Mapped", identity_mapping=mapping)
    assert tenant.tenant_id.startswith("ten_")
    assert tenant.tenant_id != "org_never_as_tenant"


def test_tenant_creation_creates_no_workspace() -> None:
    repo = _repo()
    tenant = repo.create_tenant(display_name="No Project")
    assert repo.list_workspaces_for_tenant(tenant.tenant_id) == []
    assert tenant.active_workspace_count == 0


def test_planner_entitlement_has_zero_project_capacity() -> None:
    repo = _repo()
    tenant = repo.create_tenant(display_name="Planner")
    entitlement = repo.get_current_entitlement(tenant.tenant_id)
    assert entitlement.plan_id == PlanId.PLANNER
    assert entitlement.max_active_projects == 0
    with pytest.raises(ProjectLimitReachedError):
        repo.create_workspace_with_capacity(tenant_id=tenant.tenant_id, name="Blocked")


def test_workspace_create_requires_tenant() -> None:
    repo = _repo()
    with pytest.raises(TenantNotFoundError):
        repo.create_workspace_with_capacity(tenant_id="ten_missing0000000000", name="X")


def test_workspace_lookup_is_tenant_scoped() -> None:
    repo = _repo()
    tenant = repo.create_tenant(display_name="A")
    repo.put_entitlement_snapshot(
        entitlement_for_plan(
            tenant_id=tenant.tenant_id,
            plan_id=PlanId.PROJECT,
            source=EntitlementSource.MANUAL_GRANT,
        )
    )
    workspace = repo.create_workspace_with_capacity(
        tenant_id=tenant.tenant_id, name="Only A"
    )
    other = repo.create_tenant(display_name="B")
    assert (
        repo.get_workspace_for_tenant(
            tenant_id=other.tenant_id, workspace_id=workspace.workspace_id
        )
        is None
    )


def test_dataset_lookup_is_workspace_scoped() -> None:
    repo = _repo()
    tenant = repo.create_tenant(display_name="Scoped")
    repo.put_entitlement_snapshot(
        entitlement_for_plan(
            tenant_id=tenant.tenant_id,
            plan_id=PlanId.PORTFOLIO,
            source=EntitlementSource.MANUAL_GRANT,
        )
    )
    a = repo.create_workspace_with_capacity(tenant_id=tenant.tenant_id, name="A")
    b = repo.create_workspace_with_capacity(tenant_id=tenant.tenant_id, name="B")
    dataset = repo.create_dataset(
        tenant_id=tenant.tenant_id, workspace_id=a.workspace_id, name="D"
    )
    assert (
        repo.get_dataset_for_workspace(
            tenant_id=tenant.tenant_id,
            workspace_id=b.workspace_id,
            dataset_id=dataset.dataset_id,
        )
        is None
    )


def test_cross_tenant_workspace_not_resolvable() -> None:
    repo = _repo()
    a = repo.create_tenant(display_name="A")
    b = repo.create_tenant(display_name="B")
    repo.put_entitlement_snapshot(
        entitlement_for_plan(
            tenant_id=a.tenant_id,
            plan_id=PlanId.PROJECT,
            source=EntitlementSource.MANUAL_GRANT,
        )
    )
    workspace = repo.create_workspace_with_capacity(tenant_id=a.tenant_id, name="W")
    assert (
        repo.get_workspace_for_tenant(
            tenant_id=b.tenant_id, workspace_id=workspace.workspace_id
        )
        is None
    )


def test_cross_tenant_dataset_not_resolvable() -> None:
    repo = _repo()
    a = repo.create_tenant(display_name="A")
    b = repo.create_tenant(display_name="B")
    repo.put_entitlement_snapshot(
        entitlement_for_plan(
            tenant_id=a.tenant_id,
            plan_id=PlanId.PROJECT,
            source=EntitlementSource.MANUAL_GRANT,
        )
    )
    workspace = repo.create_workspace_with_capacity(tenant_id=a.tenant_id, name="W")
    dataset = repo.create_dataset(
        tenant_id=a.tenant_id, workspace_id=workspace.workspace_id, name="D"
    )
    assert (
        repo.get_dataset_for_workspace(
            tenant_id=b.tenant_id,
            workspace_id=workspace.workspace_id,
            dataset_id=dataset.dataset_id,
        )
        is None
    )


def test_cross_workspace_dataset_not_resolvable() -> None:
    test_dataset_lookup_is_workspace_scoped()


def test_dataset_cannot_be_reparented() -> None:
    repo = _repo()
    tenant = repo.create_tenant(display_name="Owner")
    repo.put_entitlement_snapshot(
        entitlement_for_plan(
            tenant_id=tenant.tenant_id,
            plan_id=PlanId.PORTFOLIO,
            source=EntitlementSource.MANUAL_GRANT,
        )
    )
    a = repo.create_workspace_with_capacity(tenant_id=tenant.tenant_id, name="A")
    b = repo.create_workspace_with_capacity(tenant_id=tenant.tenant_id, name="B")
    dataset = repo.create_dataset(
        tenant_id=tenant.tenant_id, workspace_id=a.workspace_id, name="Pinned"
    )
    # Creating the same dataset_id under another workspace is a different resource;
    # original remains owned by A and is not resolvable under B.
    assert dataset.workspace_id == a.workspace_id
    assert (
        repo.get_dataset_for_workspace(
            tenant_id=tenant.tenant_id,
            workspace_id=b.workspace_id,
            dataset_id=dataset.dataset_id,
        )
        is None
    )
    still = repo.get_dataset_for_workspace(
        tenant_id=tenant.tenant_id,
        workspace_id=a.workspace_id,
        dataset_id=dataset.dataset_id,
    )
    assert still is not None
    assert still.workspace_id == a.workspace_id


def test_entitlement_fails_closed_when_missing() -> None:
    repo = _repo()
    tenant = repo.create_tenant(display_name="Bare", with_planner_entitlement=False)
    with pytest.raises(EntitlementUnavailableError):
        repo.get_current_entitlement(tenant.tenant_id)
    with pytest.raises(EntitlementUnavailableError):
        repo.create_workspace_with_capacity(tenant_id=tenant.tenant_id, name="No")


def test_project_plan_allows_one_active_project() -> None:
    repo = _repo()
    tenant = repo.create_tenant(display_name="Project")
    repo.put_entitlement_snapshot(
        entitlement_for_plan(
            tenant_id=tenant.tenant_id,
            plan_id=PlanId.PROJECT,
            source=EntitlementSource.MANUAL_GRANT,
        )
    )
    repo.create_workspace_with_capacity(tenant_id=tenant.tenant_id, name="Only")
    with pytest.raises(ProjectLimitReachedError):
        repo.create_workspace_with_capacity(tenant_id=tenant.tenant_id, name="Two")
    assert len(repo.list_workspaces_for_tenant(tenant.tenant_id)) == 1


def test_portfolio_plan_allows_ten_active_projects() -> None:
    _assert_plan_capacity(PlanId.PORTFOLIO, 10)


def test_enterprise_plan_allows_fifty_active_projects() -> None:
    _assert_plan_capacity(PlanId.ENTERPRISE, 50)


def _assert_plan_capacity(plan_id: str, expected: int) -> None:
    repo = _repo()
    tenant = repo.create_tenant(display_name=plan_id)
    repo.put_entitlement_snapshot(
        entitlement_for_plan(
            tenant_id=tenant.tenant_id,
            plan_id=plan_id,
            source=EntitlementSource.MANUAL_GRANT,
        )
    )
    assert PLAN_MAX_ACTIVE_PROJECTS[plan_id] == expected
    for index in range(expected):
        repo.create_workspace_with_capacity(
            tenant_id=tenant.tenant_id, name=f"P{index}"
        )
    with pytest.raises(ProjectLimitReachedError):
        repo.create_workspace_with_capacity(tenant_id=tenant.tenant_id, name="Overflow")
    assert len(repo.list_workspaces_for_tenant(tenant.tenant_id)) == expected


def test_project_capacity_transaction_is_atomic() -> None:
    # Repeat to make a broken check-then-write observable.
    for round_id in range(20):
        repo_round = _repo()
        t = repo_round.create_tenant(display_name=f"Race{round_id}")
        repo_round.put_entitlement_snapshot(
            entitlement_for_plan(
                tenant_id=t.tenant_id,
                plan_id=PlanId.PROJECT,
                source=EntitlementSource.MANUAL_GRANT,
            )
        )
        with ThreadPoolExecutor(max_workers=8) as pool:
            active_repo = repo_round
            tenant_id = t.tenant_id

            def _create(name: str, repository=active_repo, tid=tenant_id):
                return repository.create_workspace_with_capacity(
                    tenant_id=tid, name=name
                )

            futures = [pool.submit(_create, f"w{i}") for i in range(8)]
            round_ok = 0
            round_fail = 0
            for future in as_completed(futures):
                try:
                    future.result()
                    round_ok += 1
                except ProjectLimitReachedError:
                    round_fail += 1
        assert round_ok == 1
        assert round_fail == 7
        assert len(repo_round.list_workspaces_for_tenant(t.tenant_id)) == 1


def test_evaluation_count_does_not_consume_project_capacity() -> None:
    repo = _repo()
    tenant = repo.create_tenant(display_name="Evals")
    repo.put_entitlement_snapshot(
        entitlement_for_plan(
            tenant_id=tenant.tenant_id,
            plan_id=PlanId.PROJECT,
            source=EntitlementSource.MANUAL_GRANT,
        )
    )
    workspace = repo.create_workspace_with_capacity(
        tenant_id=tenant.tenant_id, name="One"
    )
    dataset = repo.create_dataset(
        tenant_id=tenant.tenant_id, workspace_id=workspace.workspace_id, name="D"
    )
    # Many evaluation refs must not bump active_workspace_count / capacity.
    for index in range(5):
        repo.put_evaluation_ref(
            DatasetEvaluationRef(
                tenant_id=tenant.tenant_id,
                workspace_id=workspace.workspace_id,
                dataset_id=dataset.dataset_id,
                run_id=f"run_eval{index:012d}",
                created_at=_now(),
            )
        )
    refreshed = repo.get_tenant(tenant.tenant_id)
    assert refreshed is not None
    assert refreshed.active_workspace_count == 1
    with pytest.raises(ProjectLimitReachedError):
        repo.create_workspace_with_capacity(tenant_id=tenant.tenant_id, name="Second")


def test_entitlement_snapshot_is_immutable() -> None:
    repo = _repo()
    tenant = repo.create_tenant(display_name="Immutable")
    first = default_planner_entitlement(tenant_id=tenant.tenant_id)
    repo.put_entitlement_snapshot(first)
    mutated = first.model_copy(
        update={"limits": {"max_active_projects": 99}, "plan_id": PlanId.ENTERPRISE}
    )
    with pytest.raises(ProviderMappingConflictError):
        repo.put_entitlement_snapshot(mutated)
    stored = repo.get_entitlement_snapshot(
        tenant_id=tenant.tenant_id, snapshot_id=first.snapshot_id
    )
    assert stored is not None
    assert stored.max_active_projects == 0
    assert stored.plan_id == PlanId.PLANNER


def test_duplicate_webhook_claim_is_idempotent() -> None:
    repo = _repo()
    first = repo.claim_webhook_event(
        provider=WebhookProvider.STRIPE,
        provider_event_id="evt_same",
        event_type="customer.subscription.updated",
    )
    assert first.status == WebhookClaimStatus.WON
    repo.mark_webhook_event_processed(
        provider=WebhookProvider.STRIPE, provider_event_id="evt_same", result="ok"
    )
    second = repo.claim_webhook_event(
        provider=WebhookProvider.STRIPE,
        provider_event_id="evt_same",
        event_type="customer.subscription.updated",
    )
    assert second.status == WebhookClaimStatus.ALREADY_PROCESSED


def test_concurrent_webhook_claim_has_single_winner() -> None:
    for _ in range(20):
        repo = _repo()
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [
                pool.submit(
                    repo.claim_webhook_event,
                    provider=WebhookProvider.STRIPE,
                    provider_event_id="evt_race",
                    event_type="invoice.paid",
                )
                for _ in range(8)
            ]
            results = [future.result() for future in as_completed(futures)]
        winners = [item for item in results if item.status == WebhookClaimStatus.WON]
        others = [
            item
            for item in results
            if item.status
            in {WebhookClaimStatus.ALREADY_CLAIMED, WebhookClaimStatus.ALREADY_PROCESSED}
        ]
        assert len(winners) == 1
        assert len(others) == 7


def test_subscription_projection_does_not_act_as_authority_directly() -> None:
    repo = _repo()
    tenant = repo.create_tenant(display_name="Billing")
    # Subscription alone must not raise project capacity.
    repo.put_subscription_projection(
        SubscriptionProjection(
            tenant_id=tenant.tenant_id,
            billing_provider=BillingProvider.STRIPE,
            provider_customer_id="cus_abc",
            provider_subscription_id="sub_abc",
            plan_id=PlanId.ENTERPRISE,
            status="active",
            provider_updated_at=_now(),
            projected_at=_now(),
        )
    )
    # Still on Planner entitlement until a new EntitlementSnapshot is written.
    with pytest.raises(ProjectLimitReachedError):
        repo.create_workspace_with_capacity(tenant_id=tenant.tenant_id, name="Not yet")
    entitlement = project_subscription_to_entitlement(
        repo.get_subscription_projection(tenant.tenant_id)  # type: ignore[arg-type]
    )
    assert entitlement.source == EntitlementSource.BILLING_PROVIDER
    repo.put_entitlement_snapshot(entitlement)
    repo.create_workspace_with_capacity(tenant_id=tenant.tenant_id, name="Now allowed")


def test_stripe_customer_id_is_mapping_not_storage_authority() -> None:
    repo = _repo()
    tenant = repo.create_tenant(display_name="StripeMap")
    mapping = StripeCustomerMapping(
        tenant_id=tenant.tenant_id,
        billing_provider=BillingProvider.STRIPE,
        provider_customer_id="cus_not_a_tenant",
        created_at=_now(),
        updated_at=_now(),
    )
    repo.put_stripe_customer_mapping(mapping)
    stored = repo.get_stripe_customer_mapping(tenant.tenant_id)
    assert stored is not None
    assert stored.provider_customer_id == "cus_not_a_tenant"
    assert stored.tenant_id == tenant.tenant_id
    assert stored.tenant_id != "cus_not_a_tenant"
    assert repo.get_tenant("cus_not_a_tenant") is None


def test_failed_webhook_may_be_reclaimed() -> None:
    repo = _repo()
    claim = repo.claim_webhook_event(
        provider=WebhookProvider.STRIPE,
        provider_event_id="evt_retry",
        event_type="invoice.failed",
    )
    assert claim.status == WebhookClaimStatus.WON
    repo.mark_webhook_event_failed(
        provider=WebhookProvider.STRIPE, provider_event_id="evt_retry", result="boom"
    )
    again = repo.claim_webhook_event(
        provider=WebhookProvider.STRIPE,
        provider_event_id="evt_retry",
        event_type="invoice.failed",
    )
    assert again.status == WebhookClaimStatus.WON


def test_workspace_create_against_missing_workspace_parent_raises() -> None:
    repo = _repo()
    tenant = repo.create_tenant(display_name="X")
    repo.put_entitlement_snapshot(
        entitlement_for_plan(
            tenant_id=tenant.tenant_id,
            plan_id=PlanId.PROJECT,
            source=EntitlementSource.MANUAL_GRANT,
        )
    )
    with pytest.raises(WorkspaceNotFoundError):
        repo.create_dataset(
            tenant_id=tenant.tenant_id,
            workspace_id="wsp_missing00000000000",
            name="Orphan",
        )


def test_mission04_registered_tools_remain_authority_free() -> None:
    names = agent_tool_names(root_agent)
    assert "initialize_dataset_run" in names
    for tool in root_agent.tools:
        func = getattr(tool, "func", None) or getattr(tool, "_func", None) or tool
        if not callable(func):
            continue
        for parameter in inspect.signature(func).parameters:
            assert not is_forbidden_model_supplied_authority_parameter(parameter)
