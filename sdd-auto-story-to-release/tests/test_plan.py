from __future__ import annotations

from sdd_auto_story_to_release.mcp import (
    BITBUCKET_TOOL_ALIASES,
    JIRA_TOOL_ALIASES,
    missing_actions,
    resolve_tool_names,
)
from sdd_auto_story_to_release.models import JiraIssue
from sdd_auto_story_to_release.plan import build_issue_plan, build_plan


def test_build_plan(settings):
    plan = build_plan(settings)
    assert "release Story key" in plan["input"]
    assert plan["mcp"]["jira_tool_aliases"]["search"] == JIRA_TOOL_ALIASES["search"]
    assert plan["mcp"]["bitbucket_tool_aliases"]["create_pr"] == BITBUCKET_TOOL_ALIASES["create_pr"]
    assert plan["steps"][0].startswith("1 ")
    assert "Do not call REST" in plan["mcp"]["rule"]


def test_issue_plan(settings):
    release = JiraIssue(key="REL-12", summary="Release 1.2", issue_type="Story")
    stories = [
        JiraIssue(
            key="DEV-40",
            summary="Pay",
            issue_type="Story",
            components=("backend",),
        )
    ]
    plan = build_issue_plan(settings, release, stories)
    assert plan["release_number"] == "1.2"
    assert 'parent = "REL-12"' in plan["stories_jql"]
    assert plan["composition"]["pull_requests"][0]["title"] == "DEV-40 → release/1.2"


def test_resolve_tools():
    available = ["jira_search", "create_branch", "createBitbucketRepoPullRequest"]
    jira = resolve_tool_names(available, JIRA_TOOL_ALIASES)
    bitbucket = resolve_tool_names(available, BITBUCKET_TOOL_ALIASES)
    assert jira["search"] == "jira_search"
    assert bitbucket["create_branch"] == "create_branch"
    assert missing_actions(jira, ("search", "get")) == ["get"]
