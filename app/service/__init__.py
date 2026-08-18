"""prem3-api — authenticated product HTTP service.

Local factory is fail-closed. Cloud runtime uses Firestore, Clerk, and Stripe
when deployment configuration is present.
"""

from __future__ import annotations

from app.service.app import create_app

__all__ = ["create_app"]
