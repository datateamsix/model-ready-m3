from app.core.contracts import Issue, IssueStatus, RemediationClass, Severity
from app.tools.issues import mark_issues_remediating, resolve_issues_from_transforms


def _issue(issue_id: str, tool: str, **action: object) -> Issue:
    return Issue(
        issue_id=issue_id,
        rule_id="MR-010",
        severity=Severity.ERROR,
        title=issue_id,
        remediation_class=RemediationClass.AUTO_SAFE,
        proposed_action={"tool": tool, **action},
    )


def test_issue_lifecycle_resolves_only_after_applied_transform() -> None:
    issue = _issue("MC-A-001", "remove_exact_duplicates_from_file")
    mark_issues_remediating([issue])
    assert issue.status is IssueStatus.REMEDIATING
    resolve_issues_from_transforms([issue], [])
    assert issue.status is IssueStatus.REMEDIATING
    resolve_issues_from_transforms(
        [issue],
        [
            {
                "tool": "remove_exact_duplicates",
                "status": "APPLIED",
                "action_id": "act_dupes",
                "output_sha256": "abc123",
                "output_uri": "artifacts/google_deduped.csv",
                "input_rows": 11005,
                "output_rows": 11004,
            }
        ],
    )
    assert issue.status is IssueStatus.RESOLVED
    assert issue.resolution_action_ids == ["act_dupes"]
    assert issue.resolution_evidence["excess_rows_removed"] == 1


def test_failed_transform_does_not_resolve_issue() -> None:
    issue = _issue("MC-A-004", "normalize_numeric_values_in_file", column="amount_spent")
    resolve_issues_from_transforms(
        [issue],
        [
            {
                "tool": "normalize_numeric_values",
                "status": "FAILED",
                "action_id": "act_fail",
                "output_sha256": "abc123",
                "parameters": {"column": "amount_spent"},
                "input_rows": 10,
                "output_rows": 10,
            }
        ],
    )
    assert issue.status is IssueStatus.OPEN
    assert issue.resolution_action_ids == []
