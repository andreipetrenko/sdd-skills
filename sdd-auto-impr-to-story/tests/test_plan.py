from __future__ import annotations

from sdd_auto_impr_to_story.mcp import (
    BITBUCKET_TOOL_ALIASES,
    JIRA_TOOL_ALIASES,
    missing_actions,
    resolve_tool_names,
)
from sdd_auto_impr_to_story.models import JiraIssue
from sdd_auto_impr_to_story.plan import build_issue_plan, build_plan


def test_build_plan_includes_jql_and_mcp_aliases(settings):
    plan = build_plan(settings)
    assert "project = \"IMPR\"" in plan["source_jql"]
    assert plan["bitbucket"]["workspace"] == "acme"
    assert plan["bitbucket"]["repo_slug"] == "app"
    assert plan["mcp"]["jira_tool_aliases"]["search"] == JIRA_TOOL_ALIASES["search"]
    assert "createBitbucketRepoBranch" in plan["mcp"]["bitbucket_tool_aliases"]["create_branch"]
    assert plan["steps"][0].startswith("1 ")
    assert plan["after_merge_statuses"] == ["В работе", "In Progress"]
    assert "In Progress" in plan["steps"][-1]
    assert "Do not call REST" in plan["mcp"]["rule"]


def test_issue_plan_pr_maps_source_branch_to_story_branch(settings):
    source = JiraIssue(
        key="IMPR-12",
        summary="Add export to CSV",
        description="Users need a CSV export.",
        issue_type="Improvement",
        status="To Do",
        components=("payments",),
    )
    plan = build_issue_plan(settings, source, story_key="DEV-40")
    assert plan["source_branch"] == "feature/IMPR-12"
    assert plan["story_branch"] == "feature/DEV-40"
    assert plan["pr"]["head"] == "feature/IMPR-12"
    assert plan["pr"]["base"] == "feature/DEV-40"
    assert plan["openspec_change"] == "impr-12"
    assert plan["component"] == "payments"
    assert "sdd-from-IMPR-12" in plan["story_fields"]["labels"]


def test_resolve_tool_names_picks_first_available_alias():
    available = [
        "jira_search",
        "createJiraIssue",
        "create_branch",
        "createBitbucketRepoPullRequest",
    ]
    jira = resolve_tool_names(available, JIRA_TOOL_ALIASES)
    bitbucket = resolve_tool_names(available, BITBUCKET_TOOL_ALIASES)
    assert jira["search"] == "jira_search"
    assert jira["create"] == "createJiraIssue"
    assert jira["link"] is None
    assert bitbucket["create_branch"] == "create_branch"
    assert bitbucket["create_pr"] == "createBitbucketRepoPullRequest"
    assert missing_actions(jira, ("search", "create", "link")) == ["link"]
