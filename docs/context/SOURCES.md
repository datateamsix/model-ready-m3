# Primary Official Sources

## Hackathon

- https://allthingsagentichackathon.devpost.com/
- https://allthingsagentichackathon.devpost.com/rules
- https://allthingsagentichackathon.devpost.com/details/faqs

## Meridian

- https://developers.google.com/meridian
- https://developers.google.com/meridian/docs/pre-modeling/collect-data
- https://developers.google.com/meridian/docs/pre-modeling/amount-data-needed
- https://developers.google.com/meridian/docs/user-guide/supported-data-types-formats
- https://developers.google.com/meridian/reference/api/meridian/data/load/DataFrameDataLoader
- https://developers.google.com/meridian/docs/user-guide/mmm-unified-schema

## Official Meridian EDA / ModelSpec (retrieved 2026-08-16)

- https://developers.google.com/meridian/docs/pre-modeling/perform-eda — official EDA process, ERROR/ATTENTION/INFO, `MeridianEDA.generate_and_save_report`
- https://developers.google.com/meridian/reference/api/meridian/model/eda/meridian_eda/MeridianEDA — official EDA class
- https://developers.google.com/meridian/reference/api/meridian/model/eda/eda_outcome/EDAOutcome — official structured outcomes
- https://developers.google.com/meridian/docs/user-guide/load-geo-data-without-rf — geo InputData builder used by Dataset A
- https://developers.google.com/meridian/docs/user-guide/installing — Python 3.11/3.12 install constraint
- https://developers.google.com/meridian/reference/api/meridian/model/spec/ModelSpec — official `knots=` constructor (not `n_knots`)
- https://developers.google.com/meridian/docs/advanced-modeling/setting-knots — geo default `knots=n_times`; national-level/time-only variables are collinear with time
- https://developers.google.com/meridian/docs/user-guide/configure-model — ModelSpec configuration
- https://github.com/google/meridian — upstream package source

Installed worker pin remains `google-meridian==1.8.0`. Public docs/index may show a newer release; this milestone proves the imported distribution, not the latest index listing. Official package does not expose a supported standalone `meridian` CLI.

## Cortex for Meridian / BigQuery model handoff

- https://docs.cloud.google.com/cortex/docs/v6/meridian
- https://docs.cloud.google.com/cortex/docs/v6/deployment-step-four
- https://docs.cloud.google.com/workflows
- https://cloud.google.com/colab/docs

## BigQuery / ADK integration

- https://adk.dev/integrations/bigquery/

## Google Agent Development Kit

- https://adk.dev/
- https://adk.dev/sessions/memory/
- https://adk.dev/evaluate/
- https://adk.dev/evaluate/criteria/
- https://adk.dev/optimize/

## Source policy

For technical requirements, prefer current official Google documentation.
Record source URL and retrieval date in registry/rule definitions where feasible.

## Architecture interpretation note

The official Cortex for Meridian documentation is the reference pattern for:
- BigQuery model-data views;
- generated Meridian configuration/handoff;
- optional Colab Enterprise execution;
- Cloud Workflows orchestration.

ModelReady/M3 is not Cortex. The hackathon architecture uses those official patterns as evidence that a validated BigQuery-to-Meridian handoff is a legitimate Google Cloud design.
