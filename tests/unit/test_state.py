import pytest

from app.core.errors import IllegalTransitionError
from app.core.state import (
    SUCCESS_MILESTONES,
    TERMINAL_STAGES,
    RunStage,
    assert_legal_transition,
)


def test_model_ready_stage_is_explicit() -> None:
    assert RunStage.MODEL_READY.value == "MODEL_READY"


def test_publish_precedes_exploring_and_model_ready() -> None:
    canonical = [
        RunStage.VALIDATING,
        RunStage.PUBLISHING,
        RunStage.EXPLORING,
        RunStage.MODEL_READY,
    ]
    assert canonical.index(RunStage.PUBLISHING) < canonical.index(RunStage.EXPLORING)
    assert canonical.index(RunStage.EXPLORING) < canonical.index(RunStage.MODEL_READY)


def test_publishing_cannot_skip_exploring() -> None:
    with pytest.raises(IllegalTransitionError):
        assert_legal_transition(RunStage.PUBLISHING, RunStage.MODEL_READY)


def test_exploring_may_reach_model_ready() -> None:
    assert_legal_transition(RunStage.PUBLISHING, RunStage.EXPLORING)
    assert_legal_transition(RunStage.EXPLORING, RunStage.MODEL_READY)


def test_publishing_before_validating_is_illegal() -> None:
    with pytest.raises(IllegalTransitionError):
        assert_legal_transition(RunStage.REMEDIATING, RunStage.PUBLISHING)


def test_new_cannot_jump_to_model_ready() -> None:
    with pytest.raises(IllegalTransitionError):
        assert_legal_transition(RunStage.NEW, RunStage.MODEL_READY)


def test_model_ready_is_success_milestone_not_terminal() -> None:
    assert RunStage.MODEL_READY in SUCCESS_MILESTONES
    assert RunStage.MODEL_READY not in TERMINAL_STAGES
    assert TERMINAL_STAGES == {RunStage.FAILED, RunStage.COMPLETE}


def test_model_ready_may_transition_to_learning() -> None:
    assert_legal_transition(RunStage.MODEL_READY, RunStage.LEARNING)


def test_model_ready_may_transition_to_waiting_for_model_approval() -> None:
    assert_legal_transition(RunStage.MODEL_READY, RunStage.WAITING_FOR_MODEL_APPROVAL)


def test_failed_has_no_outbound_transitions() -> None:
    for nxt in RunStage:
        with pytest.raises(IllegalTransitionError):
            assert_legal_transition(RunStage.FAILED, nxt)


def test_complete_has_no_outbound_transitions() -> None:
    for nxt in RunStage:
        with pytest.raises(IllegalTransitionError):
            assert_legal_transition(RunStage.COMPLETE, nxt)
