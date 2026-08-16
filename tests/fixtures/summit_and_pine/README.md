# Summit & Pine — Dataset C holdout

**Summit & Pine** is a fully synthetic outdoor-furniture retailer. It is the MEL holdout assignment: independent of Music Center Dataset A.

Classification: **synthetic**.

Do not claim this is a production customer.

## Seal

`dataset_c/learning/holdout_manifest.json` is sealed before candidate extraction. `lesson_ids_visible_at_seal` is empty.

## Shape

- national weekly (`US`)
- 78 weeks from 2024-07-01
- TikTok Ads (spend in cents)
- Amazon Ads (`MM-DD-YYYY` dates)
- Stripe charges/revenue
- email sends
- weather + holiday controls

Seeded defects are different from Dataset A: cents vs dollars, Amazon date format, one missing Stripe week, one duplicated Stripe row.

Generate:

```bash
python scripts/generate_dataset_c.py
```
