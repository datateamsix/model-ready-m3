"""Structured PreM3 response architecture.

Intelligence determines what is true. This package determines how it is
expressed. The UI determines how it is rendered. Output QA will later
determine whether it was expressed correctly.
"""

from app.response.builder import ResponseBuilder
from app.response.contracts import (
    PresentationStatus,
    ResponseType,
    StructuredResponse,
)
from app.response.render import render_markdown

__all__ = [
    "PresentationStatus",
    "ResponseBuilder",
    "ResponseType",
    "StructuredResponse",
    "render_markdown",
]
