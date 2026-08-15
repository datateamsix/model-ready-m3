"""Official google-meridian EDA execution. Isolated from default M3 imports.

This module is the only place that imports Meridian. Default CI must not import
it. Production Cloud Run should invoke it in a dedicated worker interpreter
when google-meridian cannot share the ADK/pandas 3 runtime.
"""

from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path
from typing import Any

from app.core.errors import SafetyViolationError, ValidationBlockedError
from app.core.meridian_eda_contracts import (
    DEFAULT_PRIOR_N_DRAW,
    DEFAULT_PRIOR_SEED,
    PINNED_GOOGLE_MERIDIAN,
    MeridianEDAPriorContext,
    MeridianInputMapping,
)

POSTERIOR_GROUP = "posterior"


def meridian_available() -> bool:
    try:
        import meridian  # noqa: F401
    except ImportError:
        return False
    return True


def require_meridian() -> None:
    if not meridian_available():
        raise ValidationBlockedError(
            "Official google-meridian is not installed in this interpreter. "
            "Pre-modeling EDA must use the published package, not a substitute."
        )


def _forbid_posterior(mmm: Any) -> None:
    def _blocked(*_args: Any, **_kwargs: Any) -> Any:
        raise SafetyViolationError(
            "sample_posterior is forbidden during pre-modeling EDA."
        )

    mmm.sample_posterior = _blocked


def _assert_no_posterior(mmm: Any) -> None:
    inference = getattr(mmm, "inference_data", None)
    groups = []
    if inference is not None and hasattr(inference, "groups"):
        groups = list(inference.groups())
    if POSTERIOR_GROUP in groups:
        raise SafetyViolationError(
            "Posterior samples were found after EDA. Pre-modeling EDA must not fit the model."
        )


def prepare_input_dataframe(frame: Any, mapping: MeridianInputMapping) -> Any:
    """Coerce time labels for official DataFrameInputDataBuilder. No EDA math."""
    prepared = frame.copy()
    time_col = mapping.time_col
    if time_col in prepared.columns:
        prepared[time_col] = prepared[time_col].astype(str).str.slice(0, 10)
    return prepared


def build_input_data(frame: Any, mapping: MeridianInputMapping) -> Any:
    from meridian.data import data_frame_input_data_builder as data_builder

    builder = data_builder.DataFrameInputDataBuilder(
        kpi_type=mapping.kpi_type,
        default_kpi_column=mapping.kpi_col,
        default_revenue_per_kpi_column=mapping.revenue_per_kpi_col,
        default_time_column=mapping.time_col,
        default_geo_column=mapping.geo_col or "geo",
        default_population_column=mapping.population_col or "population",
        default_media_time_column=mapping.time_col,
    )
    prepared = prepare_input_dataframe(frame, mapping)
    builder = (
        builder.with_kpi(prepared, kpi_col=mapping.kpi_col)
        .with_media(
            prepared,
            media_cols=mapping.media_cols,
            media_spend_cols=mapping.media_spend_cols,
            media_channels=mapping.media_channels,
        )
    )
    if mapping.kpi_type == "non_revenue":
        builder = builder.with_revenue_per_kpi(
            prepared, revenue_per_kpi_col=mapping.revenue_per_kpi_col
        )
    if mapping.population_col:
        builder = builder.with_population(prepared, population_col=mapping.population_col)
    if mapping.control_cols:
        builder = builder.with_controls(prepared, control_cols=mapping.control_cols)
    if mapping.organic_media_cols:
        builder = builder.with_organic_media(
            prepared,
            organic_media_cols=mapping.organic_media_cols,
            organic_media_channels=mapping.organic_media_channels,
        )
    return builder.build()


def effective_eda_config(
    *,
    mapping: MeridianInputMapping,
    prior: MeridianEDAPriorContext,
    meridian_version: str,
    eda_spec: Any,
) -> dict[str, Any]:
    kpi_spec = eda_spec.kpi_invariability_spec
    corr_spec = eda_spec.pairwise_corr_spec
    std_spec = eda_spec.std_spec
    vif_spec = eda_spec.vif_spec
    aggregation = eda_spec.aggregation_config
    return {
        "purpose": "PRE_MODELING_EDA_ONLY",
        "model_context": "EDA_MODEL_CONTEXT",
        "posterior_sampling": False,
        "model_fitted": False,
        "kpi_type": mapping.kpi_type,
        "kpi_type_derivation": mapping.kpi_type_derivation,
        "mapping": mapping.model_dump(mode="json"),
        "meridian_version": meridian_version,
        "pinned_google_meridian": PINNED_GOOGLE_MERIDIAN,
        "python_version": platform.python_version(),
        "backend": "cpu",
        "eda_spec": {
            "source": "MERIDIAN_DEFAULT",
            "aggregation_config": {
                "control_variables": sorted(aggregation.control_variables),
                "non_media_treatments": sorted(aggregation.non_media_treatments),
            },
            "kpi_invariability_spec": {"std_threshold": kpi_spec.std_threshold},
            "pairwise_corr_spec": {
                "overall_threshold": corr_spec.overall_threshold,
                "geo_threshold": corr_spec.geo_threshold,
                "national_threshold": corr_spec.national_threshold,
            },
            "std_spec": {
                "geo_std_threshold": std_spec.geo_std_threshold,
                "national_std_threshold": std_spec.national_std_threshold,
            },
            "vif_spec": {
                "geo_threshold": vif_spec.geo_threshold,
                "overall_threshold": vif_spec.overall_threshold,
                "national_threshold": vif_spec.national_threshold,
                "std_threshold": vif_spec.std_threshold,
            },
        },
        "prior_context": prior.model_dump(mode="json"),
    }


