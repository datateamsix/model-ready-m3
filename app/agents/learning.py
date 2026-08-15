"""MEL learning/evaluator reasoning boundary.

Learning may create candidate lessons from evidence. Promotion requires measured
outcomes and regression checks; memory never bypasses deterministic validators.
"""

LEARNING_AGENT_SCOPE = {
    "owns": [
        "episode_summary",
        "candidate_lesson_extraction",
        "lesson_scope_and_confidence",
        "evaluation_case_proposals",
    ],
    "does_not_own": [
        "uncontrolled_policy_mutation",
        "validator_overrides",
        "hard_coded_learning_receipts",
    ],
}
