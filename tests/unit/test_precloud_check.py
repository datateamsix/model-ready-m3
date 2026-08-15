from app.tools.precloud import all_required_passed, collect_checks, format_report


def test_precloud_check_passes_without_live_gcp() -> None:
    checks = collect_checks(live=False)
    assert all_required_passed(checks)
    report = format_report(checks)
    assert "READY_FOR_CLOUD_RUN" in report
    assert "NOT_READY_FOR_CLOUD_RUN" not in report
    assert "[x] Vertex endpoint: global" in report
    assert "[x] cloud region: us-central1" in report
