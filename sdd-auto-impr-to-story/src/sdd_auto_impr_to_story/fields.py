from __future__ import annotations

from typing import Any

from sdd_auto_impr_to_story.models import JiraIssue
from sdd_auto_impr_to_story.settings import Settings


def build_story_fields(settings: Settings, source: JiraIssue) -> dict[str, Any]:
    summary = settings.story.summary_pattern.format(
        source_key=source.key,
        source_summary=source.summary,
    )
    labels = [item for item in [settings.story.label, settings.story_label_for(source.key)] if item]
    return {
        "project": settings.story.project,
        "issue_type": settings.story.issue_type,
        "summary": summary,
        "description": _story_description(source),
        "labels": labels,
        "status": settings.story.status,
        "link_type": settings.story.link_type,
        "link_inward": "story",
        "link_outward": "source",
    }


def resolve_component(settings: Settings, source: JiraIssue, story: JiraIssue | None = None) -> str | None:
    if settings.related.component_from_source:
        if source.components:
            return source.components[0]
        if story and story.components:
            return story.components[0]
    return settings.related.component


def build_related_fields(
    settings: Settings,
    source: JiraIssue,
    story: JiraIssue,
    component: str | None,
) -> dict[str, Any]:
    summary = settings.related.summary_pattern.format(
        component=component or "unspecified",
        story_key=story.key,
        story_summary=story.summary,
        source_key=source.key,
        source_summary=source.summary,
    )
    labels = [
        item
        for item in [settings.related.label, settings.related_label_for(story.key)]
        if item
    ]
    description = (
        f"Implementation task for {story.key} ({story.summary}).\n"
        f"Source improvement: {source.key}.\n"
        f"Component: {component or 'not set'}.\n"
        f"OpenSpec change: `{settings.change_id(source.key)}`.\n"
    )
    return {
        "project": settings.related.project or settings.story.project,
        "issue_type": settings.related.issue_type,
        "summary": summary,
        "description": description,
        "labels": labels,
        "status": settings.related.status,
        "components": [component] if component else [],
        "link_type": settings.related.link_type,
        "link_inward": "story",
        "link_outward": "related",
    }


def _story_description(source: JiraIssue) -> str:
    body = source.description.strip() or "_No description on the source issue._"
    return (
        f"Created from {source.key}: {source.summary}\n\n"
        f"{body}\n\n"
        f"Source: {source.url or source.key}\n"
    )
