#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-modelready-m3}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"

printf 'Bootstrapping ModelReady MVP in project %s (%s)\n' "$PROJECT_ID" "$REGION"

gcloud config set project "$PROJECT_ID"

gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com \
  eventarc.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  logging.googleapis.com

cat <<EOF
Core APIs enabled.

This script intentionally does NOT create buckets, datasets, service accounts, IAM
bindings, Eventarc triggers, or deploy services yet. Those resources should be added
as explicit, reviewable MVP steps once naming/region decisions are confirmed.
EOF
