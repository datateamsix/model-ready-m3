from app.config import load_settings


def test_vertex_location_and_cloud_region_are_distinct(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "global")
    monkeypatch.setenv("GOOGLE_CLOUD_REGION", "us-central1")
    settings = load_settings()
    assert settings.vertex_location == "global"
    assert settings.cloud_region == "us-central1"
    assert settings.vertex_location != settings.cloud_region


def test_cloud_region_does_not_fall_back_to_vertex_location(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "global")
    monkeypatch.delenv("GOOGLE_CLOUD_REGION", raising=False)
    settings = load_settings()
    assert settings.vertex_location == "global"
    assert settings.cloud_region == "us-central1"
