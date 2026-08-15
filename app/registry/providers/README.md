# Provider seed registry

Initial MVP providers:

1. Google Ads
2. Meta Ads
3. GA4
4. Shopify

Do not create executable field mappings from memory or assumption. Each provider/report-family YAML entry must include official source evidence and retrieval date before M3 can treat it as trusted registry context.

Required record shape is defined in `app/registry/schema.py`.

Provider seeding is Phase 2 work after the first end-to-end vertical slice is operational.
