# Provider registry

Layer A context for M3 intake. The catalog file is:

`marketing_advertising_providers.v1.json`

- **50 providers** covering common marketing, advertising, analytics, commerce, and measurement exports.
- **`trust=executable`**: Google Ads, Meta Ads, GA4, Shopify. Field-level maps may be applied. Each includes sources.
- **`trust=directory`**: identification, export-format hints, and Meridian gap hypotheses only. M3 must fail closed on `apply_mapping_to_file(provider_id=...)` until the card is sourced and promoted.

Do not invent official column names for directory rows. Do not paste the full catalog into the Gemini system prompt; use `lookup_provider_card` / `search_provider_directory`.

Required record shape is defined in `app/registry/schema.py`.
