from app.agent import root_agent
from app.tools.adk_tools import PHASE1_ADK_TOOLS
from app.tools.precloud import agent_tool_names
from app.tools.runtime_probe import CLOUD_RUNTIME_DIAGNOSTIC_TOOLS


def test_root_agent_registers_phase1_tools() -> None:
    assert root_agent is not None
    names = agent_tool_names(root_agent)
    expected = {fn.__name__ for fn in PHASE1_ADK_TOOLS}
    missing = sorted(expected - names)
    assert not missing, missing
    assert "evaluate_model_ready_gate_from_files" in names
    assert "build_model_ready_frame_from_files" in names
    assert "validate_model_ready_artifact_file" in names


def test_root_agent_registers_runtime_probe_separately() -> None:
    names = agent_tool_names(root_agent)
    diagnostic = {fn.__name__ for fn in CLOUD_RUNTIME_DIAGNOSTIC_TOOLS}
    assert diagnostic == {"cloud_runtime_probe"}
    assert "cloud_runtime_probe" in names
    phase1 = {fn.__name__ for fn in PHASE1_ADK_TOOLS}
    assert "cloud_runtime_probe" not in phase1
