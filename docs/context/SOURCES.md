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
