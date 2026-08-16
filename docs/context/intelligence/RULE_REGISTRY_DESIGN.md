# PreM3 Rule / Diagnostic Authority Registry — Design

**Status:** design + catalog extension. Not a runtime behavior change.  
**Version:** 1.0  
**Intelligence version:** 2.0.0  
**Last verified:** 2026-08-16

This mission does **not** implement the future diagnostic tool suite. It defines the authority model those tools must use.

---

## 1. Source-of-truth model

| Layer | Owns | Must not own |
|---|---|---|
| Official Meridian runtime (`MeridianEDA`, `EDASpec`, `EDAFinding`) | Official findings and official default thresholds | PreM3 heuristics |
| Machine-readable registry | Rule IDs, knowledge class, decision class, source, last-verified, threshold authority, `blocks_model_ready` | Prompt improvisation of thresholds |
| Markdown context | Explanation, examples, advisory language | Duplicate independent numeric thresholds |
| Agent prompt | Routing and interpretation | Hidden second copy of a blocker threshold |

Do not independently maintain the same threshold in Markdown, prompt, Python, and JSON.

Prefer:

machine-readable runtime config  
+  
Markdown explanation.

Official Meridian remains runtime authority for its own EDA findings.

---

## 2. Required fields

Every runtime-relevant rule or future diagnostic should eventually record:

| Field | Meaning |
|---|---|
| `rule_id` | Stable identifier (`MR-002`, `PREM3-PB-001`, …) |
| `name` | Machine name |
| `knowledge_class` | `MERIDIAN_NORMATIVE` · `PREM3_DETERMINISTIC_DIAGNOSTIC` · `MMM_EVIDENCE_HEURISTIC` · `MMM_JUDGMENT` · `PREM3_POLICY_BLOCKER` · `DESIGN_DEFAULT` |
| `decision_class` | `AUTO_BLOCK` · `AUTO_SAFE` · `ADVISORY` · `APPROVAL_REQUIRED` · `MODELER_REVIEW_REQUIRED` · `USER_REQUIRED` |
| `source_tier` | `TIER_1_MERIDIAN_OFFICIAL` · `TIER_2_FOUNDATIONAL_MMM` · `TIER_3_CROSS_FRAMEWORK` |
| `source_url` | Canonical reference |
| `last_verified` | ISO date of last official-source check |
| `applicability` | When the rule applies |
| `calculation_or_tool` | Future tool name or current implemented check |
| `threshold` | Numeric or categorical threshold, if any |
| `threshold_authority` | `MERIDIAN_OFFICIAL_DEFAULT` · `PREM3_ADVISORY` · `NONE` |
| `status` | `implemented` · `specified_not_implemented` |
| `severity` | `ERROR` · `ATTENTION` · `INFO` · `ADVISORY` |
| `blocks_model_ready` | Boolean. Heuristics must be `false` unless an official Meridian ERROR/contract rule. |
| `agent_can_fix` | Boolean |
| `human_owner` | `PREM3` · `MARKETER` · `ANALYST` · `DATA_ENGINEER` · `MODELER` · `SYSTEM_ADMIN` |
| `best_practice_guidance` | Short labeled guidance |
| `resolution_template` | Guided-remediation section keys |
| `artifact_output` | Manifest / receipt field, if any |

---

## 3. Mapping to current runtime

Current executable remediation classes in `app/core/contracts.py` remain:

`AUTO_SAFE` · `APPROVAL_REQUIRED` · `BLOCKED`

Do **not** expand that enum in this mission.

Intelligence-layer mapping:

| Intelligence `decision_class` | Current runtime class | Notes |
|---|---|---|
| `AUTO_SAFE` | `AUTO_SAFE` | Unchanged |
| `APPROVAL_REQUIRED` | `APPROVAL_REQUIRED` | Unchanged |
| `AUTO_BLOCK` | `BLOCKED` | Contract / official ERROR path |
| `USER_REQUIRED` | run state + User Resolution Pack | Not a new remediation enum |
| `ADVISORY` | no mutation | Future diagnostics only |
| `MODELER_REVIEW_REQUIRED` | no mutation / review flag | Future diagnostics only |

Current catalog: `app/rules/meridian.yaml`  
Future specified diagnostics: `app/rules/intelligence_registry.yaml`  
Loader today: `app/rules/engine.py` reads only an explicit path. The intelligence registry is **not** wired into the run coordinator.

---

## 4. Authority split example

Calculation: channel represents 1.4% of spend  
→ `PREM3_DETERMINISTIC_DIAGNOSTIC`

Interpretation: channel deserves scope review  
→ `MMM_EVIDENCE_HEURISTIC`

Action: merge channel  
→ `APPROVAL_REQUIRED`

The calculation may be automated later. The merge may not.

---

## 5. Parameter-pressure rule (specified, not implemented)

`PREM3-PB-001` computes lenient / strict / shadow ratios.

- Ratio calculation: `PREM3_DETERMINISTIC_DIAGNOSTIC`
- ~10 observations/parameter interpretation: `MMM_EVIDENCE_HEURISTIC`
- `blocks_model_ready`: **false**
- `review_recommended`: true when pressure is high/severe
- Confounder drop to improve the ratio: forbidden

---

## 6. Missingness rules (policy already documented)

`MR-002` remains implemented and `APPROVAL_REQUIRED` at runtime.

Intelligence refinement (already in YAML notes, not a new tool):

- media zero-fill only with `CONFIRMED_INACTIVE` evidence
- unknown absence → `USER_REQUIRED` / source investigation
- KPI/control imputation stays `APPROVAL_REQUIRED`
- never `AUTO_SAFE` merely because Meridian requires completeness

---

## 7. Future tools this registry will govern

Specified only. Do not implement in this mission:

`compute_parameter_budget`  
`assess_modeling_feasibility`  
`analyze_history_sufficiency`  
`check_pre_period_media`  
`analyze_channel_spend_distribution`  
`analyze_media_variation`  
`analyze_spend_range`  
`analyze_geo_coverage`  
`analyze_population_relationships`  
`analyze_collinearity`  
`analyze_media_spend_consistency`  
`classify_missing_data_evidence`  
`analyze_channel_scope_candidates`  
`detect_semantic_question_triggers`  
`generate_semantic_readiness_interview`  
`simulate_model_scope_scenarios`  
`build_pre_eda_diagnostic_report`  
`build_user_resolution_pack` (exists in EDA-gate form; do not rebuild here)

---

## 8. Context versioning

Run artifacts should eventually record `intelligence_version` from `intelligence_version.json`.

This mission adds the version file. It does not change the model-ready manifest schema or publish path.
