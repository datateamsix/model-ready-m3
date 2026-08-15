"""Canonical M3 run state machine values."""

from enum import StrEnum

from app.core.errors import IllegalTransitionError


class RunStage(StrEnum):
    NEW = "NEW"
    DISCOVERING = "DISCOVERING"
    PROFILING = "PROFILING"
    MAPPING = "MAPPING"
    ASSESSING = "ASSESSING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    REMEDIATING = "REMEDIATING"
    VALIDATING = "VALIDATING"
    PUBLISHING = "PUBLISHING"
    MODEL_READY = "MODEL_READY"
    WAITING_FOR_MODEL_APPROVAL = "WAITING_FOR_MODEL_APPROVAL"
    MODELING = "MODELING"
    FAILED = "FAILED"
    LEARNING = "LEARNING"
    COMPLETE = "COMPLETE"


TERMINAL_STAGES = {RunStage.MODEL_READY, RunStage.FAILED, RunStage.COMPLETE}

_LEGAL_TRANSITIONS: dict[RunStage, frozenset[RunStage]] = {
    RunStage.NEW: frozenset({RunStage.DISCOVERING, RunStage.FAILED}),
    RunStage.DISCOVERING: frozenset({RunStage.PROFILING, RunStage.FAILED}),
    RunStage.PROFILING: frozenset({RunStage.MAPPING, RunStage.FAILED}),
    RunStage.MAPPING: frozenset({RunStage.ASSESSING, RunStage.FAILED}),
    RunStage.ASSESSING: frozenset(
        {RunStage.REMEDIATING, RunStage.WAITING_FOR_APPROVAL, RunStage.VALIDATING, RunStage.FAILED}
    ),
    RunStage.WAITING_FOR_APPROVAL: frozenset({RunStage.REMEDIATING, RunStage.FAILED}),
    RunStage.REMEDIATING: frozenset({RunStage.VALIDATING, RunStage.FAILED}),
    RunStage.VALIDATING: frozenset({RunStage.PUBLISHING, RunStage.REMEDIATING, RunStage.FAILED}),
    RunStage.PUBLISHING: frozenset({RunStage.MODEL_READY, RunStage.FAILED}),
    RunStage.MODEL_READY: frozenset(
        {RunStage.LEARNING, RunStage.WAITING_FOR_MODEL_APPROVAL, RunStage.COMPLETE, RunStage.FAILED}
    ),
    RunStage.WAITING_FOR_MODEL_APPROVAL: frozenset({RunStage.MODELING, RunStage.FAILED}),
    RunStage.MODELING: frozenset({RunStage.LEARNING, RunStage.COMPLETE, RunStage.FAILED}),
    RunStage.LEARNING: frozenset({RunStage.COMPLETE, RunStage.FAILED}),
    RunStage.FAILED: frozenset(),
    RunStage.COMPLETE: frozenset(),
}


def _assert_transition_table_complete() -> None:
    missing = [stage for stage in RunStage if stage not in _LEGAL_TRANSITIONS]
    if missing:
        raise RuntimeError(f"Legal transition table missing stages: {missing}")


_assert_transition_table_complete()


def assert_legal_transition(current: RunStage, nxt: RunStage) -> None:
    allowed = _LEGAL_TRANSITIONS[current]
    if nxt not in allowed:
        raise IllegalTransitionError(f"Illegal transition {current.value} -> {nxt.value}")
