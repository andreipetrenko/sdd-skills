from __future__ import annotations

from typing import Any

from sdd_auto_impr_to_story.bitbucket import parse_bitbucket_url
from sdd_auto_impr_to_story.fields import build_related_fields, build_story_fields, resolve_component
from sdd_auto_impr_to_story.mcp import BITBUCKET_TOOL_ALIASES, JIRA_TOOL_ALIASES
from sdd_auto_impr_to_story.models import JiraIssue
from sdd_auto_impr_to_story.settings import Settings


def build_plan(settings: Settings) -> dict[str, Any]:
    bb = parse_bitbucket_url(settings.bitbucket.repository)
    workspace = settings.bitbucket.workspace or bb.workspace
    repo_slug = settings.bitbucket.repo_slug or bb.repo_slug
    return {
        "source_jql": settings.source.jql(),
        "source": {
            "project": settings.source.project,
            "issue_type": settings.source.issue_type,
            "label": settings.source.label,
            "status": settings.source.status,
        },
        "story": {
            "project": settings.story.project,
            "issue_type": settings.story.issue_type,
            "label": settings.story.label,
            "status": settings.story.status,
            "link_type": settings.story.link_type,
        },
        "related": {
            "project": settings.related.project or settings.story.project,
            "issue_type": settings.related.issue_type,
            "link_type": settings.related.link_type,
            "component": settings.related.component,
            "component_from_source": settings.related.component_from_source,
            "label": settings.related.label,
            "status": settings.related.status,
        },
        "bitbucket": {
            "repository": settings.bitbucket.repository,
            "workspace": workspace,
            "repo_slug": repo_slug,
            "project": settings.bitbucket.project or bb.project,
            "default_branch": settings.bitbucket.default_branch,
            "source_branch_pattern": settings.bitbucket.source_branch_pattern,
            "story_branch_pattern": settings.bitbucket.story_branch_pattern,
        },
        "after_merge_statuses": list(settings.after_merge.statuses),
        "openspec": {
            "capabilities": list(settings.openspec.capabilities),
            "change_id_pattern": settings.openspec.change_id_pattern,
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
            "1 search source issues via Jira MCP",
            "2 create story via Jira MCP",
            "3 create Bitbucket branch named after source key",
            "4 generate OpenSpec BR/FR, commit, push to source branch",
            "5 create related issue + link + component via Jira MCP",
            "6 create Bitbucket branch named after story key",
            "7 create Bitbucket PR source-branch -> story-branch",
            "8 after merge, transition source issue to In Progress via Jira MCP",
        ],
    }


def build_issue_plan(
    settings: Settings,
    source: JiraIssue,
    story_key: str | None = None,
) -> dict[str, Any]:
    story_fields = build_story_fields(settings, source)
    fake_story = JiraIssue(
        key=story_key or f"{settings.story.project}-?",
        summary=story_fields["summary"],
        description=story_fields["description"],
        issue_type=settings.story.issue_type,
        status=settings.story.status or "",
        labels=tuple(story_fields["labels"]),
    )
    component = resolve_component(settings, source, fake_story)
    related_fields = build_related_fields(settings, source, fake_story, component)
    source_branch = settings.source_branch_name(source.key)
    story_branch = settings.story_branch_name(fake_story.key) if story_key else settings.story_branch_name("{STORY-KEY}")
    return {
        "source_key": source.key,
        "source_branch": source_branch,
        "story_branch": story_branch if story_key else None,
        "story_branch_pattern": settings.bitbucket.story_branch_pattern,
        "openspec_change": settings.change_id(source.key),
        "story_fields": story_fields,
        "related_fields": related_fields,
        "component": component,
        "pr": {
            "head": source_branch,
            "base": story_branch if story_key else None,
            "title": f"{source.key} → {fake_story.key}: OpenSpec BR/FR",
        },
    }
