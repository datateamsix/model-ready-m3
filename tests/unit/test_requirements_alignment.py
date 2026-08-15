import tomllib
from pathlib import Path

from app.tools.adk_tools import PHASE1_ADK_TOOLS

REPO_ROOT = Path(__file__).resolve().parents[2]


def _requirement_name(line: str) -> str | None:
    stripped = line.split("#", 1)[0].strip()
    if not stripped:
        return None
    for separator in ("==", ">=", "<=", "~=", "!=", ">", "<"):
        if separator in stripped:
            stripped = stripped.split(separator, 1)[0]
            break
    return stripped.strip().split("[", 1)[0]


def test_app_requirements_match_pyproject_runtime_dependencies() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    expected = {_requirement_name(item) for item in pyproject["project"]["dependencies"]}
    req_text = (REPO_ROOT / "app" / "requirements.txt").read_text(encoding="utf-8")
    actual = {_requirement_name(line) for line in req_text.splitlines()}
    expected.discard(None)
    actual.discard(None)
    assert actual == expected


def test_phase1_adk_tools_are_unchanged_count() -> None:
    names = [fn.__name__ for fn in PHASE1_ADK_TOOLS]
    assert "cloud_runtime_probe" not in names
    assert "evaluate_model_ready_gate_from_files" in names
    assert len(names) == len(set(names))
