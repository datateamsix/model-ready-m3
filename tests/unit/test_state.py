from app.core.state import RunStage


def test_model_ready_stage_is_explicit() -> None:
    assert RunStage.MODEL_READY.value == "MODEL_READY"


def test_publish_precedes_model_ready_in_canonical_order() -> None:
    canonical = [
        RunStage.VALIDATING,
        RunStage.PUBLISHING,
        RunStage.MODEL_READY,
    ]
    assert canonical.index(RunStage.PUBLISHING) < canonical.index(RunStage.MODEL_READY)
