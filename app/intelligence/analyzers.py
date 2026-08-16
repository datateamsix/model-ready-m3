"""Internal deterministic PreM3 pre-EDA calculators.

These are ordinary functions. They are not agent-facing tools and they do
not emit official Meridian EDA findings.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.intelligence.contracts import (
    AuthorityRef,
    DecisionClass,
    KnowledgeClass,
    MissingnessClass,
    Prem3DiagnosticDisposition,
    Prem3PreEdaFinding,
    PrePeriodCoverage,
    ResponsibleActor,
)
from app.intelligence.registry import load_intelligence_config, rule_authority
from app.intelligence.snapshot import ChannelSpec, DiagnosticSnapshot


def analyze_history_sufficiency(snapshot: DiagnosticSnapshot) -> dict[str, Any]:
    frame = snapshot.frame
    time_col = snapshot.time_column
    times = pd.to_datetime(frame[time_col], errors="coerce").dropna().sort_values()
    unique_times = pd.DatetimeIndex(times.unique())
    n_periods = int(len(unique_times))
    first = unique_times.min().strftime("%Y-%m-%d") if n_periods else None
    last = unique_times.max().strftime("%Y-%m-%d") if n_periods else None
    duration_days = int((unique_times.max() - unique_times.min()).days) if n_periods else 0
    config = load_intelligence_config().history
    geo = snapshot.n_geos > 1
    preferred = (
        config.preferred_geo_weekly_periods if geo else config.preferred_national_weekly_periods
    )
    preferred_years = (
        config.preferred_geo_weekly_years if geo else config.preferred_national_weekly_years
    )
    observed = {
        "first_kpi_period": first,
        "last_kpi_period": last,
        "n_periods": n_periods,
        "time_grain": snapshot.time_grain,
        "geo_count": snapshot.n_geos,
        "national": snapshot.n_geos == 1,
        "calendar_duration_days": duration_days,
        "continuity_established_by_readiness_contract": True,
    }
    guidance = {
        "preferred_periods": preferred,
        "preferred_years": preferred_years,
        "knowledge_class": config.knowledge_class,
        "blocks_model_ready": False,
        "structural_break_caveat": (
            "Longer history is not automatically better when structural breaks exist."
        ),
    }
    disposition = (
        Prem3DiagnosticDisposition.PASS
        if n_periods >= preferred
        else Prem3DiagnosticDisposition.REVIEW_RECOMMENDED
    )
    interpretation = (
        "Observed history meets the preferred geo/national weekly planning range."
        if disposition is Prem3DiagnosticDisposition.PASS
        else "Observed history is shorter than preferred planning guidance."
    )
    finding = _finding(
        finding_id="PREM3-PREEDA-HISTORY",
        dimension="HISTORY",
        disposition=disposition,
        knowledge_class=KnowledgeClass.MMM_EVIDENCE_HEURISTIC,
        title="History sufficiency",
        calculated="KPI period count, date range, grain, and geo/national structure.",
        evidence=observed,
        why="History length affects identification of seasonality, carryover, and controls.",
        practice=(
            "Official planning guidance prefers about 2 years geo-weekly or 3 years "
            "national-weekly. This is not an independent MODEL_READY blocker."
        ),
        action=(
            "If history is short, request additional source periods rather than fabricating them."
        ),
        actor=ResponsibleActor.DATA_ENGINEER if n_periods < preferred else ResponsibleActor.PREM3,
        review=disposition is Prem3DiagnosticDisposition.REVIEW_RECOMMENDED,
        rule_id="PREM3-PB-001",
    )
    return {
        "observed_fact": observed,
        "guidance": guidance,
        "interpretation": interpretation,
        "authority": rule_authority("PREM3-PB-001"),
        "disposition": disposition.value,
        "finding": finding.model_dump(mode="json"),
    }


def check_pre_period_media(snapshot: DiagnosticSnapshot) -> dict[str, Any]:
    frame = snapshot.frame
    time_col = snapshot.time_column
    kpi = snapshot.kpi_column
    kpi_times = pd.to_datetime(frame.loc[frame[kpi].notna(), time_col], errors="coerce")
    kpi_start = kpi_times.min() if not kpi_times.empty else None
    channels: list[dict[str, Any]] = []
    classifications: list[str] = []
    for spec in snapshot.channels:
        media_col = spec.impressions_column or spec.organic_column
        spend_col = spec.spend_column
        if media_col is None or media_col not in frame.columns:
            channels.append(
                {
                    "channel": spec.channel,
                    "coverage": PrePeriodCoverage.UNKNOWN.value,
                    "reason": "media column missing from verified input",
                }
            )
            classifications.append(PrePeriodCoverage.UNKNOWN.value)
            continue
        media_start = _first_positive(frame, time_col, media_col, spend_col)
        pre_mask = (
            pd.to_datetime(frame[time_col], errors="coerce") < kpi_start
            if kpi_start is not None
            else pd.Series(False, index=frame.index)
        )
        pre_rows = int(pre_mask.sum())
        if pre_rows == 0:
            coverage = PrePeriodCoverage.UNKNOWN
            reason = (
                "Verified model input contains no periods before the first KPI date. "
                "Absence of pre-KPI rows is not confirmed inactivity."
            )
        else:
            pre = frame.loc[pre_mask]
            positive = _positive_mask(pre, media_col, spend_col)
            if bool(positive.any()) and bool(positive.all()):
                coverage = PrePeriodCoverage.PRESENT
            elif bool(positive.any()):
                coverage = PrePeriodCoverage.PARTIAL
            else:
                coverage = PrePeriodCoverage.ABSENT
            reason = f"pre_kpi_periods={pre_rows}"
        channels.append(
            {
                "channel": spec.channel,
                "kpi_start": None if kpi_start is None else kpi_start.strftime("%Y-%m-%d"),
                "media_start": media_start,
                "pre_kpi_row_count": pre_rows,
                "coverage": coverage.value,
                "reason": reason,
                "zero_not_assumed": True,
            }
        )
        classifications.append(coverage.value)
    overall = _overall_coverage(classifications)
    finding = _finding(
        finding_id="PREM3-PREEDA-PRE-PERIOD-MEDIA",
        dimension="PRE_PERIOD_MEDIA",
        disposition=(
            Prem3DiagnosticDisposition.NOT_APPLICABLE
            if overall == PrePeriodCoverage.UNKNOWN.value
            else Prem3DiagnosticDisposition.REVIEW_RECOMMENDED
            if overall != PrePeriodCoverage.PRESENT.value
            else Prem3DiagnosticDisposition.PASS
        ),
        knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
        title="Pre-period media coverage",
        calculated="KPI start vs media start and pre-KPI coverage by channel.",
        evidence={"channels": channels, "overall": overall},
        why="Carryover identification is weaker when pre-period media is missing or unknown.",
        practice=(
            "Unknown absence is not confirmed inactivity. Do not zero-fill media without "
            "source evidence."
        ),
        action="Obtain earlier media exports if pre-period coverage is unknown or absent.",
        actor=ResponsibleActor.DATA_ENGINEER,
        review=overall != PrePeriodCoverage.PRESENT.value,
        rule_id="PREM3-MISS-001",
        channels=[item["channel"] for item in channels],
    )
    return {
        "overall": overall,
        "channels": channels,
        "unknown_absence_is_not_zero": True,
        "finding": finding.model_dump(mode="json"),
    }


def analyze_channel_spend_distribution(snapshot: DiagnosticSnapshot) -> dict[str, Any]:
    threshold = load_intelligence_config().spend.low_spend_share_review
    rows: list[dict[str, Any]] = []
    totals: dict[str, float] = {}
    for spec in snapshot.channels:
        if not spec.spend_column or spec.spend_column not in snapshot.frame.columns:
            continue
        total = float(
            pd.to_numeric(snapshot.frame[spec.spend_column], errors="coerce").fillna(0).sum()
        )
        totals[spec.channel] = total
        rows.append({"channel": spec.channel, "total_spend": round(total, 6)})
    grand = float(sum(totals.values()))
    for row in rows:
        share = (row["total_spend"] / grand) if grand else 0.0
        row["share_of_spend"] = round(share, 6)
        row["scope_review_candidate"] = bool(share > 0 and share < threshold)
        row["auto_drop"] = False
    rows.sort(key=lambda item: item["total_spend"], reverse=True)
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    bottom = [row["channel"] for row in rows if row["scope_review_candidate"]]
    herfindahl = round(sum(row["share_of_spend"] ** 2 for row in rows), 6) if rows else None
    finding = _finding(
        finding_id="PREM3-PREEDA-SPEND-DISTRIBUTION",
        dimension="CHANNEL_SPEND_DISTRIBUTION",
        disposition=(
            Prem3DiagnosticDisposition.REVIEW_RECOMMENDED
            if bottom
            else Prem3DiagnosticDisposition.PASS
        ),
        knowledge_class=KnowledgeClass.MMM_EVIDENCE_HEURISTIC,
        title="Channel spend distribution",
        calculated="Total spend, share, rank, and concentration from verified spend columns.",
        evidence={
            "total_spend": round(grand, 6),
            "channels": rows,
            "bottom_share_candidates": bottom,
            "herfindahl": herfindahl,
            "low_share_review_threshold": threshold,
        },
        why="Very low-share channels can add parameters without much execution support.",
        practice="Low share can generate a SCOPE_REVIEW_CANDIDATE. It is never AUTO_DROP.",
        action="Review low-share channels with the analyst. Do not merge autonomously.",
        actor=ResponsibleActor.ANALYST,
        review=bool(bottom),
        rule_id="PREM3-SCOPE-001",
        channels=[row["channel"] for row in rows],
    )
    return {
        "total_spend": round(grand, 6),
        "channels": rows,
        "bottom_share_candidates": bottom,
        "auto_drop": False,
        "finding": finding.model_dump(mode="json"),
    }


def analyze_media_variation(snapshot: DiagnosticSnapshot) -> dict[str, Any]:
    channels: list[dict[str, Any]] = []
    weak: list[str] = []
    for spec in snapshot.channels:
        series = _media_series(snapshot.frame, spec)
        if series is None:
            continue
        numeric = pd.to_numeric(series, errors="coerce")
        nonzero = numeric[numeric > 0]
        geo_col = snapshot.geo_column
        time_col = snapshot.time_column
        time_cv = _cv(numeric.groupby(snapshot.frame[time_col]).sum()) if time_col else None
        geo_cv = None
        if geo_col and geo_col in snapshot.frame.columns:
            geo_cv = _cv(numeric.groupby(snapshot.frame[geo_col]).sum())
        zero_share = float((numeric.fillna(0) <= 0).mean())
        stats = {
            "channel": spec.channel,
            "overall_std": _safe_float(numeric.std()),
            "overall_cv": _cv(numeric),
            "nonzero_cv": _cv(nonzero) if not nonzero.empty else None,
            "zero_share": round(zero_share, 6),
            "go_dark_periods": int((numeric.fillna(0) <= 0).sum()),
            "time_cv": time_cv,
            "geo_cv": geo_cv,
            "outlier_dependence": _outlier_share(numeric),
            "near_constant": bool(_cv(numeric) is not None and _cv(numeric) < 0.05),
        }
        if stats["near_constant"] or (
            stats["overall_cv"] is not None and stats["overall_cv"] < 0.1
        ):
            weak.append(spec.channel)
            stats["limited_historical_execution_variation"] = True
        else:
            stats["limited_historical_execution_variation"] = False
        stats["causal_effect_not_established"] = False
        channels.append(stats)
    finding = _finding(
        finding_id="PREM3-PREEDA-MEDIA-VARIATION",
        dimension="CHANNEL_VARIATION",
        disposition=(
            Prem3DiagnosticDisposition.REVIEW_RECOMMENDED
            if weak
            else Prem3DiagnosticDisposition.PASS
        ),
        knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
        title="Media variation",
        calculated="Time/geo variation, go-dark frequency, and outlier dependence.",
        evidence={"channels": channels, "limited_variation_channels": weak},
        why="Limited execution variation weakens the empirical support for response estimation.",
        practice=(
            "Report limited historical execution variation. Do not conclude that the model "
            "cannot estimate a causal effect unless an official/contract condition says so."
        ),
        action="Review weak-variation channels with the modeler.",
        actor=ResponsibleActor.MODELER,
        review=bool(weak),
        rule_id="PREM3-SCOPE-001",
        channels=[item["channel"] for item in channels],
    )
    return {
        "channels": channels,
        "limited_variation_channels": weak,
        "finding": finding.model_dump(mode="json"),
    }


def analyze_spend_range(snapshot: DiagnosticSnapshot) -> dict[str, Any]:
    channels: list[dict[str, Any]] = []
    limited: list[str] = []
    for spec in snapshot.channels:
        if not spec.spend_column or spec.spend_column not in snapshot.frame.columns:
            continue
        numeric = pd.to_numeric(snapshot.frame[spec.spend_column], errors="coerce")
        nonzero = numeric[numeric > 0]
        stats = {
            "channel": spec.channel,
            "min": _safe_float(numeric.min()),
            "max": _safe_float(numeric.max()),
            "nonzero_min": _safe_float(nonzero.min()) if not nonzero.empty else None,
            "p25": _safe_float(numeric.quantile(0.25)),
            "p50": _safe_float(numeric.quantile(0.50)),
            "p75": _safe_float(numeric.quantile(0.75)),
            "zero_periods": int((numeric.fillna(0) <= 0).sum()),
            "relative_range": _relative_range(numeric),
        }
        if stats["relative_range"] is not None and stats["relative_range"] < 0.2:
            limited.append(spec.channel)
            stats["limited_observed_execution_support"] = True
        else:
            stats["limited_observed_execution_support"] = False
        stats["roi_not_inferred"] = True
        channels.append(stats)
    finding = _finding(
        finding_id="PREM3-PREEDA-SPEND-RANGE",
        dimension="SPEND_RANGE",
        disposition=(
            Prem3DiagnosticDisposition.REVIEW_RECOMMENDED
            if limited
            else Prem3DiagnosticDisposition.PASS
        ),
        knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
        title="Spend range",
        calculated="Min/max/quantiles and relative historical spend range by channel.",
        evidence={"channels": channels, "limited_range_channels": limited},
        why="Narrow observed spend ranges limit the empirical support for later response curves.",
        practice=(
            "This is pre-modeling evidence only. Do not produce ROI or budget recommendations."
        ),
        action="Note limited execution support for modeler review.",
        actor=ResponsibleActor.MODELER,
        review=bool(limited),
        rule_id="PREM3-SCOPE-001",
        channels=[item["channel"] for item in channels],
    )
    return {
        "channels": channels,
        "limited_range_channels": limited,
        "finding": finding.model_dump(mode="json"),
    }


def analyze_geo_coverage(snapshot: DiagnosticSnapshot) -> dict[str, Any]:
    geo_col = snapshot.geo_column
    if not geo_col or geo_col not in snapshot.frame.columns:
        finding = _finding(
            finding_id="PREM3-PREEDA-GEO-COVERAGE",
            dimension="GEO_COVERAGE",
            disposition=Prem3DiagnosticDisposition.NOT_APPLICABLE,
            knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
            title="Geo coverage",
            calculated="National model has no geo dimension.",
            evidence={"geo_count": 1, "national": True},
            why="Geo coverage is not applicable to a national model.",
            practice="Do not autonomously drop geos.",
            action="No geo action.",
            actor=ResponsibleActor.PREM3,
            review=False,
            rule_id="PREM3-SCOPE-001",
        )
        return {"national": True, "geo_count": 1, "finding": finding.model_dump(mode="json")}
    frame = snapshot.frame
    geos = sorted(frame[geo_col].astype(str).unique().tolist())
    rows_per_geo = frame.groupby(geo_col, sort=True).size().astype(int).to_dict()
    kpi = pd.to_numeric(frame[snapshot.kpi_column], errors="coerce").fillna(0)
    contrib = (kpi.groupby(frame[geo_col]).sum() / kpi.sum()) if float(kpi.sum()) else pd.Series()
    contribution = {str(key): round(float(value), 6) for key, value in contrib.items()}
    low = [geo for geo, share in contribution.items() if share < 0.05]
    pop_cov = None
    pop_col = snapshot.population_column
    if pop_col and pop_col in frame.columns:
        pop = pd.to_numeric(frame[pop_col], errors="coerce")
        pop_cov = {
            str(geo): _safe_float(pop[frame[geo_col] == geo].iloc[0]) if not pop.empty else None
            for geo in geos
        }
    finding = _finding(
        finding_id="PREM3-PREEDA-GEO-COVERAGE",
        dimension="GEO_COVERAGE",
        disposition=(
            Prem3DiagnosticDisposition.REVIEW_RECOMMENDED
            if low
            else Prem3DiagnosticDisposition.PASS
        ),
        knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
        title="Geo coverage",
        calculated="Geo count, rows per geo, KPI contribution, and population coverage.",
        evidence={
            "geo_count": len(geos),
            "geos": geos,
            "rows_per_geo": {str(k): int(v) for k, v in rows_per_geo.items()},
            "kpi_contribution": contribution,
            "low_contribution_review_candidates": low,
            "population_coverage": pop_cov,
            "autonomous_geo_drop": False,
        },
        why="Very-low-contribution geos can add parameters without much outcome support.",
        practice="Dropping geos remains APPROVAL_REQUIRED / MODELER_REVIEW_REQUIRED.",
        action="Do not drop geos autonomously.",
        actor=ResponsibleActor.MODELER,
        review=bool(low),
        rule_id="PREM3-SCOPE-001",
    )
    return {
        "geo_count": len(geos),
        "geos": geos,
        "rows_per_geo": {str(k): int(v) for k, v in rows_per_geo.items()},
        "kpi_contribution": contribution,
        "low_contribution_review_candidates": low,
        "population_coverage": pop_cov,
        "decision_class": DecisionClass.APPROVAL_REQUIRED.value,
        "finding": finding.model_dump(mode="json"),
    }


def analyze_population_relationships(snapshot: DiagnosticSnapshot) -> dict[str, Any]:
    pop_col = snapshot.population_column
    if not pop_col or pop_col not in snapshot.frame.columns:
        finding = _finding(
            finding_id="PREM3-PREEDA-POPULATION",
            dimension="POPULATION_RELATIONSHIPS",
            disposition=Prem3DiagnosticDisposition.NOT_APPLICABLE,
            knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
            title="Population relationships",
            calculated="No population column in the verified contract.",
            evidence={},
            why="Population scaling is a modeler configuration choice.",
            practice="Do not automatically pre-scale data.",
            action="No population action.",
            actor=ResponsibleActor.MODELER,
            review=False,
            rule_id="PREM3-VIF-001",
        )
        return {"applicable": False, "finding": finding.model_dump(mode="json")}
    frame = snapshot.frame
    pop = pd.to_numeric(frame[pop_col], errors="coerce")
    kpi = pd.to_numeric(frame[snapshot.kpi_column], errors="coerce")
    raw_corr = _corr(kpi, pop)
    scaled_looking = False
    if pop.gt(0).all():
        ratio = kpi / pop
        scaled_looking = bool(_cv(ratio) is not None and _cv(ratio) < 0.15)
    media_corrs = []
    for spec in snapshot.channels:
        series = _media_series(frame, spec)
        if series is None:
            continue
        media_corrs.append(
            {"channel": spec.channel, "correlation_with_population": _corr(series, pop)}
        )
    finding = _finding(
        finding_id="PREM3-PREEDA-POPULATION",
        dimension="POPULATION_RELATIONSHIPS",
        disposition=Prem3DiagnosticDisposition.REVIEW_RECOMMENDED
        if scaled_looking
        else Prem3DiagnosticDisposition.PASS,
        knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
        title="Population relationships",
        calculated="KPI/media correlations with population and scaled-looking ratio check.",
        evidence={
            "kpi_population_correlation": raw_corr,
            "already_population_scaled_looking": scaled_looking,
            "media_population_correlations": media_corrs,
            "autonomous_prescale": False,
            "control_population_scaling_id_unchanged": True,
        },
        why="Population scaling changes how geo size enters the model.",
        practice=(
            "Do not automatically pre-scale. Do not change control_population_scaling_id "
            "or final model configuration autonomously."
        ),
        action="Leave population scaling to the modeler.",
        actor=ResponsibleActor.MODELER,
        review=scaled_looking,
        rule_id="PREM3-VIF-001",
    )
    return {
        "kpi_population_correlation": raw_corr,
        "already_population_scaled_looking": scaled_looking,
        "media_population_correlations": media_corrs,
        "autonomous_prescale": False,
        "finding": finding.model_dump(mode="json"),
    }


def analyze_collinearity(snapshot: DiagnosticSnapshot) -> dict[str, Any]:
    config = load_intelligence_config().collinearity
    columns = [
        *snapshot.contract.media.values(),
        *snapshot.contract.organic_media,
        *snapshot.contract.controls,
    ]
    present = [name for name in columns if name in snapshot.frame.columns]
    if len(present) < 2:
        finding = _finding(
            finding_id="PREM3-PREEDA-COLLINEARITY",
            dimension="COLLINEARITY",
            disposition=Prem3DiagnosticDisposition.NOT_APPLICABLE,
            knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
            title="Collinearity",
            calculated="Fewer than two numeric treatment/control columns.",
            evidence={},
            why="Collinearity diagnostics require at least two variables.",
            practice="Official Meridian EDA owns official VIF/correlation defaults.",
            action="No collinearity action.",
            actor=ResponsibleActor.PREM3,
            review=False,
            rule_id="PREM3-VIF-001",
        )
        return {"applicable": False, "finding": finding.model_dump(mode="json")}
    matrix = snapshot.frame[present].apply(pd.to_numeric, errors="coerce")
    corr = matrix.corr(numeric_only=True)
    pairs: list[dict[str, Any]] = []
    official_pairs: list[dict[str, Any]] = []
    advisory_pairs: list[dict[str, Any]] = []
    names = list(corr.columns)
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            value = corr.loc[left, right]
            if pd.isna(value):
                continue
            item = {"left": left, "right": right, "abs_correlation": round(abs(float(value)), 6)}
            pairs.append(item)
            if item["abs_correlation"] >= config.official_pairwise_abs:
                official_pairs.append(item)
            elif item["abs_correlation"] >= config.prem3_advisory_pairwise_abs:
                advisory_pairs.append(item)
    vif_rows = _vif_table(matrix)
    official_vif = [row for row in vif_rows if row["vif"] >= config.official_vif]
    advisory_vif = [
        row
        for row in vif_rows
        if row["vif"] >= config.prem3_advisory_vif and row["vif"] < config.official_vif
    ]
    disposition = Prem3DiagnosticDisposition.PASS
    if official_pairs or official_vif:
        disposition = Prem3DiagnosticDisposition.REVIEW_RECOMMENDED
    elif advisory_pairs or advisory_vif:
        disposition = Prem3DiagnosticDisposition.REVIEW_RECOMMENDED
    finding = _finding(
        finding_id="PREM3-PREEDA-COLLINEARITY",
        dimension="COLLINEARITY",
        disposition=disposition,
        knowledge_class=KnowledgeClass.MMM_EVIDENCE_HEURISTIC,
        title="Collinearity (PreM3 advisory)",
        calculated="Pairwise correlation and VIF on treatments and controls.",
        evidence={
            "official_thresholds": {
                "vif": config.official_vif,
                "pairwise_abs": config.official_pairwise_abs,
                "authority": config.official_authority,
            },
            "prem3_advisory_thresholds": {
                "vif": config.prem3_advisory_vif,
                "pairwise_abs": config.prem3_advisory_pairwise_abs,
                "authority": config.prem3_authority,
            },
            "pairs_at_official": official_pairs,
            "pairs_at_prem3_advisory": advisory_pairs,
            "vif": vif_rows,
            "vif_at_official": official_vif,
            "vif_at_prem3_advisory": advisory_vif,
            "official_meridian_edaspec_unchanged": True,
            "finding_origin": "PREM3_PRE_EDA",
        },
        why="Collinear treatments/controls can make later effect estimates fragile.",
        practice=(
            "Official Meridian defaults remain VIF 1000 and |r| 0.999 during official EDA. "
            "Tighter PreM3 thresholds are advisory only."
        ),
        action="Do not change EDASpec defaults. Review advisory pairs with the modeler.",
        actor=ResponsibleActor.MODELER,
        review=disposition is Prem3DiagnosticDisposition.REVIEW_RECOMMENDED,
        rule_id="PREM3-VIF-001",
        variables=present,
    )
    return {
        "pairs": pairs,
        "vif": vif_rows,
        "official_pairs": official_pairs,
        "advisory_pairs": advisory_pairs,
        "official_vif": official_vif,
        "advisory_vif": advisory_vif,
        "finding_origin": "PREM3_PRE_EDA",
        "not_official_meridian_eda": True,
        "finding": finding.model_dump(mode="json"),
    }


def analyze_media_spend_consistency(snapshot: DiagnosticSnapshot) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    for spec in snapshot.channels:
        if not spec.is_paid:
            continue
        if not spec.impressions_column or not spec.spend_column:
            continue
        if spec.impressions_column not in snapshot.frame.columns:
            continue
        if spec.spend_column not in snapshot.frame.columns:
            continue
        media = pd.to_numeric(snapshot.frame[spec.impressions_column], errors="coerce").fillna(0)
        spend = pd.to_numeric(snapshot.frame[spec.spend_column], errors="coerce").fillna(0)
        spend_no_media = snapshot.frame.loc[(spend > 0) & (media <= 0)]
        media_no_spend = snapshot.frame.loc[(media > 0) & (spend <= 0)]
        cpu = np.where(media > 0, spend / media, np.nan)
        cpu_series = pd.Series(cpu)
        if not spend_no_media.empty:
            issues.append(
                {
                    "channel": spec.channel,
                    "pattern": "spend_positive_exposure_zero",
                    "row_count": int(len(spend_no_media)),
                }
            )
        if not media_no_spend.empty:
            issues.append(
                {
                    "channel": spec.channel,
                    "pattern": "exposure_positive_spend_zero",
                    "row_count": int(len(media_no_spend)),
                }
            )
        if cpu_series.notna().any():
            median = float(cpu_series.median())
            extreme = int((cpu_series > median * 20).fillna(False).sum()) if median > 0 else 0
            if extreme:
                issues.append(
                    {
                        "channel": spec.channel,
                        "pattern": "extreme_cost_per_unit",
                        "row_count": extreme,
                    }
                )
    finding = _finding(
        finding_id="PREM3-PREEDA-MEDIA-SPEND-CONSISTENCY",
        dimension="MEDIA_SPEND_CONSISTENCY",
        disposition=(
            Prem3DiagnosticDisposition.REVIEW_RECOMMENDED
            if issues
            else Prem3DiagnosticDisposition.PASS
        ),
        knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
        title="Media/spend consistency",
        calculated="Spend without exposure, exposure without spend, and extreme cost-per-unit.",
        evidence={"inconsistencies": issues, "autonomous_patch": False},
        why="Source inconsistencies usually require data-engineer or marketer resolution.",
        practice="Do not automatically patch source-system defects.",
        action="Investigate source exports for inconsistent spend/exposure pairs.",
        actor=ResponsibleActor.DATA_ENGINEER,
        review=bool(issues),
        rule_id="PREM3-MISS-001",
        channels=sorted({item["channel"] for item in issues}),
    )
    return {
        "inconsistencies": issues,
        "autonomous_patch": False,
        "finding": finding.model_dump(mode="json"),
    }


def classify_missing_data_evidence(snapshot: DiagnosticSnapshot) -> dict[str, Any]:
    frame = snapshot.frame
    classifications: list[dict[str, Any]] = []
    for spec in snapshot.channels:
        for column, role in (
            (spec.impressions_column, "media"),
            (spec.spend_column, "spend"),
            (spec.organic_column, "organic"),
        ):
            if not column or column not in frame.columns:
                continue
            nulls = int(frame[column].isna().sum())
            evidence = _missingness_from_provenance(snapshot, column)
            if nulls == 0 and not evidence:
                klass = MissingnessClass.NOT_APPLICABLE
            else:
                klass = evidence or MissingnessClass.UNKNOWN_ABSENCE
            classifications.append(
                {
                    "column": column,
                    "channel": spec.channel,
                    "role": role,
                    "null_count": nulls,
                    "classification": klass.value,
                    "zero_not_assumed": klass is not MissingnessClass.CONFIRMED_INACTIVITY
                    and klass is not MissingnessClass.SOURCE_CONFIRMED_ZERO,
                    "action_authority": (
                        "AUTO_SAFE"
                        if klass is MissingnessClass.CONFIRMED_INACTIVITY
                        else "USER_REQUIRED"
                    ),
                }
            )
    kpi_imp = _imputation_evidence(snapshot, snapshot.kpi_column, "kpi")
    control_imps = [
        _imputation_evidence(snapshot, column, "control") for column in snapshot.contract.controls
    ]
    finding = _finding(
        finding_id="PREM3-PREEDA-MISSINGNESS",
        dimension="MISSINGNESS_EVIDENCE",
        disposition=Prem3DiagnosticDisposition.PASS,
        knowledge_class=KnowledgeClass.PREM3_POLICY_BLOCKER,
        title="Missing-data evidence",
        calculated="Classified missing media/KPI/control cells using provenance, not imputation.",
        evidence={
            "media": classifications,
            "kpi_imputation": kpi_imp,
            "control_imputation": control_imps,
            "unknown_absence_is_not_zero": True,
            "kpi_control_imputation_auto_safe": False,
        },
        why="Unknown absence must not be treated as inactivity.",
        practice=(
            "AUTO_SAFE zero-fill is allowed only for CONFIRMED_INACTIVE media. "
            "KPI/control imputation remains APPROVAL_REQUIRED."
        ),
        action="Do not fill unknown media as zero. Do not impute KPI/controls autonomously.",
        actor=ResponsibleActor.DATA_ENGINEER,
        review=any(
            item["classification"]
            in {MissingnessClass.UNKNOWN_ABSENCE.value, MissingnessClass.SOURCE_GAP.value}
            for item in classifications
        ),
        rule_id="PREM3-MISS-001",
    )
    if kpi_imp.get("occurred") and not kpi_imp.get("approved"):
        finding.disposition = Prem3DiagnosticDisposition.USER_CONTEXT_REQUIRED
        finding.decision_class = DecisionClass.APPROVAL_REQUIRED
    return {
        "media": classifications,
        "kpi_imputation": kpi_imp,
        "control_imputation": control_imps,
        "unknown_absence_is_not_zero": True,
        "finding": finding.model_dump(mode="json"),
    }


def analyze_reach_frequency_structure(snapshot: DiagnosticSnapshot) -> dict[str, Any]:
    rf_cols = [
        column
        for column in snapshot.frame.columns
        if "reach" in column.lower() or "frequency" in column.lower()
    ]
    if not rf_cols:
        finding = _finding(
            finding_id="PREM3-PREEDA-RF",
            dimension="REACH_FREQUENCY",
            disposition=Prem3DiagnosticDisposition.NOT_APPLICABLE,
            knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
            title="Reach and frequency",
            calculated="No reach/frequency columns in the verified input.",
            evidence={"applicable": False},
            why="R&F diagnostics apply only when reach/frequency variables exist.",
            practice="Do not infer cumulative reach solely because values tend to rise.",
            action="No R&F action.",
            actor=ResponsibleActor.PREM3,
            review=False,
            rule_id="PREM3-SCOPE-001",
        )
        return {"applicable": False, "finding": finding.model_dump(mode="json")}
    notes: list[dict[str, Any]] = []
    for column in rf_cols:
        numeric = pd.to_numeric(snapshot.frame[column], errors="coerce")
        increasing = bool(numeric.diff().dropna().ge(0).mean() > 0.9)
        notes.append(
            {
                "column": column,
                "zero_share": round(float((numeric.fillna(0) <= 0).mean()), 6),
                "possible_cumulative_pattern": increasing,
                "cumulative_not_inferred": True,
            }
        )
    finding = _finding(
        finding_id="PREM3-PREEDA-RF",
        dimension="REACH_FREQUENCY",
        disposition=Prem3DiagnosticDisposition.REVIEW_RECOMMENDED
        if any(item["possible_cumulative_pattern"] for item in notes)
        else Prem3DiagnosticDisposition.PASS,
        knowledge_class=KnowledgeClass.PREM3_DETERMINISTIC_DIAGNOSTIC,
        title="Reach and frequency structure",
        calculated="R&F alignment, dark periods, and possible cumulative patterns.",
        evidence={"columns": notes, "auto_fix": False},
        why="Misaligned or cumulative reach can distort R&F treatments.",
        practice="Generate review evidence. Do not auto-fix.",
        action="Have the data engineer confirm period-level reach vs cumulative reach.",
        actor=ResponsibleActor.DATA_ENGINEER,
        review=any(item["possible_cumulative_pattern"] for item in notes),
        rule_id="PREM3-SCOPE-001",
        variables=rf_cols,
    )
    return {"applicable": True, "columns": notes, "finding": finding.model_dump(mode="json")}


def analyze_channel_scope_candidates(
    snapshot: DiagnosticSnapshot,
    *,
    spend: dict[str, Any] | None = None,
    variation: dict[str, Any] | None = None,
    parameter_budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spend = spend or analyze_channel_spend_distribution(snapshot)
    variation = variation or analyze_media_variation(snapshot)
    low_share = set(spend.get("bottom_share_candidates") or [])
    weak_var = set(variation.get("limited_variation_channels") or [])
    candidates: list[dict[str, Any]] = []
    for spec in snapshot.channels:
        reasons: list[str] = []
        if spec.channel in low_share:
            reasons.append("low_spend_share")
        if spec.channel in weak_var:
            reasons.append("weak_variation")
        if not reasons:
            continue
        if spec.channel in snapshot.confirmed_confounders:
            continue
        candidates.append(
            {
                "channel": spec.channel,
                "why_surfaced": reasons,
                "semantic_compatibility": "UNKNOWN",
                "expected_diagnostic_effect": (
                    "Reducing treatment count would improve the lenient parameter ratio. "
                    "This does not establish a valid merge."
                ),
                "decision_authority": DecisionClass.APPROVAL_REQUIRED.value,
                "recommendation": False,
                "authorized_merge": False,
                "drop_confounder": False,
            }
        )
    finding = _finding(
        finding_id="PREM3-PREEDA-SCOPE-CANDIDATES",
        dimension="CHANNEL_SPEND_DISTRIBUTION",
        disposition=(
            Prem3DiagnosticDisposition.REVIEW_RECOMMENDED
            if candidates
            else Prem3DiagnosticDisposition.PASS
        ),
        knowledge_class=KnowledgeClass.MMM_JUDGMENT,
        title="Channel scope candidates",
        calculated="Ranked low-share / weak-variation channels as review candidates only.",
        evidence={
            "candidates": candidates,
            "parameter_pressure": (parameter_budget or {}).get("interpretation"),
            "never_drop_confirmed_confounder": True,
        },
        why="Scope review may reduce parameter pressure when channels are semantically compatible.",
        practice=(
            "Candidate != recommendation != authorized merge. "
            "Correlation cannot prove compatibility."
        ),
        action="Analyst/modeler must approve any consolidation. PreM3 will not merge autonomously.",
        actor=ResponsibleActor.ANALYST,
        review=bool(candidates),
        rule_id="PREM3-SCOPE-001",
        channels=[item["channel"] for item in candidates],
    )
    return {
        "candidates": candidates,
        "authorized_merge": False,
        "finding": finding.model_dump(mode="json"),
    }


def _finding(
    *,
    finding_id: str,
    dimension: str,
    disposition: Prem3DiagnosticDisposition,
    knowledge_class: KnowledgeClass,
    title: str,
    calculated: str,
    evidence: dict[str, Any],
    why: str,
    practice: str,
    action: str,
    actor: ResponsibleActor,
    review: bool,
    rule_id: str,
    channels: list[str] | None = None,
    variables: list[str] | None = None,
) -> Prem3PreEdaFinding:
    meta = rule_authority(rule_id)
    decision = DecisionClass(str(meta.get("decision_class") or DecisionClass.ADVISORY.value))
    return Prem3PreEdaFinding(
        finding_id=finding_id,
        dimension=dimension,
        disposition=disposition,
        knowledge_class=knowledge_class,
        decision_class=decision,
        title=title,
        what_was_calculated=calculated,
        observed_evidence=evidence,
        why_it_matters=why,
        best_practice=practice,
        recommended_action=action,
        responsible_actor=actor,
        blocks_model_ready=False,
        review_recommended=review,
        affected_channels=channels or [],
        affected_variables=variables or [],
        source_authority=_authority(meta, knowledge_class, decision),
    )


def _authority(meta: dict[str, Any], knowledge: KnowledgeClass, decision: DecisionClass):
    return AuthorityRef(
        knowledge_class=knowledge,
        decision_class=decision,
        rule_id=str(meta.get("rule_id") or ""),
        source_url=str(meta.get("source_url") or ""),
        source_tier=str(meta.get("source_tier") or ""),
        blocks_model_ready=False,
        threshold_authority=str(meta.get("threshold_authority") or ""),
    )


def _first_positive(
    frame: pd.DataFrame, time_col: str, media_col: str, spend_col: str | None
) -> str | None:
    mask = _positive_mask(frame, media_col, spend_col)
    if not bool(mask.any()):
        return None
    times = pd.to_datetime(frame.loc[mask, time_col], errors="coerce").dropna()
    if times.empty:
        return None
    return times.min().strftime("%Y-%m-%d")


def _positive_mask(frame: pd.DataFrame, media_col: str, spend_col: str | None) -> pd.Series:
    media = pd.to_numeric(frame[media_col], errors="coerce").fillna(0)
    mask = media > 0
    if spend_col and spend_col in frame.columns:
        spend = pd.to_numeric(frame[spend_col], errors="coerce").fillna(0)
        mask = mask | (spend > 0)
    return mask


def _overall_coverage(values: list[str]) -> str:
    unique = set(values)
    if unique == {PrePeriodCoverage.PRESENT.value}:
        return PrePeriodCoverage.PRESENT.value
    if unique == {PrePeriodCoverage.UNKNOWN.value}:
        return PrePeriodCoverage.UNKNOWN.value
    if unique == {PrePeriodCoverage.ABSENT.value}:
        return PrePeriodCoverage.ABSENT.value
    return PrePeriodCoverage.PARTIAL.value


def _media_series(frame: pd.DataFrame, spec: ChannelSpec) -> pd.Series | None:
    column = spec.impressions_column or spec.organic_column
    if not column or column not in frame.columns:
        return None
    return pd.to_numeric(frame[column], errors="coerce")


def _cv(series: pd.Series) -> float | None:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return None
    mean = float(numeric.mean())
    if mean == 0:
        return None
    return round(float(numeric.std(ddof=0) / abs(mean)), 6)


def _relative_range(series: pd.Series) -> float | None:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return None
    max_v = float(numeric.max())
    if max_v == 0:
        return 0.0
    return round((float(numeric.max()) - float(numeric.min())) / abs(max_v), 6)


def _outlier_share(series: pd.Series) -> float | None:
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if len(numeric) < 4:
        return None
    q1 = numeric.quantile(0.25)
    q3 = numeric.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return 0.0
    outliers = (numeric < q1 - 1.5 * iqr) | (numeric > q3 + 1.5 * iqr)
    return round(float(outliers.mean()), 6)


def _corr(left: pd.Series, right: pd.Series) -> float | None:
    pair = pd.concat([left, right], axis=1).dropna()
    if len(pair) < 3:
        return None
    value = pair.iloc[:, 0].corr(pair.iloc[:, 1])
    if pd.isna(value):
        return None
    return round(float(value), 6)


def _vif_table(matrix: pd.DataFrame) -> list[dict[str, Any]]:
    clean = matrix.dropna()
    if len(clean) < 3 or clean.shape[1] < 2:
        return []
    values = clean.to_numpy(dtype=float)
    rows: list[dict[str, Any]] = []
    for index, name in enumerate(clean.columns):
        y = values[:, index]
        z = np.delete(values, index, axis=1)
        z = np.column_stack([np.ones(len(z)), z])
        try:
            beta, *_ = np.linalg.lstsq(z, y, rcond=None)
        except np.linalg.LinAlgError:
            rows.append({"variable": name, "vif": float("inf")})
            continue
        pred = z @ beta
        ss_res = float(np.sum((y - pred) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        if ss_tot <= 0:
            vif = float("inf")
        else:
            r2 = 1.0 - (ss_res / ss_tot)
            vif = float("inf") if r2 >= 0.999999 else 1.0 / (1.0 - r2)
        rows.append({"variable": str(name), "vif": round(vif, 6) if vif != float("inf") else vif})
    return rows


def _safe_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    return round(float(value), 6)


def _missingness_from_provenance(
    snapshot: DiagnosticSnapshot, column: str
) -> MissingnessClass | None:
    for record in snapshot.transformation_provenance:
        tool = str(record.get("tool") or record.get("action_id") or "").lower()
        params = record.get("parameters") or {}
        if column not in str(params) and column not in str(record):
            continue
        if "inactive" in tool or params.get("confirmed_inactive") is True:
            return MissingnessClass.CONFIRMED_INACTIVITY
        if "zero_fill" in tool and params.get("confirmed_inactive") is not True:
            return MissingnessClass.UNKNOWN_ABSENCE
        if "source_gap" in tool or params.get("source_gap") is True:
            return MissingnessClass.SOURCE_GAP
    for issue in snapshot.issues:
        if column in str(issue) and "inactive" in str(issue).lower():
            return MissingnessClass.CONFIRMED_INACTIVITY
    return None


def _imputation_evidence(snapshot: DiagnosticSnapshot, column: str, role: str) -> dict[str, Any]:
    occurred = False
    approved = False
    method = None
    periods: list[str] = []
    for record in snapshot.transformation_provenance:
        tool = str(record.get("tool") or "").lower()
        mentions_column = column in str(record)
        if "imput" not in tool:
            continue
        if role == "kpi" and not (mentions_column or "kpi" in tool):
            continue
        if role == "control" and not (mentions_column or "control" in tool):
            continue
        occurred = True
        method = record.get("tool")
        approved = str(record.get("status") or "").upper() == "APPROVED"
        periods = list(record.get("affected_periods") or [])
    return {
        "column": column,
        "role": role,
        "occurred": occurred,
        "method": method,
        "affected_periods": periods,
        "approved": approved,
        "action_authority": "APPROVAL_REQUIRED",
        "auto_safe": False,
        "remaining_risk": "Imputed KPI/control values remain modeler-review items."
        if occurred
        else None,
    }
