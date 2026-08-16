from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from app.core.contracts import utc_now
from app.core.errors import SafetyViolationError, ValidationBlockedError
from app.core.meridian_eda_contracts import (
    EDA_MODEL_SPEC_GEO_TIME_INVARIANT,
    EDA_MODEL_SPEC_POLICY,
    PINNED_GOOGLE_MERIDIAN,
    MeridianEDAFinding,
    MeridianEDAPriorContext,
    MeridianEDAReceipt,
    canonical_eda_config,
    category_for_check,
    eda_config_fingerprint,
    eda_idempotency_key,
)
from app.core.model_intent import DATASET_A_MODEL_INTENT
from app.tools.meridian_contract import generate_meridian_input_contract
from app.tools.meridian_eda import (
    _assert_receipt_identity,
    _matching_receipt,
    assert_fingerprint_matches,
)
from app.tools.meridian_eda_gate import (
    accept_eda_analysis,
    build_meridian_feedback,
    build_meridian_refusal_feedback,
    default_eda_analysis,
    evaluate_meridian_eda_gate,
    validate_eda_analysis,
)
from app.tools.meridian_eda_mapping import derive_kpi_type, mapping_from_contract
from app.tools.meridian_eda_runtime import (
    _assert_no_posterior,
    _construct_eda_meridian,
    _forbid_posterior,
    extract_time_only_variables,
    meridian_available,
)
from app.tools.meridian_eda_serialize import extract_data_adequacy, serialize_outcomes
from app.tools.model_consumption import fingerprint_frame
from app.tools.run_tools import RUN_READY_TOOLS, _sanitize_eda_analysis


def _dataset_a_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "time": ["2024-01-01"],
            "geo": ["CA"],
            "kpi_orders": [1],
            "kpi_revenue": [1.0],
            "revenue_per_kpi": [1.0],
            "population": [1],
            "paid_search_impressions": [1],
            "paid_search_spend": [1.0],
            "shopping_impressions": [1],
            "shopping_spend": [1.0],
            "paid_social_impressions": [1],
            "paid_social_spend": [1.0],
            "organic_sessions": [1],
            "consumer_sentiment_index": [1.0],
            "competitor_discount_index": [0.1],
            "music_center_promo": [0],
        }
    )


def _dataset_a_contract():
    return generate_meridian_input_contract(
        run_id="run-eda",
        intent=DATASET_A_MODEL_INTENT,
        frame=_dataset_a_frame(),
        project_id="modelready-m3",
        dataset_id="modelready_models",
        table_id="model_input_run_eda",
    )


def _finding(**overrides) -> MeridianEDAFinding:
    payload = {
        "finding_id": "KPI_INVARIABILITY.OVERALL.VARIABILITY.INFO.01",
        "check_type": "KPI_INVARIABILITY",
        "report_category": "individual_variables",
        "severity": "INFO",
        "finding_cause": "NONE",
        "explanation": "KPI varies enough to model.",
        "analysis_level": "OVERALL",
    }
    payload.update(overrides)
    return MeridianEDAFinding.model_validate(payload)


def _official_model_context() -> dict:
    return {
        "model_spec": {
            "source": "MERIDIAN_DEFAULT",
            "knots": "MERIDIAN_DEFAULT",
            "n_knots": "MERIDIAN_DEFAULT",
            "n_time": 10,
            "enable_aks": False,
            "approved_for_final_modeling": False,
        },
        "data_adequacy": {
            "n_geos": 2,
            "n_times": 10,
            "n_knots": 10,
            "n_controls": 3,
            "n_treatments": 4,
            "n_parameters": 20,
            "n_data_points": 100,
            "ratio": 0.2,
            "source_artifact_ref": "DATA_ADEQUACY.OVERALL.01",
        },
    }


def _receipt(*findings: MeridianEDAFinding) -> MeridianEDAReceipt:
    items = list(findings) or [_finding()]
    errors = sum(item.severity == "ERROR" for item in items)
    attention = sum(item.severity == "ATTENTION" for item in items)
    info = sum(item.severity == "INFO" for item in items)
    max_sev = "ERROR" if errors else "ATTENTION" if attention else "INFO"
    return MeridianEDAReceipt(
        run_id="run-eda",
        html_report_uri="gs://bucket/eda/meridian_eda_report.html",
        posterior_sampling=False,
        model_fitted=False,
        findings=items,
        severity_summary={
            "error_count": errors,
            "attention_count": attention,
            "info_count": info,
            "max_severity": max_sev,
        },
        status="EDA_COMPLETE",
        **_official_model_context(),
    )


