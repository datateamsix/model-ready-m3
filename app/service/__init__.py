"""prem3-api — authenticated product HTTP service.

Contracts exist. Clerk and Stripe provider adapters are not live.
"""

from __future__ import annotations

from app.service.app import create_app

__all__ = ["create_app"]
