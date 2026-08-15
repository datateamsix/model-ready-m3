import pytest

from app.core.errors import IllegalTransitionError
from app.core.state import RunStage, assert_legal_transition


def test_model_ready_stage_is_explicit() -> None:
    assert RunStage.MODEL_READY.value == "MODEL_READY"


def test_publish_precedes_model_ready_in_canonical_order() -> None:
    canonical = [
        RunStage.VALIDATING,
        RunStage.PUBLISHING,
        RunStage.MODEL_READY,
    ]
    assert canonical.index(RunStage.PUBLISHING) < canonical.index(RunStage.MODEL_READY)


def test_publishing_before_validating_is_illegal() -> None:
    with pytest.raises(IllegalTransitionError):
        assert_legal_transition(RunStage.REMEDIATING, RunStage.PUBLISHING)


def test_new_cannot_jump_to_model_ready() -> None:
    with pytest.raises(IllegalTransitionError):
        assert_legal_transition(RunStage.NEW, RunStage.MODEL_READY)
