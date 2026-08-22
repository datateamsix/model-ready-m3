"""Explicit Stripe subscription status → PreM3 entitlement mapping."""

from __future__ import annotations

import pytest

from app.control_plane.entitlements import (
    STRIPE_SUBSCRIPTION_STATUSES,
    UnsupportedSubscriptionStatusError,
    map_stripe_subscription_status,
)
from app.control_plane.models import EntitlementStatus

_EXPECTED = {
    "active": EntitlementStatus.ACTIVE,
    "trialing": EntitlementStatus.TRIALING,
    "past_due": EntitlementStatus.PAST_DUE,
    "incomplete": EntitlementStatus.INCOMPLETE,
    "canceled": EntitlementStatus.CANCELED,
    "unpaid": EntitlementStatus.CANCELED,
    "paused": EntitlementStatus.CANCELED,
    "incomplete_expired": EntitlementStatus.CANCELED,
}


@pytest.mark.parametrize("status", sorted(STRIPE_SUBSCRIPTION_STATUSES))
def test_every_stripe_subscription_status_has_explicit_mapping(status: str) -> None:
    mapped = map_stripe_subscription_status(status)
    assert mapped == _EXPECTED[status]
    if status not in {"active", "trialing"}:
        assert mapped is not EntitlementStatus.ACTIVE


def test_unknown_future_status_is_not_active() -> None:
    with pytest.raises(UnsupportedSubscriptionStatusError):
        map_stripe_subscription_status("pending_activation")
    with pytest.raises(UnsupportedSubscriptionStatusError):
        map_stripe_subscription_status("something_new")
    assert map_stripe_subscription_status("Active") is EntitlementStatus.ACTIVE