def test_dataset_a_mapping_uses_contract_not_hardcoded_display_names() -> None:
    mapping = mapping_from_contract(intent=DATASET_A_MODEL_INTENT, contract=_dataset_a_contract())
    kpi_type, derivation = derive_kpi_type(DATASET_A_MODEL_INTENT)
    assert kpi_type == "non_revenue"
    assert "distinct from revenue" in derivation
    assert mapping.kpi_col == "kpi_orders"
    assert mapping.media_cols == [
        "paid_search_impressions",
        "shopping_impressions",
        "paid_social_impressions",
    ]
    assert mapping.media_spend_cols == [
        "paid_search_spend",
        "shopping_spend",
        "paid_social_spend",
    ]
    assert mapping.media_channels == ["paid_search", "shopping", "paid_social"]
    assert mapping.organic_media_cols == ["organic_sessions"]
    assert mapping.control_cols == [
        "consumer_sentiment_index",
        "competitor_discount_index",
        "music_center_promo",
    ]


def test_official_check_types_map_to_five_report_categories() -> None:
    assert category_for_check("DATA_ADEQUACY") == "spend_and_media_unit"
    assert category_for_check("COST_PER_MEDIA_UNIT") == "spend_and_media_unit"
    assert category_for_check("KPI_INVARIABILITY") == "individual_variables"
    assert category_for_check("STANDARD_DEVIATION") == "individual_variables"
    assert category_for_check("POPULATION_CORRELATION") == "population_scaling"
    assert category_for_check("PAIRWISE_CORRELATION") == "variable_relationships"
    assert category_for_check("MULTICOLLINEARITY") == "variable_relationships"
    assert category_for_check("VARIABLE_GEO_TIME_COLLINEARITY") == "variable_relationships"
    assert category_for_check("PRIOR_PROBABILITY") == "prior_specifications"
    with pytest.raises(ValueError, match="Unknown official Meridian check type"):
        category_for_check("HOMEMADE_CHECK")


def test_error_findings_become_user_required_feedback() -> None:
    receipt = _receipt(
        _finding(
            finding_id="PAIRWISE_CORRELATION.OVERALL.MULTICOLLINEARITY.ERROR.01",
            check_type="PAIRWISE_CORRELATION",
            report_category="variable_relationships",
            severity="ERROR",
            finding_cause="MULTICOLLINEARITY",
            explanation="Near-perfect correlation. Consider combining the variables.",
        )
    )
    gate = evaluate_meridian_eda_gate(receipt=receipt, html_persisted=True)
    feedback = build_meridian_feedback(receipt=receipt, gate=gate)
    assert feedback.status == "EDA_BLOCKED"
    assert feedback.resolution_status == "USER_REQUIRED"
    assert feedback.agent_can_fix is False
    assert feedback.safe_to_model is False
    assert feedback.source_type == "EDA_ERROR"
    assert feedback.eda_ran is True
    assert feedback.user_action_required is True
    assert "Near-perfect correlation" in feedback.official_message
    required = [item for item in feedback.corrections if item.owner == "USER_REQUIRED"]
    assert required[0].agent_can_fix is False
    assert required[0].official_message
    assert required[0].prem3_interpretation
    assert "Near-perfect correlation" in required[0].what_to_correct


def test_meridian_construction_refusal_is_user_required() -> None:
    feedback = build_meridian_refusal_feedback(
        run_id="run-eda",
        official_message="drop the listed variables that do not vary across geos",
    )
    assert feedback.status == "MERIDIAN_INPUT_REJECTED"
    assert feedback.resolution_status == "USER_REQUIRED"
    assert feedback.agent_can_fix is False
    assert feedback.safe_to_model is False
    assert feedback.source_type == "INPUT_REJECTION"
    assert feedback.official_message.startswith("drop the listed variables")
    assert feedback.meridian_accepted_input is False
    assert feedback.eda_ran is False
    assert feedback.corrections[0].owner == "USER_REQUIRED"
    assert feedback.corrections[0].agent_can_fix is False
    assert feedback.corrections[0].official_message
    assert feedback.corrections[0].prem3_interpretation


