from __future__ import annotations

from typing import Any, Iterable

from sdd_auto_release_to_uat.evaluate import ReleaseEvaluation, evaluate_release
from sdd_auto_release_to_uat.mcp import JIRA_TOOL_ALIASES, match_transition, parse_transitions
from sdd_auto_release_to_uat.models import JiraIssue
from sdd_auto_release_to_uat.settings import Settings


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
            "ready_statuses": list(settings.stories.ready_statuses),
            "jql_pattern": settings.stories_jql("{RELEASE-KEY}"),
        },
        "target_statuses": list(settings.target.statuses),
        "limits": {
            "max_issues": settings.max_issues,
            "max_stories": settings.max_stories,
        },
        "mcp": {
            "jira_tool_aliases": JIRA_TOOL_ALIASES,
            "rule": (
                "Use already connected Jira MCP. "
                "Do not call REST APIs and do not ask for tokens."
            ),
        },
        "steps": [
            "1 search release Epic/task via Jira MCP using source JQL",
            "2 for each release, search Stories via parent and/or linkedIssues",
            "3 if there are no Stories, skip the release",
            "4 if any Story is not in ready status, skip the release",
            "5 if all Stories are ready, get transitions for the release Epic/task",
            "6 pick the first transition whose name or destination matches target statuses",
            "7 transition the release via Jira MCP; do not write via REST",
        ],
    }


def build_issue_plan(
    settings: Settings,
    release: JiraIssue,
    stories: Iterable[JiraIssue] = (),
    transitions: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evaluation = evaluate_release(settings, release, stories)
    chosen = None
    if transitions is not None:
        chosen = match_transition(parse_transitions(transitions), settings.target.statuses)
    return {
        "release_key": release.key,
        "release_status": release.status,
        "stories_jql": settings.stories_jql(release.key),
        "stories_max_results": settings.max_stories,
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
                "jql": settings.stories_jql(release.key),
                "maxResults": settings.max_stories,
            },
            "get_release": {"issueKey": release.key},
            "get_transitions": {"issueKey": release.key},
            "transition_release": {
                "issueKey": release.key,
                "when": "should_transition is true and a matching transition id exists",
            },
        },
    }


def summarize_evaluations(results: Iterable[ReleaseEvaluation]) -> dict[str, Any]:
    items = list(results)
    return {
        "total": len(items),
        "transition": [item.release_key for item in items if item.should_transition],
        "skipped": [
            {"release_key": item.release_key, "reason": item.skip_reason}
            for item in items
            if not item.should_transition
        ],
    }
