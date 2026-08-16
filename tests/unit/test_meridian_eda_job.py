from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.errors import ValidationBlockedError
from app.tools.meridian_eda_job import _poll_execution


class _Client:
    def __init__(self, execution: object) -> None:
        self.execution = execution

    def get_execution(self, name: str) -> object:
        return self.execution


def test_poll_execution_terminal_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.tools.meridian_eda_job.run_v2.ExecutionsClient",
        lambda: _Client(
            SimpleNamespace(succeeded_count=1, failed_count=0, cancelled_count=0, name="ok")
        ),
    )
    _poll_execution("projects/p/locations/l/executions/ok", timeout_seconds=5)


def test_poll_execution_terminal_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.tools.meridian_eda_job.run_v2.ExecutionsClient",
        lambda: _Client(
            SimpleNamespace(succeeded_count=0, failed_count=1, cancelled_count=0, name="bad")
        ),
    )
    with pytest.raises(ValidationBlockedError, match="Job failed"):
        _poll_execution("projects/p/locations/l/executions/bad", timeout_seconds=5)


def test_poll_execution_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.tools.meridian_eda_job.run_v2.ExecutionsClient",
        lambda: _Client(
            SimpleNamespace(succeeded_count=0, failed_count=0, cancelled_count=0, name="slow")
        ),
    )
    monkeypatch.setattr("app.tools.meridian_eda_job._POLL_SECONDS", 0)
    with pytest.raises(ValidationBlockedError, match="timed out"):
        _poll_execution("projects/p/locations/l/executions/slow", timeout_seconds=0)