def test_error_finding_fails_eda_gate() -> None:
    receipt = _receipt(
        _finding(
            finding_id="PAIRWISE_CORRELATION.OVERALL.MULTICOLLINEARITY.ERROR.01",
            check_type="PAIRWISE_CORRELATION",
            report_category="variable_relationships",
            severity="ERROR",
            finding_cause="MULTICOLLINEARITY",
            explanation="Near-perfect correlation.",
        )
    )
    gate = evaluate_meridian_eda_gate(receipt=receipt, html_persisted=True)
    assert gate["status"] == "FAIL"
    assert gate["outcome"] == "EDA_BLOCKED"


def test_attention_passes_with_review_recommended() -> None:
    receipt = _receipt(
        _finding(
            finding_id="COST_PER_MEDIA_UNIT.NATIONAL.OUTLIER.ATTENTION.01",
            check_type="COST_PER_MEDIA_UNIT",
            report_category="spend_and_media_unit",
            severity="ATTENTION",
            finding_cause="OUTLIER",
            explanation="Cost-per-media-unit outlier.",
        )
    )
    gate = evaluate_meridian_eda_gate(receipt=receipt, html_persisted=True)
    assert gate["status"] == "PASS"
    assert gate["outcome"] == "PRE_MODELING_COMPLETE"
    assert gate["review_recommended"] is True


def test_info_only_passes_without_review_flag() -> None:
    gate = evaluate_meridian_eda_gate(receipt=_receipt(), html_persisted=True)
    assert gate["status"] == "PASS"
    assert gate["outcome"] == "PRE_MODELING_COMPLETE"
    assert gate["review_recommended"] is False
    assert gate["evidence"]["n_geos"] == 2
    assert gate["evidence"]["n_times"] == 10
    assert gate["evidence"]["n_knots"] == 10
    assert gate["evidence"]["n_controls"] == 3
    assert gate["evidence"]["n_treatments"] == 4
    assert gate["evidence"]["n_parameters"] == 20
    assert gate["evidence"]["n_data_points"] == 100
    assert gate["evidence"]["data_adequacy_ratio"] == 0.2
    assert gate["evidence"]["knots_identifiable"] is True


def test_missing_data_adequacy_fails_closed() -> None:
    receipt = _receipt()
    receipt.data_adequacy.n_knots = None
    with pytest.raises(ValidationBlockedError, match="data-adequacy parameters"):
        evaluate_meridian_eda_gate(receipt=receipt, html_persisted=True)


def test_unidentifiable_knots_fail_closed() -> None:
    receipt = _receipt()
    receipt.model_spec.source = EDA_MODEL_SPEC_GEO_TIME_INVARIANT
    receipt.model_spec.knots = 10
    receipt.model_spec.n_knots = 10
    receipt.model_spec.n_time = 10
    receipt.data_adequacy.n_knots = 10
    with pytest.raises(ValidationBlockedError, match="knots are not identifiable"):
        evaluate_meridian_eda_gate(receipt=receipt, html_persisted=True)


def test_serialize_captures_official_data_adequacy_parameters() -> None:
    class _Artifact:
        level = type("L", (), {"name": "OVERALL"})()
        n_geos = 4
        n_times = 131
        n_knots = 130
        n_controls = 3
        n_treatments = 4
        n_parameters = 80
        n_data_points = 524
        ratio = 80 / 524

    class _Outcome:
        check_type = type("C", (), {"name": "DATA_ADEQUACY"})()
        findings = []
        analysis_artifacts = [_Artifact()]

    started = utc_now()
    receipt = serialize_outcomes(
        [_Outcome()],
        run_id="run-eda",
        source={"model_scope": "geo"},
        meridian={"version": PINNED_GOOGLE_MERIDIAN},
        prior_context=MeridianEDAPriorContext(),
        html_report_uri="gs://bucket/eda/meridian_eda_report.html",
        eda_config_uri="gs://bucket/eda/meridian_eda_config.json",
        started_at=started,
        completed_at=started,
        duration_seconds=1.0,
        model_spec={
            "source": EDA_MODEL_SPEC_GEO_TIME_INVARIANT,
            "knots": 130,
            "n_knots": 130,
            "n_time": 131,
            "enable_aks": False,
            "approved_for_final_modeling": False,
        },
        compatibility_event={
            "official_error": (
                "The following controls variables do not vary across geos, "
                "making a model with n_knots=n_time unidentifiable: "
                "[b'music_center_promo']"
            ),
            "condition": {
                "geo_model": True,
                "n_time": 131,
                "time_only_variables": ["music_center_promo"],
            },
            "default_model_spec": {"knots": None, "effective_knots": 131},
            "eda_model_spec": {"knots": 130},
        },
    )
    assert receipt.data_adequacy.is_complete()
    assert receipt.data_adequacy.n_geos == 4
    assert receipt.data_adequacy.n_times == 131
    assert receipt.data_adequacy.n_knots == 130
    assert receipt.model_spec.knots == 130
    assert receipt.compatibility_event is not None
    assert receipt.compatibility_event.eda_model_spec["knots"] == 130
    assert receipt.compatibility_event.approved_for_final_modeling is False
    gate = evaluate_meridian_eda_gate(receipt=receipt, html_persisted=True)
    assert gate["status"] == "PASS"
    assert gate["evidence"]["model_spec_source"] == EDA_MODEL_SPEC_GEO_TIME_INVARIANT
    assert extract_data_adequacy(receipt.analysis_artifacts).n_parameters == 80


