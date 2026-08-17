"""ModelReady domain exceptions."""


class ModelReadyError(Exception):
    """Base exception for ModelReady failures."""


class ValidationBlockedError(ModelReadyError):
    """Raised when deterministic validation prevents MODEL_READY."""


class AssignmentInitError(ValidationBlockedError):
    """Typed assignment initialization failure. Reason codes are machine-stable."""

    def __init__(
        self,
        message: str,
        *,
        reason: str,
        source: str | None = None,
        authority: str = "PREM3_DETERMINISTIC",
        recoverability: str = "USER_REQUIRED",
        owner: str = "user",
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.source = source
        self.authority = authority
        self.recoverability = recoverability
        self.owner = owner


class ApprovalRequiredError(ModelReadyError):
    """Raised when a transformation requires an explicit human decision."""


class PublishParityError(ModelReadyError):
    """Raised when BigQuery output does not match the validated artifact."""


class RegistryTrustError(ModelReadyError):
    """Raised when a directory registry card is used as an executable field map."""


class SafetyViolationError(ModelReadyError):
    """Raised when a requested transform violates a deterministic safety rule."""


class IllegalTransitionError(ModelReadyError):
    """Raised when a run attempts an illegal state-machine transition."""
