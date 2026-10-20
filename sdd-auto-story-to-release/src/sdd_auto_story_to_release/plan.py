from __future__ import annotations

from typing import Any, Iterable

from sdd_auto_story_to_release.bitbucket import repo_plan
from sdd_auto_story_to_release.compose import compose
from sdd_auto_story_to_release.mcp import BITBUCKET_TOOL_ALIASES, JIRA_TOOL_ALIASES
from sdd_auto_story_to_release.models import JiraIssue
from sdd_auto_story_to_release.settings import Settings


def build_plan(settings: Settings) -> dict[str, Any]:
    return {
        "input": "release Story key (CLI / пользователь), не JQL-поиск релиза",
        "stories": {
            "issue_types": list(settings.stories.issue_types),
            "via": settings.stories.via,
            "link_type": settings.stories.link_type,
            "project": settings.stories.project,
            "label": settings.stories.label,
            "status": settings.stories.status,
            "jql_pattern": settings.stories_jql("{RELEASE-KEY}", "{number}"),
        },
        "release": {
            "number": settings.release.number,
            "number_field": settings.release.number_field,
            "number_pattern": settings.release.number_pattern,
            "branch_patterns": list(settings.release.branch_patterns),
        },
        "components": [repo_plan(item) for item in settings.components],
        "fallback_component": settings.fallback_component,
        "limits": {"max_stories": settings.max_stories},
        "mcp": {
            "jira_tool_aliases": JIRA_TOOL_ALIASES,
            "bitbucket_tool_aliases": BITBUCKET_TOOL_ALIASES,
            "rule": (
                "Use already connected Jira MCP and Bitbucket MCP. "
                "Do not call REST APIs and do not ask for tokens."
            ),
        },
        "steps": [
            "1 get the release Story by the given key via Jira MCP",
            "2 extract release number (settings / --release-number / fixVersion / summary)",
            "3 search child/linked Stories (same via as sdd-auto-story-to-uat)",
            "4 read Jira Component on each Story (same field as sdd-auto-impr-to-story)",
            "5 create release/{number} from component default_branch in each mapped repo",
            "6 for each Story × component, create PR feature/{STORY-KEY} → release/{number}",
            "7 skip Story/component pairs that have no Component or no repo in settings",
        ],
    }


def build_issue_plan(
    settings: Settings,
    release: JiraIssue,
    stories: Iterable[JiraIssue] = (),
    *,
    release_number: str | None = None,
) -> dict[str, Any]:
    composition = compose(settings, release, stories, release_number=release_number)
    return {
        "release_key": release.key,
        "release_number": composition.release_number,
        "stories_jql": settings.stories_jql(release.key, composition.release_number),
        "composition": composition.to_dict(),
        "mcp": {
            "get_release": {"issueKey": release.key},
            "search_stories": {
                "jql": settings.stories_jql(release.key, composition.release_number),
                "maxResults": settings.max_stories,
            },
            "get_story": "get each Story if search payload has no components",
            "create_branch": [
                {
                    "name": branch.name,
                    "start_point": branch.start_point,
                    "repository": branch.bitbucket,
                }
                for branch in composition.branches
            ],
            "create_pr": [
                {
                    "head": pr.head,
                    "base": pr.base,
                    "title": pr.title,
                    "repository": pr.bitbucket,
                    "when": "list_prs has no PR with this head/base",
                }
                for pr in composition.pull_requests
            ],
        },
    }
