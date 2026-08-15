from app.agent import root_agent
from app.tools.adk_tools import PHASE1_ADK_TOOLS
from app.tools.precloud import agent_tool_names
from app.tools.run_tools import READ_ONLY_CONTEXT_TOOLS, RUN_READY_TOOLS
from app.tools.runtime_probe import CLOUD_RUNTIME_DIAGNOSTIC_TOOLS


def test_root_agent_registers_run_level_tools() -> None:
    assert root_agent is not None
    names = agent_tool_names(root_agent)
    expected = {fn.__name__ for fn in RUN_READY_TOOLS}
    missing = sorted(expected - names)
    assert not missing, missing
    assert "initialize_dataset_run" in names
    assert "inspect_dataset_run" in names
    assert "apply_safe_remediations" in names
    assert "validate_and_publish_run" in names
    assert "complete_dataset_run" in names
    assert "run_meridian_eda" in names


def test_root_agent_does_not_expose_low_level_mutating_tools() -> None:
    names = agent_tool_names(root_agent)
    mutating = {
        fn.__name__
        for fn in PHASE1_ADK_TOOLS
        if fn.__name__
        not in {
            "get_meridian_pocket_card",
            "lookup_provider_card",
            "search_provider_directory",
        }
    }
    leaked = sorted(mutating & names)
    assert not leaked, leaked
    assert "run_dataset_a" not in names


def test_root_agent_registers_read_only_context_and_runtime_probe() -> None:
    names = agent_tool_names(root_agent)
    context = {fn.__name__ for fn in READ_ONLY_CONTEXT_TOOLS}
    diagnostic = {fn.__name__ for fn in CLOUD_RUNTIME_DIAGNOSTIC_TOOLS}
    assert context <= names
    assert diagnostic == {"cloud_runtime_probe"}
    assert "cloud_runtime_probe" in names
    assert "cloud_runtime_probe" not in {fn.__name__ for fn in PHASE1_ADK_TOOLS}