def test_missing_html_fails_closed() -> None:
    receipt = _receipt()
    receipt.html_report_uri = None
    with pytest.raises(ValidationBlockedError, match="HTML report missing"):
        evaluate_meridian_eda_gate(receipt=receipt, html_persisted=False)


def test_unknown_finding_id_is_rejected() -> None:
    receipt = _receipt()
    analysis = default_eda_analysis(receipt)
    analysis.blocking_findings = ["NOT-A-REAL-FINDING"]
    with pytest.raises(ValidationBlockedError, match="unknown finding IDs"):
        validate_eda_analysis(analysis, receipt)


def test_gemini_shaped_analysis_is_accepted_without_blocking_ready() -> None:
    receipt = _receipt()
    analysis = accept_eda_analysis(
        {
            "recommendations": [
                {
                    "message": "Review cost-per-media-unit outliers.",
                    "finding_ids": ["KPI_INVARIABILITY.OVERALL.VARIABILITY.INFO.01"],
                }
            ]
        },
        receipt,
    )
    assert analysis.executive_summary
    assert analysis.recommendations[0].recommendation.startswith("Review cost-per-media")
    assert analysis.recommendations[0].source_finding_ids == [
        "KPI_INVARIABILITY.OVERALL.VARIABILITY.INFO.01"
    ]
    fallback = accept_eda_analysis(
        {"recommendations": [{"finding_ids": ["NOT-A-REAL-FINDING"]}]},
        receipt,
    )
    assert fallback.analysis_source == "DETERMINISTIC_RECEIPT_SUMMARY"


def test_prior_disclosure_and_no_posterior() -> None:
    receipt = _receipt()
    assert receipt.purpose == "PRE_MODELING_EDA_ONLY"
    assert receipt.prior_context.source == "MERIDIAN_DEFAULT"
    assert receipt.prior_context.used_for == "EDA_PRIOR_DIAGNOSTICS_ONLY"
    assert receipt.prior_context.approved_for_final_modeling is False
    assert receipt.prior_context.n_draws_prior == 500
    assert receipt.prior_context.seed == 0
    assert receipt.posterior_sampling is False
    assert receipt.model_fitted is False
    with pytest.raises(ValueError, match="must not sample posterior"):
        MeridianEDAReceipt(
            run_id="run-eda",
            posterior_sampling=True,
            findings=[_finding()],
        )


def test_fingerprint_mismatch_fails_closed() -> None:
    frame = _dataset_a_frame()
    expected = fingerprint_frame(frame)
    other = frame.copy()
    other.loc[0, "kpi_orders"] = 99
    with pytest.raises(ValidationBlockedError, match="fingerprint does not match"):
        assert_fingerprint_matches(other, expected)


def test_agent_cannot_supply_eda_severities() -> None:
    with pytest.raises(SafetyViolationError, match="may not supply"):
        _sanitize_eda_analysis({"executive_summary": "ok", "error_count": 0})


