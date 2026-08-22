"""Deterministic webhook claim/lease decisions shared by memory and Firestore."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import assert_never

from app.control_plane.models import (
    ProcessedWebhookEvent,
    WebhookClaimResult,
    WebhookClaimStatus,
    WebhookEventStatus,
    WebhookProvider,
)

DEFAULT_WEBHOOK_CLAIM_LEASE_SECONDS = 120


def claim_expiry(*, claimed_at: datetime, lease_seconds: int) -> datetime:
    return claimed_at + timedelta(seconds=lease_seconds)


def decide_webhook_claim(
    existing: ProcessedWebhookEvent | None,
    *,
    provider: WebhookProvider,
    provider_event_id: str,
    event_type: str,
    now: datetime,
    lease_seconds: int = DEFAULT_WEBHOOK_CLAIM_LEASE_SECONDS,
) -> WebhookClaimResult:
    """Return the next claim outcome without performing persistence."""
    claimed = ProcessedWebhookEvent(
        provider=provider,
        provider_event_id=provider_event_id,
        event_type=event_type,
        status=WebhookEventStatus.CLAIMED,
        claimed_at=now,
        claim_expires_at=claim_expiry(claimed_at=now, lease_seconds=lease_seconds),
        processed_at=None,
        result=None,
    )
    if existing is None:
        return WebhookClaimResult(status=WebhookClaimStatus.WON, event=claimed)
    if existing.status is WebhookEventStatus.FAILED:
        return WebhookClaimResult(status=WebhookClaimStatus.WON, event=claimed)
    if existing.status is WebhookEventStatus.PROCESSED:
        return WebhookClaimResult(status=WebhookClaimStatus.ALREADY_PROCESSED, event=existing)
    if existing.status is WebhookEventStatus.CLAIMED:
        expires_at = existing.claim_expires_at or claim_expiry(
            claimed_at=existing.claimed_at, lease_seconds=lease_seconds
        )
        if expires_at <= now:
            return WebhookClaimResult(status=WebhookClaimStatus.WON, event=claimed)
        return WebhookClaimResult(status=WebhookClaimStatus.ALREADY_CLAIMED, event=existing)
    assert_never(existing.status)
