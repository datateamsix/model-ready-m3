import type { ExperienceBundle, ExperienceEpisode, ExperienceReflection } from "@/types/mel";
import { domainViewV1 } from "./domain-view";
import { musicCenterDatasetARun } from "./music-center-run";

/**
 * UI_DEMO_FIXTURE
 *
 * app/mel/ has synthetic unit-test coverage for episode/reflection
 * construction (tests/unit/test_mel_reflection.py uses a "music-center"
 * organization_id) but no committed JSON artifact to copy. This bundle is
 * authored to visually exercise the experience/reflection/DOMAIN_VIEW
 * surfaces of the run workspace. It intentionally leaves promotionReceipt
 * and application null: MEL promotion is not proven for this run.
 *
 * domain_view_fingerprint_used is the one fingerprint field that is a real
 * sourced value (domainViewV1.content_fingerprint — the actual DOMAIN_VIEW
 * this reflection was produced against). episode_fingerprint and each
 * record's own content_fingerprint are illustrative placeholders, not real
 * computed hashes — there is no live MEL pipeline in Mission 1 to compute
 * them from. dataset_role/reflection_role are TRAINING_EXPERIENCE/TRAINING
 * because Music Center Dataset A is real training-eligible data, not the
 * Dataset C (Summit & Pine) sealed holdout.
 */

const reflection: ExperienceReflection = {
  reflection_id: "reflection-music-center-dataset-a-demo",
  episode_id: "episode-music-center-dataset-a-demo",
  run_id: musicCenterDatasetARun.run_id,
  episode_fingerprint: "UI_DEMO_FIXTURE-episode-fingerprint",
  domain_view_version_used: domainViewV1.domain_view_version,
  domain_view_fingerprint_used: domainViewV1.content_fingerprint,
  created_at: musicCenterDatasetARun.updated_at,
  known_at_decision_time: [
    {
      item_id: "r-001",
      surface: "KNOWN_AT_DECISION_TIME",
      statement: "DOMAIN_VIEW 1.0.0 authorized date-format normalization (MR-001) as AUTO_SAFE.",
      origin: "DOMAIN_VIEW",
      evidence_refs: ["rule:MR-001"],
    },
  ],
  observed: [
    {
      item_id: "r-002",
      surface: "OBSERVED",
      statement: "5 issues detected across the Music Center Dataset A package; all AUTO_SAFE.",
      origin: "RUN_EVIDENCE",
      evidence_refs: ["MC-A-001", "MC-A-002", "MC-A-003", "MC-A-004", "MC-A-005"],
    },
  ],
  determined: [
    {
      item_id: "r-003",
      surface: "DETERMINED",
      statement: "All 5 detected issues met their AUTO_SAFE preconditions and were remediated without approval.",
      origin: "RUN_EVIDENCE",
      evidence_refs: [],
    },
  ],
  believed: [],
  allowed: [
    {
      item_id: "r-004",
      surface: "ALLOWED",
      statement: "AUTO_SAFE remediation was permitted to run without a human approval pause.",
      origin: "DOMAIN_VIEW",
      evidence_refs: [],
    },
  ],
  unknown: [],
  expected: [
    {
      item_id: "r-005",
      surface: "EXPECTED",
      statement: "Expected the run to reach MODEL_READY with zero official Meridian ERROR findings.",
      origin: "RUN_EVIDENCE",
      evidence_refs: [],
    },
  ],
  actual_outcome: [
    {
      item_id: "r-006",
      surface: "ACTUAL_OUTCOME",
      statement: "The run reached MODEL_READY with zero official ERROR findings.",
      origin: "RUN_EVIDENCE",
      evidence_refs: [],
    },
  ],
  confirmed: [
    {
      item_id: "r-007",
      surface: "CONFIRMED",
      statement: "Expected outcome matched actual outcome.",
      origin: "RUN_EVIDENCE",
      evidence_refs: [],
    },
  ],
  missed: [],
  incomplete: [],
  human_added: [],
  meridian_added: [],
  effective_actions: [
    {
      item_id: "r-008",
      surface: "EFFECTIVE_ACTIONS",
      statement: "normalize_dates, aggregate_to_week, normalize_numeric_values, and apply_mapping each resolved their targeted issue.",
      origin: "RUN_EVIDENCE",
      evidence_refs: [],
    },
  ],
  ineffective_or_unnecessary_actions: [],
  surprises: [],
  possible_improvements: [
    {
      item_id: "r-009",
      surface: "POSSIBLE_IMPROVEMENTS",
      statement: "No candidate lesson has yet passed MEL's promotion bar for this pattern.",
      origin: "PREM3_INTERPRETATION",
      evidence_refs: [],
    },
  ],
  generalization_risk: "LOW",
  reflection_summary:
    "Music Center Dataset A reached MODEL_READY exactly as expected via 5 AUTO_SAFE remediations. Reflection captured; no candidate lesson has been promoted from it yet.",
  content_fingerprint: "UI_DEMO_FIXTURE-reflection-fingerprint",
  operational_authority: false,
  reflection_role: "TRAINING",
};

const episode: ExperienceEpisode = {
  episode_id: "episode-music-center-dataset-a-demo",
  run_id: musicCenterDatasetARun.run_id,
  episode_started_at: musicCenterDatasetARun.created_at,
  episode_closed_at: musicCenterDatasetARun.updated_at,
  terminal_outcome: "MODEL_READY",
  domain_view_version: domainViewV1.domain_view_version,
  domain_view_fingerprint: domainViewV1.content_fingerprint,
  content_fingerprint: "UI_DEMO_FIXTURE-episode-content-fingerprint",
  summary: {
    detected_issue_count: musicCenterDatasetARun.detected_issue_count,
    resolved_issue_count: musicCenterDatasetARun.resolved_issue_count,
  },
  learning_eligible: true,
  holdout: false,
  dataset_role: "TRAINING_EXPERIENCE",
  reflection_id: reflection.reflection_id,
};

export const musicCenterExperienceBundle: ExperienceBundle = {
  episode,
  reflection,
  promotionReceipt: null,
  application: null,
};