def collect_official_outcomes(mmm_eda: Any, *, is_national: bool) -> list[Any]:
    outcomes: list[Any] = []
    engine = mmm_eda.eda_engine
    outcomes.append(engine.check_data_param_ratio())
    outcomes.append(mmm_eda.critical_outcomes.kpi_invariability)
    outcomes.append(mmm_eda.critical_outcomes.pairwise_correlation)
    outcomes.append(mmm_eda.critical_outcomes.multicollinearity)
    outcomes.append(engine.check_std())
    outcomes.append(engine.check_cost_per_media_unit())
    outcomes.append(engine.check_prior_probability())
    if is_national:
        return outcomes
    outcomes.append(engine.check_population_corr_raw_media())
    outcomes.append(engine.check_population_corr_scaled_treatment_control())
    outcomes.append(engine.check_variable_geo_time_collinearity())
    outcomes.append(mmm_eda.national_cost_per_media_unit_check_outcome)
    outcomes.append(mmm_eda.national_stdev_check_outcome)
    outcomes.append(mmm_eda.national_pairwise_correlation_check_outcome)
    outcomes.append(mmm_eda.geo_cost_per_media_unit_check_outcome)
    outcomes.append(mmm_eda.geo_stdev_check_outcome)
    return outcomes


def run_official_meridian_eda(
    *,
    frame: Any,
    mapping: MeridianInputMapping,
    output_dir: str | Path,
    n_draws_prior: int = DEFAULT_PRIOR_N_DRAW,
    seed: int = DEFAULT_PRIOR_SEED,
) -> dict[str, Any]:
    require_meridian()
    import meridian
    from meridian.model import model
    from meridian.model.eda import eda_spec, meridian_eda

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    prior = MeridianEDAPriorContext(
        source="MERIDIAN_DEFAULT",
        used_for="EDA_PRIOR_DIAGNOSTICS_ONLY",
        approved_for_final_modeling=False,
        n_draws_prior=n_draws_prior,
        seed=seed,
    )
    input_data = build_input_data(frame, mapping)
    spec = eda_spec.EDASpec()
    mmm = model.Meridian(input_data, eda_spec=spec)
    _forbid_posterior(mmm)
    mmm_eda = meridian_eda.MeridianEDA(mmm, n_draws_prior=n_draws_prior, seed=seed)
    html_name = "meridian_eda_report.html"
    mmm_eda.generate_and_save_report(filename=html_name, filepath=str(output))
    _assert_no_posterior(mmm)
    html_path = output / html_name
    if not html_path.is_file() or html_path.stat().st_size <= 0:
        raise ValidationBlockedError("Official Meridian EDA HTML report was not generated.")
    is_national = bool(getattr(mmm, "is_national", mapping.model_scope == "national"))
    outcomes = collect_official_outcomes(mmm_eda, is_national=is_national)
    version = getattr(meridian, "__version__", PINNED_GOOGLE_MERIDIAN)
    config = effective_eda_config(
        mapping=mapping,
        prior=prior,
        meridian_version=str(version),
        eda_spec=spec,
    )
    return {
        "html_path": str(html_path),
        "config": config,
        "outcomes": outcomes,
        "prior_context": prior,
        "meridian_version": str(version),
        "python_version": platform.python_version(),
        "backend": "cpu",
        "posterior_sampling": False,
        "model_fitted": False,
        "is_national": is_national,
    }


def main() -> int:
    """Subprocess entry for a dedicated Meridian EDA worker interpreter."""
    if len(sys.argv) != 2:
        print("usage: python -m app.tools.meridian_eda_runtime <request.json>", file=sys.stderr)
        return 2
    request_path = Path(sys.argv[1])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    try:
        import pandas as pd

        frame = pd.read_csv(request["frame_path"])
        mapping = MeridianInputMapping.model_validate(request["mapping"])
        result = run_official_meridian_eda(
            frame=frame,
            mapping=mapping,
            output_dir=request["output_dir"],
            n_draws_prior=int(request.get("n_draws_prior", DEFAULT_PRIOR_N_DRAW)),
            seed=int(request.get("seed", DEFAULT_PRIOR_SEED)),
        )
        marker = Path(request["output_dir"]) / "meridian_eda_runtime_ok.json"
        marker.write_text(
            json.dumps(
                {
                    "status": "OK",
                    "html_path": result["html_path"],
                    "meridian_version": result["meridian_version"],
                    "python_version": result["python_version"],
                    "posterior_sampling": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return 0
    except Exception as exc:
        out_dir = Path(request.get("output_dir") or request_path.parent)
        failure = out_dir / "meridian_eda_runtime_fail.json"
        failure.write_text(
            json.dumps(
                {"status": "FAIL", "error": str(exc), "traceback": traceback.format_exc()},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
