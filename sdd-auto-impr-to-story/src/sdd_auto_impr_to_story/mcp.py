from __future__ import annotations

from typing import Iterable

JIRA_TOOL_ALIASES = {
    "search": [
        "searchJiraIssuesUsingJql",
        "jira_search",
        "search_issues",
        "jira_search_issues",
        "searchIssues",
    ],
    "get": ["getJiraIssue", "jira_get_issue", "get_issue", "getIssue"],
    "create": ["createJiraIssue", "jira_create_issue", "create_issue", "createIssue"],
    "link": [
        "createJiraIssueLink",
        "createIssueLink",
        "jira_create_issue_link",
        "create_issue_link",
        "jira_link_issues",
        "link_issues",
    ],
    "link_types": [
        "getIssueLinkTypes",
        "listJiraIssueLinkTypes",
        "jira_get_issue_link_types",
        "get_issue_link_types",
    ],
    "transitions": [
        "getTransitionsForJiraIssue",
        "listJiraIssueTransitions",
        "jira_get_transitions",
        "get_transitions",
        "listTransitions",
    ],
    "transition": [
        "transitionJiraIssue",
        "jira_transition_issue",
        "transition_issue",
        "transitionIssue",
    ],
}

BITBUCKET_TOOL_ALIASES = {
    "create_branch": [
        "createBitbucketRepoBranch",
        "create_branch",
        "createBranch",
        "bitbucket_create_branch",
        "create_bitbucket_branch",
    ],
    "get_branch": [
        "getBitbucketRepoBranch",
        "list_branches",
        "listBranches",
        "get_branch",
        "listBitbucketRepoBranches",
    ],
    "create_pr": [
        "createBitbucketRepoPullRequest",
        "create_pull_request",
        "createPullRequest",
        "bitbucket_create_pull_request",
        "create_bitbucket_pull_request",
    ],
    "list_prs": [
        "listBitbucketRepoPullRequests",
        "list_pull_requests",
        "listPullRequests",
        "get_pull_requests",
    ],
    "get_pr": [
        "getBitbucketRepoPullRequest",
        "get_pull_request",
        "getPullRequest",
    ],
}

REQUIRED_JIRA_ACTIONS = ("search", "get", "create", "link", "transitions", "transition")
REQUIRED_BITBUCKET_ACTIONS = ("create_branch", "create_pr")


def resolve_tool_names(
    available: Iterable[str],
    aliases: dict[str, list[str]],
) -> dict[str, str | None]:
    """Map logical actions to the first matching MCP tool name."""
    lower = {name.lower(): name for name in available}
    resolved: dict[str, str | None] = {}
    for action, names in aliases.items():
        resolved[action] = None
        for alias in names:
            hit = lower.get(alias.lower())
            if hit:
                resolved[action] = hit
                break
    return resolved


def missing_actions(resolved: dict[str, str | None], required: Iterable[str]) -> list[str]:
    return [action for action in required if not resolved.get(action)]
