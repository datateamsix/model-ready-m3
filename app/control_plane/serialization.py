"""Deterministic Firestore document serialization for control-plane models.

UTC-aware datetimes. Enums as stable strings. Fail closed on malformed documents.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.errors import ControlPlaneError

SCHEMA_VERSION = 1


class ControlPlaneDocumentError(ControlPlaneError):
    """Raised when a persisted document cannot be deserialized safely."""


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def model_to_document(model: BaseModel) -> dict[str, Any]:
    payload = model.model_dump(mode="python")
    payload["schema_version"] = SCHEMA_VERSION
    return _normalize_outbound(payload)


def document_to_model[T: BaseModel](model_type: type[T], data: dict[str, Any] | None) -> T:
    if data is None:
        raise ControlPlaneDocumentError(f"Missing document for {model_type.__name__}.")
    if not isinstance(data, dict):
        raise ControlPlaneDocumentError(f"Malformed document for {model_type.__name__}.")
    cleaned = dict(data)
    cleaned.pop("schema_version", None)
    try:
        return model_type.model_validate(_normalize_inbound(cleaned))
    except ValidationError as exc:
        raise ControlPlaneDocumentError(
            f"Rejected malformed {model_type.__name__} document."
        ) from exc


def _normalize_outbound(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _normalize_outbound(value.model_dump(mode="python"))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return _to_utc(value)
    if isinstance(value, frozenset):
        return sorted(_normalize_outbound(item) for item in value)
    if isinstance(value, set):
        return sorted(_normalize_outbound(item) for item in value)
    if isinstance(value, dict):
        return {str(key): _normalize_outbound(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_normalize_outbound(item) for item in value]
    return value


def _normalize_inbound(value: Any) -> Any:
    if isinstance(value, datetime):
        return _to_utc(value)
    if isinstance(value, dict):
        return {str(key): _normalize_inbound(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_inbound(item) for item in value]
    return value