def test_execute_fails_closed_without_meridian_or_job(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("app.tools.meridian_eda.meridian_eda_job_configured", lambda: False)
    monkeypatch.setattr("app.tools.meridian_eda.meridian_available", lambda: False)
    from app.tools.meridian_eda import execute_meridian_eda

    with pytest.raises(ValidationBlockedError, match="MODELREADY_EDA_JOB"):
        execute_meridian_eda(
            run_id="run-eda",
            frame=_dataset_a_frame(),
            intent=DATASET_A_MODEL_INTENT,
            contract=_dataset_a_contract(),
            output_dir=tmp_path,
            source_endpoint="project.dataset.table",
            content_fingerprint=fingerprint_frame(_dataset_a_frame()),
        )


def test_construct_eda_meridian_uses_official_n_knots_fallback() -> None:
    class _Kpi:
        shape = (2, 10)

    class _Data:
        kpi = _Kpi()

    class _Spec:
        def __init__(self, knots: int) -> None:
            self.knots = knots

    def _model(_input_data, model_spec=None, eda_spec=None):
        if model_spec is None:
            raise ValueError(
                "The following controls variables do not vary across geos, "
                "making a model with n_knots=n_time unidentifiable: "
                "[b'music_center_promo']"
            )
        return {"knots": model_spec.knots}

    mmm, context = _construct_eda_meridian(
        model_cls=_model,
        spec_cls=_Spec,
        input_data=_Data(),
        eda=object(),
    )
    assert mmm["knots"] == 9
    assert context["knots"] == 9
    assert context["n_knots"] == 9
    assert context["approved_for_final_modeling"] is False
    assert context["enable_aks"] is False
    assert context["source"] == EDA_MODEL_SPEC_GEO_TIME_INVARIANT
    event = context["compatibility_event"]
    assert event["event_type"] == "EDA_MODEL_SPEC_COMPATIBILITY_ADJUSTMENT"
    assert event["approved_for_final_modeling"] is False
    assert event["agent_selected"] is False
    assert event["eda_model_spec"]["knots"] == 9
    assert event["default_model_spec"]["effective_knots"] == 10
    assert event["condition"]["time_only_variables"] == ["music_center_promo"]


def test_eda_idempotency_is_run_fingerprint_version_and_config() -> None:
    mapping = mapping_from_contract(intent=DATASET_A_MODEL_INTENT, contract=_dataset_a_contract())
    config_fp = eda_config_fingerprint(mapping)
    first = eda_idempotency_key(
        run_id="run-eda",
        model_input_fingerprint="abc",
        meridian_version=PINNED_GOOGLE_MERIDIAN,
        eda_config_fingerprint_value=config_fp,
    )
    second = eda_idempotency_key(
        run_id="run-eda",
        model_input_fingerprint="abc",
        meridian_version=PINNED_GOOGLE_MERIDIAN,
        eda_config_fingerprint_value=config_fp,
    )
    other_run = eda_idempotency_key(
        run_id="run-other",
        model_input_fingerprint="abc",
        meridian_version=PINNED_GOOGLE_MERIDIAN,
        eda_config_fingerprint_value=config_fp,
    )
    other_input = eda_idempotency_key(
        run_id="run-eda",
        model_input_fingerprint="def",
        meridian_version=PINNED_GOOGLE_MERIDIAN,
        eda_config_fingerprint_value=config_fp,
    )
    assert first == second
    assert first != other_run
    assert first != other_input
    assert PINNED_GOOGLE_MERIDIAN == "1.8.0"


def test_run_ready_tools_include_meridian_eda() -> None:
    names = {fn.__name__ for fn in RUN_READY_TOOLS}
    assert names == {
        "initialize_dataset_run",
        "inspect_dataset_run",
        "apply_safe_remediations",
        "validate_and_publish_run",
        "run_meridian_eda",
        "complete_dataset_run",
    }


def test_eda_config_fingerprint_includes_model_spec_policy() -> None:
    mapping = mapping_from_contract(intent=DATASET_A_MODEL_INTENT, contract=_dataset_a_contract())
    config = canonical_eda_config(mapping)
    first = eda_config_fingerprint(mapping)
    assert config["model_spec_policy"] == EDA_MODEL_SPEC_POLICY
    original = EDA_MODEL_SPEC_POLICY["geo_time_invariant_control_fallback"]["knots_rule"]
    EDA_MODEL_SPEC_POLICY["geo_time_invariant_control_fallback"]["knots_rule"] = "changed"
    try:
        second = eda_config_fingerprint(mapping)
    finally:
        EDA_MODEL_SPEC_POLICY["geo_time_invariant_control_fallback"]["knots_rule"] = original
    assert first != second


def test_changed_input_fingerprint_cannot_reuse_receipt(tmp_path: Path) -> None:
    receipt = _receipt()
    receipt.model_input_fingerprint = "abc"
    receipt.eda_config_fingerprint = "cfg"
    receipt.idempotency_key = "key"
    receipt.meridian = {"version": PINNED_GOOGLE_MERIDIAN}
    receipt_path = tmp_path / "meridian_eda_receipt.json"
    receipt_path.write_text(receipt.model_dump_json(), encoding="utf-8")
    html_path = tmp_path / "meridian_eda_report.html"
    html_path.write_text("<html>official</html>", encoding="utf-8")
    assert (
        _matching_receipt(
            receipt_path,
            html_path=html_path,
            run_id="run-eda",
            content_fingerprint="CHANGED",
            config_fp="cfg",
            idem_key="key",
        )
        is None
    )
    with pytest.raises(ValidationBlockedError, match="idempotency does not match"):
        _assert_receipt_identity(
            receipt,
            run_id="run-eda",
            content_fingerprint="CHANGED",
            config_fp="cfg",
            idem_key="key",
        )


def test_changed_eda_config_cannot_reuse_receipt() -> None:
    receipt = _receipt()
    receipt.model_input_fingerprint = "abc"
    receipt.eda_config_fingerprint = "cfg"
    receipt.idempotency_key = "key"
    receipt.meridian = {"version": PINNED_GOOGLE_MERIDIAN}
    with pytest.raises(ValidationBlockedError, match="idempotency does not match"):
        _assert_receipt_identity(
            receipt,
            run_id="run-eda",
            content_fingerprint="abc",
            config_fp="CHANGED-CONFIG",
            idem_key="key",
        )


def test_changed_meridian_version_cannot_reuse_receipt() -> None:
    receipt = _receipt()
    receipt.model_input_fingerprint = "abc"
    receipt.eda_config_fingerprint = "cfg"
    receipt.idempotency_key = "key"
    receipt.meridian = {"version": "9.9.9"}
    with pytest.raises(ValidationBlockedError, match="meridian_version"):
        _assert_receipt_identity(
            receipt,
            run_id="run-eda",
            content_fingerprint="abc",
            config_fp="cfg",
            idem_key="key",
        )


def test_sample_posterior_is_structurally_blocked() -> None:
    class _Mmm:
        inference_data = None

        def sample_posterior(self, *_args, **_kwargs):
            return "POSTERIOR_RAN"

    mmm = _Mmm()
    _forbid_posterior(mmm)
    with pytest.raises(SafetyViolationError, match="sample_posterior is forbidden"):
        mmm.sample_posterior()
    _assert_no_posterior(mmm)


def test_gemini_cannot_declare_model_ready_over_official_error() -> None:
    receipt = _receipt(
        _finding(
            finding_id="PAIRWISE_CORRELATION.OVERALL.MULTICOLLINEARITY.ERROR.01",
            check_type="PAIRWISE_CORRELATION",
            report_category="variable_relationships",
            severity="ERROR",
            finding_cause="MULTICOLLINEARITY",
            explanation="Near-perfect correlation.",
        )
    )
    analysis = accept_eda_analysis(
        {
            "recommended_handoff_action": "MODEL_READY",
            "executive_summary": "0 ERROR. MODEL_READY.",
            "blocking_findings": [],
        },
        receipt,
    )
    gate = evaluate_meridian_eda_gate(receipt=receipt, html_persisted=True)
    assert gate["status"] == "FAIL"
    assert gate["outcome"] == "EDA_BLOCKED"
    assert analysis.recommended_handoff_action == "MODEL_READY"
    with pytest.raises(SafetyViolationError, match="may not supply"):
        _sanitize_eda_analysis({"MODEL_READY": True, "error_count": 0})


def test_extract_time_only_variables_from_official_text() -> None:
    names = extract_time_only_variables(
        "The following controls variables do not vary across geos, "
        "making a model with n_knots=n_time unidentifiable: [b'music_center_promo']"
    )
    assert names == ["music_center_promo"]


@pytest.mark.meridian_eda
def test_official_meridian_package_importable() -> None:
    if not meridian_available():
        pytest.skip("google-meridian is not installed in this interpreter")
    import meridian
    from meridian.model.eda import meridian_eda

    assert hasattr(meridian_eda.MeridianEDA, "generate_and_save_report")
    assert hasattr(meridian, "__version__")
