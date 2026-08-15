"""ModelReady domain exceptions."""


class ModelReadyError(Exception):
    """Base exception for ModelReady failures."""


class ValidationBlockedError(ModelReadyError):
    """Raised when deterministic validation prevents MODEL_READY."""


class ApprovalRequiredError(ModelReadyError):
    """Raised when a transformation requires an explicit human decision."""


class PublishParityError(ModelReadyError):
    """Raised when BigQuery output does not match the validated artifact."""


class RegistryTrustError(ModelReadyError):
    """Raised when a directory registry card is used as an executable field map."""
