from __future__ import annotations

from sdd_auto_story_to_uat.mcp import (
    BITBUCKET_TOOL_ALIASES,
    JIRA_TOOL_ALIASES,
    missing_actions,
    resolve_tool_names,
)
from sdd_auto_story_to_uat.models import JiraIssue, PullRequest
from sdd_auto_story_to_uat.plan import build_issue_plan, build_plan


def test_build_plan_includes_jql_and_mcp_aliases(settings):
    plan = build_plan(settings)
    assert 'project = "REL"' in plan["source_jql"]
    assert plan["mcp"]["jira_tool_aliases"]["search"] == JIRA_TOOL_ALIASES["search"]
    assert plan["mcp"]["bitbucket_tool_aliases"]["list_prs"] == BITBUCKET_TOOL_ALIASES["list_prs"]
    assert plan["bitbucket"][0]["workspace"] == "acme"
    assert plan["steps"][0].startswith("1 ")
    assert "per Story" in plan["steps"][-1]
    assert "Do not call REST" in plan["mcp"]["rule"]


def test_issue_plan_includes_stories_jql(settings):
    release = JiraIssue(key="REL-12", summary="Release 1.2", issue_type="Task")
    story = JiraIssue(key="DEV-40", summary="Pay", issue_type="Story", status="Ready for IFT")
    prs = [
        PullRequest(
            title="DEV-40",
            state="MERGED",
            source_branch="feature/DEV-40",
            destination_branch="release/1.2",
        )
    ]
    plan = build_issue_plan(settings, release, story, prs, release_number="1.2")
    assert plan["release_number"] == "1.2"
    assert 'parent = "REL-12"' in plan["stories_jql"]
    assert plan["evaluation"]["should_transition"] is True


def test_resolve_tool_names_picks_first_available_alias():
    available = ["jira_search", "getJiraIssue", "list_pull_requests"]
    jira = resolve_tool_names(available, JIRA_TOOL_ALIASES)
    bitbucket = resolve_tool_names(available, BITBUCKET_TOOL_ALIASES)
    assert jira["search"] == "jira_search"
    assert bitbucket["list_prs"] == "list_pull_requests"
    assert missing_actions(jira, ("search", "get", "transitions")) == ["transitions"]
