from __future__ import annotations

from typing import Any, Iterable

from sdd_auto_story_to_ift.evaluate import StoryEvaluation, evaluate_story
from sdd_auto_story_to_ift.mcp import JIRA_TOOL_ALIASES, match_transition, parse_transitions
from sdd_auto_story_to_ift.models import JiraIssue
from sdd_auto_story_to_ift.settings import Settings


def build_plan(settings: Settings) -> dict[str, Any]:
    return {
        "source_jql": settings.source.jql(),
        "source": {
            "project": settings.source.project,
            "issue_type": settings.source.issue_type,
            "label": settings.source.label,
            "status": settings.source.status,
        },
        "children": {
            "issue_types": list(settings.children.issue_types),
            "ready_statuses": list(settings.children.ready_statuses),
            "jql_pattern": settings.children.jql("{STORY-KEY}"),
        },
        "target_statuses": list(settings.target.statuses),
        "limits": {
            "max_issues": settings.max_issues,
            "max_children": settings.max_children,
        },
        "mcp": {
            "jira_tool_aliases": JIRA_TOOL_ALIASES,
            "rule": (
                "Use already connected Jira MCP. "
                "Do not call REST APIs and do not ask for tokens."
            ),
        },
        "steps": [
            "1 search stories via Jira MCP using source JQL",
            "2 for each story, search child Task/Sub-task via parent JQL",
            "3 if the story has no matching children, skip it",
            "4 if any matching child is not in ready status, skip the story",
            "5 if all matching children are ready, get transitions for the story",
            "6 pick the first transition whose name or destination matches target statuses",
            "7 transition the story via Jira MCP; do not write via REST",
        ],
    }


def build_issue_plan(
    settings: Settings,
    story: JiraIssue,
    children: Iterable[JiraIssue] = (),
    transitions: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evaluation = evaluate_story(settings, story, children)
    chosen = None
    if transitions is not None:
        chosen = match_transition(parse_transitions(transitions), settings.target.statuses)
    return {
        "story_key": story.key,
        "story_status": story.status,
        "children_jql": settings.children_jql(story.key),
        "children_max_results": settings.max_children,
        "evaluation": evaluation.to_dict(),
        "transition": {
            "wanted_statuses": list(settings.target.statuses),
            "matched": chosen,
        },
        "mcp": {
            "search_stories": {
                "jql": settings.source.jql(),
                "maxResults": settings.max_issues,
            },
            "search_children": {
                "jql": settings.children_jql(story.key),
                "maxResults": settings.max_children,
            },
            "get_story": {"issueKey": story.key},
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
