"""prem3-api application factory.

Local default is in-memory and fail-closed unless Clerk/Stripe settings
are present. Cloud runtime (PREM3_API_RUNTIME=cloud or Cloud Run K_SERVICE)
constructs Firestore, Clerk, and Stripe from deployment configuration.
No Firestore, Clerk, or Stripe network call on import.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import Settings, load_settings
from app.control_plane.repository import ControlPlaneRepository
from app.service.auth import IdentityVerifier, UnconfiguredIdentityVerifier
from app.service.billing import BillingGateway, UnavailableBillingGateway
from app.service.billing_config import BillingConfig
from app.service.billing_events import BillingWebhookProcessor
from app.service.catalog import build_plan_catalog
from app.service.clerk_runtime import (
    MembershipAuthority,
    OrganizationDirectory,
    RealClerkRuntime,
    WebhookVerifier,
)
from app.service.errors import (
    APIError,
    ProblemDetail,
    ProblemFieldError,
    internal_error,
    problem_json,
    validation_error,
)
from app.service.middleware import RequestIdMiddleware, current_request_id
from app.service.models import PlanCatalogResponse
from app.service.routers import (
    billing,
    catalog,
    datasets,
    health,
    identity,
    identity_webhooks,
    workspaces,
)
from app.service.runtime import assert_provider_mode_safe, build_control_plane
from app.service.stripe_gateway import StripeBillingGateway
from app.service.stripe_provider import RealStripeProvider


def create_app(
    *,
    settings: Settings | None = None,
    control_plane_repository: ControlPlaneRepository | None = None,
    identity_verifier: IdentityVerifier | None = None,
    billing_gateway: BillingGateway | None = None,
    billing_webhook_processor: BillingWebhookProcessor | None = None,
    plan_catalog: PlanCatalogResponse | None = None,
    membership_authority: MembershipAuthority | None = None,
    webhook_verifier: WebhookVerifier | None = None,
    organization_directory: OrganizationDirectory | None = None,
) -> FastAPI:
    cfg = settings or load_settings()
    assert_provider_mode_safe(cfg)
    clerk_runtime = None
    if identity_verifier is None and cfg.clerk_secret_key:
        clerk_runtime = RealClerkRuntime(cfg)
        identity_verifier = clerk_runtime
        if membership_authority is None:
            membership_authority = clerk_runtime
        if webhook_verifier is None:
            webhook_verifier = clerk_runtime
        if organization_directory is None:
            organization_directory = clerk_runtime
    app = FastAPI(
        title="prem3-api",
        version="0.1.0",
        summary="PreM3 authenticated product API",
        description=(
            "Presentation-safe Project, Dataset, catalog, and billing contracts. "
            "Clerk session tokens are verified when the identity provider is configured. "
            "Stripe Checkout and Customer Portal are available when billing is configured. "
            "Tenant identity is never accepted from the client."
        ),
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = cfg
    repo, control_plane_status = build_control_plane(cfg, control_plane_repository)
    app.state.control_plane = repo
    app.state.control_plane_status = control_plane_status
    app.state.identity_verifier = identity_verifier or UnconfiguredIdentityVerifier()
    app.state.membership_authority = membership_authority
    app.state.webhook_verifier = webhook_verifier
    app.state.organization_directory = organization_directory
    app.state.clerk_runtime = clerk_runtime
    billing_config = BillingConfig.from_settings(cfg)
    app.state.billing_config = billing_config
    if billing_gateway is None and cfg.stripe_secret_key:
        provider = RealStripeProvider(billing_config)
        billing_gateway = StripeBillingGateway(
            provider=provider, repo=repo, config=billing_config
        )
        if billing_webhook_processor is None and cfg.stripe_webhook_secret:
            billing_webhook_processor = BillingWebhookProcessor(
                provider=provider, repo=repo, config=billing_config
            )
    app.state.billing_gateway = billing_gateway or UnavailableBillingGateway()
    app.state.billing_webhook_processor = billing_webhook_processor
    app.state.plan_catalog = plan_catalog or build_plan_catalog(config=billing_config)

    app.add_middleware(RequestIdMiddleware)
    app.include_router(health.router)
    app.include_router(catalog.router)
    app.include_router(identity.router)
    app.include_router(workspaces.router)
    app.include_router(datasets.router)
    app.include_router(billing.router)
    app.include_router(identity_webhooks.router)

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        problem = exc.to_problem(request_id=_request_id(), instance=str(request.url.path))
        return _problem_response(problem)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields: list[ProblemFieldError] = []
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", ()) if part != "body")
            fields.append(ProblemFieldError(field=loc or "body", message=str(err.get("msg", ""))))
        problem = validation_error(fields).to_problem(
            request_id=_request_id(), instance=str(request.url.path)
        )
        return _problem_response(problem)

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, APIError):
            problem = exc.to_problem(request_id=_request_id(), instance=str(request.url.path))
            return _problem_response(problem)
        if isinstance(exc, RequestValidationError):
            return await validation_handler(request, exc)
        if isinstance(exc, StarletteHTTPException):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        problem = internal_error().to_problem(
            request_id=_request_id(), instance=str(request.url.path)
        )
        return _problem_response(problem)

    def custom_openapi() -> dict:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = _build_openapi(app)
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
    return app


def _request_id() -> str:
    return current_request_id() or "unknown"


def _problem_response(problem: ProblemDetail) -> JSONResponse:
    return JSONResponse(
        status_code=problem.status,
        content=jsonable_encoder(problem_json(problem)),
        media_type="application/problem+json",
    )


def _build_openapi(app: FastAPI) -> dict:
    from fastapi.openapi.utils import get_openapi

    schema = get_openapi(
        title=app.title,
        version=app.version,
        summary=app.summary,
        description=app.description,
        routes=app.routes,
    )
    schema["openapi"] = "3.1.0"
    schema["components"] = schema.get("components") or {}
    schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Clerk session token forwarded by the Next.js BFF. "
                "prem3-api verifies the session token. Tenant IDs are never "
                "accepted from the client."
            ),
        }
    }
    schema["components"]["schemas"] = schema.get("components", {}).get("schemas") or {}
    schema["components"]["schemas"]["ProblemDetail"] = ProblemDetail.model_json_schema()
    protected_prefixes = ("/v1/me", "/v1/workspaces", "/v1/billing/")
    for path, operations in schema.get("paths", {}).items():
        if not path.startswith(protected_prefixes):
            continue
        if not isinstance(operations, dict):
            continue
        for operation in operations.values():
            if isinstance(operation, dict):
                operation.setdefault("security", [{"HTTPBearer": []}])
    return schema


app = create_app()
