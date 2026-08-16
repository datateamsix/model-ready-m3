from __future__ import annotations

from app.agent import PREM3_INSTRUCTION, root_agent
from app.config import settings
from app.core.product import (
    HANDOFF_TITLE,
    LEARNING_RECEIPT_DISPLAY_NAME,
    LEARNING_SYSTEM_NAME,
    PRODUCT_DESCRIPTOR,
    PRODUCT_NAME,
    PRODUCT_SECONDARY_LINE,
    PRODUCT_TAGLINE,
    USER_RESOLUTION_TITLE,
)
from app.core.state import RunStage
from app.tools.meridian_eda_gate import (
    build_meridian_refusal_feedback,
    default_eda_analysis,
    render_pre_modeling_handoff,
)
from app.tools.precloud import agent_tool_names
from app.tools.run_tools import RUN_READY_TOOLS
from tests.unit.test_meridian_eda import _receipt


def test_product_metadata_is_prem3() -> None:
    assert PRODUCT_NAME == "PreM3"
    assert PRODUCT_DESCRIPTOR.startswith("A self-learning, autonomous pre-modeling agent")
    assert PRODUCT_TAGLINE == "Map. Mend. Model."
    assert PRODUCT_SECONDARY_LINE == "Before you model, PreM3."
    assert LEARNING_SYSTEM_NAME == "PreM3 Experience Loop"
    assert LEARNING_RECEIPT_DISPLAY_NAME == "PreM3 Learning Receipt"
    assert HANDOFF_TITLE == "PreM3 Pre-Modeling Handoff"
    assert USER_RESOLUTION_TITLE == "PreM3 User Resolution Pack"


def test_root_agent_display_identity_is_prem3() -> None:
    assert settings.agent_name == "modelready_m3"
    assert root_agent.name == "modelready_m3"
    assert "PreM3" in (root_agent.description or "")
    assert "PreM3" in PREM3_INSTRUCTION
    assert "Map. Mend. Model." in PREM3_INSTRUCTION
    assert "Launching Meridian itself is approval-gated" not in PREM3_INSTRUCTION
    assert "sample_posterior" in PREM3_INSTRUCTION


def test_root_agent_tool_order_unchanged() -> None:
    names = agent_tool_names(root_agent)
    expected = {fn.__name__ for fn in RUN_READY_TOOLS}
    assert expected <= names
    assert expected == {
        "initialize_dataset_run",
        "inspect_dataset_run",
        "apply_safe_remediations",
        "validate_and_publish_run",
        "run_meridian_eda",
        "complete_dataset_run",
    }
    assert {
        "run_pre_eda_diagnostics",
        "inspect_modeling_feasibility",
        "generate_semantic_readiness_interview",
        "simulate_model_scope_scenarios",
        "record_semantic_context",
    } <= names


def test_handoff_heading_uses_prem3() -> None:
    receipt = _receipt()
    analysis = default_eda_analysis(receipt)
    text = render_pre_modeling_handoff(
        run_id="run-eda",
        data_engineering={"detected": 5, "resolved": 5, "open": 0},
        model_input={"endpoint": "view", "fingerprint": "abc", "rows": 1, "columns": 1},
        destination={
            "versioned_table": "t",
            "consumption_view": "v",
            "physical_schema_status": "PASS",
        },
        receipt=receipt,
        analysis=analysis,
        eda_gate={"status": "PASS"},
    )
    assert text.startswith("# PreM3 Pre-Modeling Handoff")


def test_user_resolution_copy_uses_prem3() -> None:
    feedback = build_meridian_refusal_feedback(
        run_id="run-eda",
        official_message="controls do not vary across geos",
    )
    actions = [step.action for step in feedback.recommended_steps]
    assert any("Rerun PreM3" in action for action in actions)
    assert all("Rerun ModelReady" not in action for action in actions)
    assert "PreM3 cannot" in feedback.problem_summary
    assert "ModelReady" not in feedback.problem_summary


def test_model_ready_state_enum_unchanged() -> None:
    assert RunStage.MODEL_READY.value == "MODEL_READY"
    assert RunStage.EXPLORING.value == "EXPLORING"
    assert RunStage.LEARNING.value == "LEARNING"
