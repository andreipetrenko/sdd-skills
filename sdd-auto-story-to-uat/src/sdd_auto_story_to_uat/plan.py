from __future__ import annotations

from typing import Any, Iterable

from sdd_auto_story_to_uat.bitbucket import repo_plans
from sdd_auto_story_to_uat.evaluate import StoryEvaluation, evaluate_story, extract_release_number
from sdd_auto_story_to_uat.mcp import (
    BITBUCKET_TOOL_ALIASES,
    JIRA_TOOL_ALIASES,
    match_transition,
    parse_transitions,
)
from sdd_auto_story_to_uat.models import JiraIssue, PullRequest
from sdd_auto_story_to_uat.settings import Settings


def build_plan(settings: Settings) -> dict[str, Any]:
    return {
        "source_jql": settings.source.jql(),
        "source": {
            "project": settings.source.project,
            "issue_type": settings.source.issue_type,
            "label": settings.source.label,
            "status": settings.source.status,
        },
        "stories": {
            "issue_types": list(settings.stories.issue_types),
            "via": settings.stories.via,
            "link_type": settings.stories.link_type,
            "project": settings.stories.project,
            "label": settings.stories.label,
            "status": settings.stories.status,
            "jql_pattern": settings.stories_jql("{RELEASE-KEY}", "{number}"),
        },
        "children": {"issue_types": list(settings.children.issue_types)},
        "release": {
            "number": settings.release.number,
            "number_field": settings.release.number_field,
            "number_pattern": settings.release.number_pattern,
            "branch_patterns": list(settings.release.branch_patterns),
        },
        "bitbucket": repo_plans(settings.bitbucket),
        "pr": {
            "include_child_keys": settings.pr.include_child_keys,
            "merged_states": list(settings.pr.merged_states),
            "ignore_states": list(settings.pr.ignore_states),
            "ignore_destination_prefixes": list(settings.pr.ignore_destination_prefixes),
        },
        "target_statuses": list(settings.target.statuses),
        "limits": {
            "max_issues": settings.max_issues,
            "max_stories": settings.max_stories,
            "max_children": settings.max_children,
            "max_prs": settings.max_prs,
        },
        "mcp": {
            "jira_tool_aliases": JIRA_TOOL_ALIASES,
            "bitbucket_tool_aliases": BITBUCKET_TOOL_ALIASES,
            "rule": (
                "Use already connected Jira MCP and Bitbucket MCP. "
                "Do not call REST APIs and do not ask for tokens."
            ),
        },
        "steps": [
            "1 search release tasks via Jira MCP using source JQL",
            "2 extract release number from settings, --release-number, fixVersion or summary",
            "3 search Stories under the release (parent and/or linkedIssues)",
            "4 for each Story, optionally search child Task/Sub-task keys",
            "5 list PRs via Bitbucket MCP in configured repositories",
            "6 keep PRs that mention the Story (or child) key",
            "7 ignore declined/superseded PRs and feature/task destinations",
            "8 if all remaining PRs are MERGED into release/{number}, transition that Story",
            "9 do not wait for the whole release: apply per Story that meets the condition",
        ],
    }


def build_issue_plan(
    settings: Settings,
    release: JiraIssue,
    story: JiraIssue,
    prs: Iterable[PullRequest] = (),
    *,
    release_number: str | None = None,
    child_keys: Iterable[str] = (),
    transitions: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    number = extract_release_number(settings, release, explicit=release_number)
    evaluation = evaluate_story(
        settings,
        story,
        prs,
        release_number=number,
        release_key=release.key,
        child_keys=child_keys,
    )
    chosen = None
    if transitions is not None:
        chosen = match_transition(parse_transitions(transitions), settings.target.statuses)
    return {
        "release_key": release.key,
        "release_number": number,
        "story_key": story.key,
        "story_status": story.status,
        "stories_jql": settings.stories_jql(release.key, number),
        "children_jql": settings.children_jql(story.key),
        "evaluation": evaluation.to_dict(),
        "transition": {
            "wanted_statuses": list(settings.target.statuses),
            "matched": chosen,
        },
        "mcp": {
            "search_releases": {
                "jql": settings.source.jql(),
                "maxResults": settings.max_issues,
            },
            "search_stories": {
                "jql": settings.stories_jql(release.key, number),
                "maxResults": settings.max_stories,
            },
            "search_children": {
                "jql": settings.children_jql(story.key),
                "maxResults": settings.max_children,
            },
            "list_prs": {
                "repositories": repo_plans(settings.bitbucket),
                "maxResults": settings.max_prs,
            },
            "get_transitions": {"issueKey": story.key},
            "transition_story": {
                "issueKey": story.key,
                "when": "should_transition is true and a matching transition id exists",
            },
        },
    }


def summarize_evaluations(results: Iterable[StoryEvaluation]) -> dict[str, Any]:
    items = list(results)
    return {
        "total": len(items),
        "transition": [item.story_key for item in items if item.should_transition],
        "skipped": [
            {"story_key": item.story_key, "reason": item.skip_reason}
            for item in items
            if not item.should_transition
        ],
    }
