from __future__ import annotations

from sdd_auto_story_to_ift.mcp import JIRA_TOOL_ALIASES, missing_actions, resolve_tool_names
from sdd_auto_story_to_ift.models import JiraIssue
from sdd_auto_story_to_ift.plan import build_issue_plan, build_plan


def test_build_plan_includes_jql_and_mcp_aliases(settings):
    plan = build_plan(settings)
    assert 'project = "DEV"' in plan["source_jql"]
    assert plan["mcp"]["jira_tool_aliases"]["search"] == JIRA_TOOL_ALIASES["search"]
    assert plan["steps"][0].startswith("1 ")
    assert plan["children"]["ready_statuses"] == ["Готов"]
    assert "Ready for IFT" in plan["target_statuses"]
    assert "Do not call REST" in plan["mcp"]["rule"]


def test_issue_plan_includes_children_jql(settings):
    story = JiraIssue(
        key="DEV-40",
        summary="Ready check",
        issue_type="Story",
        status="In Progress",
    )
    children = [
        JiraIssue(key="DEV-41", summary="t", issue_type="Task", status="Готов"),
    ]
    plan = build_issue_plan(settings, story, children)
    assert plan["children_jql"] == settings.children_jql("DEV-40")
    assert plan["evaluation"]["should_transition"] is True
    assert plan["mcp"]["search_children"]["maxResults"] == 50


def test_resolve_tool_names_picks_first_available_alias():
    available = ["jira_search", "getJiraIssue", "transition_issue"]
    jira = resolve_tool_names(available, JIRA_TOOL_ALIASES)
    assert jira["search"] == "jira_search"
    assert jira["get"] == "getJiraIssue"
    assert jira["transition"] == "transition_issue"
    assert jira["transitions"] is None
    assert missing_actions(jira, ("search", "get", "transitions", "transition")) == ["transitions"]
