from app.agent import root_agent
from app.tools.adk_tools import PHASE1_ADK_TOOLS
from app.tools.precloud import agent_tool_names


def test_root_agent_registers_phase1_tools() -> None:
    assert root_agent is not None
    names = agent_tool_names(root_agent)
    expected = {fn.__name__ for fn in PHASE1_ADK_TOOLS}
    missing = sorted(expected - names)
    assert not missing, missing
    assert "evaluate_model_ready_gate_from_files" in names
    assert "build_model_ready_frame_from_files" in names
    assert "validate_model_ready_artifact_file" in names
