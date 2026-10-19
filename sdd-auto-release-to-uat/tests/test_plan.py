from __future__ import annotations

from sdd_auto_release_to_uat.mcp import JIRA_TOOL_ALIASES, missing_actions, resolve_tool_names
from sdd_auto_release_to_uat.models import JiraIssue
from sdd_auto_release_to_uat.plan import build_issue_plan, build_plan


def test_build_plan_includes_jql_and_mcp_aliases(settings):
    plan = build_plan(settings)
    assert 'project = "REL"' in plan["source_jql"]
    assert plan["mcp"]["jira_tool_aliases"]["search"] == JIRA_TOOL_ALIASES["search"]
    assert plan["steps"][0].startswith("1 ")
    assert plan["stories"]["ready_statuses"] == ["Ready for UAT"]
    assert "Ready for UAT" in plan["target_statuses"]
    assert "Do not call REST" in plan["mcp"]["rule"]


def test_issue_plan_includes_stories_jql(settings):
    release = JiraIssue(
        key="REL-12",
        summary="Release",
        issue_type="Epic",
        status="In Progress",
    )
    stories = [
        JiraIssue(key="DEV-40", summary="one", issue_type="Story", status="Ready for UAT"),
    ]
    plan = build_issue_plan(settings, release, stories)
    assert plan["stories_jql"] == settings.stories_jql("REL-12")
    assert plan["evaluation"]["should_transition"] is True
    assert plan["mcp"]["search_stories"]["maxResults"] == 50


def test_resolve_tool_names_picks_first_available_alias():
    available = ["jira_search", "getJiraIssue", "transition_issue"]
    jira = resolve_tool_names(available, JIRA_TOOL_ALIASES)
    assert jira["search"] == "jira_search"
    assert jira["get"] == "getJiraIssue"
    assert jira["transition"] == "transition_issue"
    assert jira["transitions"] is None
    assert missing_actions(jira, ("search", "get", "transitions", "transition")) == ["transitions"]
