"""DOMAIN_VIEW contracts and deterministic builder."""

from app.domain.intelligence.builder import build_domain_view, summarize_domain_view
from app.domain.intelligence.diff import diff_domain_views
from app.domain.intelligence.models import DomainView, DomainViewClaim

__all__ = [
    "DomainView",
    "DomainViewClaim",
    "build_domain_view",
    "diff_domain_views",
    "summarize_domain_view",
]
