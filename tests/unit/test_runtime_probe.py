from app.tools.runtime_probe import cloud_runtime_probe, strip_secrets


def test_local_metadata_failure_is_graceful() -> None:
    result = cloud_runtime_probe()
    assert result["runtime"]["environment"] in {"local", "cloud", "cloud_run"}
    if not result["runtime"].get("service"):
        assert result["runtime"]["environment"] != "cloud_run"
    assert result["configuration"]["vertex_location"] == "global"
    assert result["configuration"]["cloud_region"] == "us-central1"
    assert result["checks"]["identity"] in {"PASS", "FAIL"}


def test_runtime_probe_never_returns_tokens() -> None:
    result = cloud_runtime_probe()
    blob = _all_keys(result)
    assert "access_token" not in blob
    assert "id_token" not in blob
    assert "credentials" not in blob
    serialized = str(result).lower()
    assert "ya29." not in serialized
    assert "-----begin" not in serialized


def test_strip_secrets_removes_credential_fields() -> None:
    cleaned = strip_secrets(
        {
            "ok": "keep",
            "access_token": "ya29.secret",
            "nested": {"id_token": "abc", "status": "PASS"},
        }
    )
    assert cleaned == {"ok": "keep", "nested": {"status": "PASS"}}


def _all_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key).lower())
            keys.update(_all_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_all_keys(item))
    return keys
