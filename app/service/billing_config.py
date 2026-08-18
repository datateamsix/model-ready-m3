"""Server-owned Stripe Price mapping and catalog presentation.

Never expose Stripe Price, Product, or Customer IDs through public contracts.
Catalog GET does not perform Stripe network reads.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.config import Settings
from app.control_plane.entitlements import PAID_PLAN_IDS, PlanId

ALLOWED_METADATA_KEYS: frozenset[str] = frozenset({"prem3_tenant_id", "prem3_plan_id"})


@dataclass(frozen=True, slots=True)
class CatalogPricePresentation:
    amount: int | None
    currency: str | None
    display_price: str | None


@dataclass(frozen=True, slots=True)
class BillingConfig:
    secret_key: str | None
    webhook_secret: str | None
    frontend_origin: str | None
    portal_configuration_id: str | None
    price_by_plan: dict[str, str]
    catalog_presentation: dict[str, CatalogPricePresentation]
    webhook_claim_lease_seconds: int
    stripe_timeout_seconds: float
    stripe_max_network_retries: int

    @classmethod
    def from_settings(cls, settings: Settings) -> BillingConfig:
        prices: dict[str, str] = {}
        if settings.stripe_price_project:
            prices[PlanId.PROJECT] = settings.stripe_price_project.strip()
        if settings.stripe_price_portfolio:
            prices[PlanId.PORTFOLIO] = settings.stripe_price_portfolio.strip()
        if settings.stripe_price_enterprise:
            prices[PlanId.ENTERPRISE] = settings.stripe_price_enterprise.strip()
        currency = (settings.stripe_catalog_currency or "").strip().lower() or None
        presentation = {
            PlanId.PROJECT: CatalogPricePresentation(
                amount=settings.stripe_catalog_project_amount,
                currency=currency if settings.stripe_catalog_project_amount is not None else None,
                display_price=settings.stripe_catalog_project_display_price,
            ),
            PlanId.PORTFOLIO: CatalogPricePresentation(
                amount=settings.stripe_catalog_portfolio_amount,
                currency=currency if settings.stripe_catalog_portfolio_amount is not None else None,
                display_price=settings.stripe_catalog_portfolio_display_price,
            ),
            PlanId.ENTERPRISE: CatalogPricePresentation(
                amount=settings.stripe_catalog_enterprise_amount,
                currency=(
                    currency if settings.stripe_catalog_enterprise_amount is not None else None
                ),
                display_price=settings.stripe_catalog_enterprise_display_price,
            ),
        }
        return cls(
            secret_key=settings.stripe_secret_key,
            webhook_secret=settings.stripe_webhook_secret,
            frontend_origin=normalize_frontend_origin(settings.prem3_frontend_origin),
            portal_configuration_id=settings.stripe_portal_configuration_id,
            price_by_plan=prices,
            catalog_presentation=presentation,
            webhook_claim_lease_seconds=settings.webhook_claim_lease_seconds,
            stripe_timeout_seconds=settings.stripe_timeout_seconds,
            stripe_max_network_retries=settings.stripe_max_network_retries,
        )

    def price_id_for_plan(self, plan_id: str) -> str | None:
        return self.price_by_plan.get(plan_id)

    def plan_id_for_price(self, price_id: str) -> str | None:
        for plan_id, configured in self.price_by_plan.items():
            if configured == price_id:
                return plan_id
        return None

    def checkout_eligible(self, plan_id: str) -> bool:
        return plan_id in PAID_PLAN_IDS and bool(self.price_id_for_plan(plan_id))


def normalize_frontend_origin(raw: str | None) -> str | None:
    if raw is None or not raw.strip():
        return None
    parsed = urlparse(raw.strip())
    if parsed.scheme not in {"https", "http"}:
        return None
    if parsed.netloc == "":
        return None
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        return None
    if parsed.username or parsed.password:
        return None
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def build_redirect_url(*, origin: str, return_path: str | None, billing_result: str) -> str:
    path = return_path or "/app/billing"
    separator = "&" if "?" in path else "?"
    return f"{origin}{path}{separator}billing={billing_result}"
