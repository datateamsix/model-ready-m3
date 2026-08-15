# Deployment — MVP

Target Google Cloud project: `modelready-m3` (configuration-driven; do not hard-code inside application logic).

## MVP deployment path

Prefer the shortest reproducible path that produces judge-visible Google Cloud proof:

1. authenticate with `gcloud` and Application Default Credentials for local development;
2. enable the core APIs with `scripts/bootstrap_gcp.sh`;
3. verify the M3 ADK agent locally;
4. deploy from source to Cloud Run;
5. capture Cloud Run execution and Cloud Logging evidence;
6. wire GCS/Eventarc only after the synchronous end-to-end vertical slice works.

Google Cloud's current Cloud Run buildpacks support ADK source deployment and `pyproject.toml`; avoid adding Docker/Terraform complexity until it earns a demo or reliability benefit.

## Required cloud resources for the golden path

- Cloud Run M3 service
- Vertex AI / Gemini access
- raw GCS bucket
- artifact GCS bucket
- BigQuery `modelready_ops` dataset
- BigQuery `modelready_models` dataset
- BigQuery `modelready_experience` dataset (Phase 3/MEL)
- Eventarc/Pub/Sub trigger after vertical-slice proof
- Secret Manager only for actual secrets

## Deployment guardrails

- Cloud Run should scale to zero for the hackathon unless a measured demo requirement says otherwise.
- Use least-privilege service accounts.
- Never commit service-account keys.
- All output tables/views are run-scoped or versioned.
- `MODEL_READY` is not set until deterministic readiness, BigQuery publish parity, Meridian handoff contract, and provenance pass.
- Meridian model execution remains approval-gated.

Vertex AI / Gemini uses `GOOGLE_CLOUD_LOCATION` (hackathon default: `global`). Cloud Run, GCS, and BigQuery jobs use `GOOGLE_CLOUD_REGION` (hackathon default: `us-central1`). Do not pass `global` to `gcloud run deploy --region`.

## Initial deploy command

Once the root ADK agent runs locally and credentials/APIs are configured:

```bash
gcloud run deploy modelready-m3 \
  --source . \
  --region "${GOOGLE_CLOUD_REGION:-us-central1}" \
  --project "${GOOGLE_CLOUD_PROJECT:-modelready-m3}"
```

Authentication/public-access policy should be chosen explicitly before the judge-facing deployment; do not blindly expose customer-data endpoints.
