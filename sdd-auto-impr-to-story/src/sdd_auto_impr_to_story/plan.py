from __future__ import annotations

from typing import Any

from sdd_auto_impr_to_story.bitbucket import parse_bitbucket_url
from sdd_auto_impr_to_story.fields import build_related_fields, build_story_fields, resolve_component
from sdd_auto_impr_to_story.mcp import BITBUCKET_TOOL_ALIASES, JIRA_TOOL_ALIASES
from sdd_auto_impr_to_story.models import JiraIssue
from sdd_auto_impr_to_story.settings import BitbucketConfig, Settings


def _repo_plan(cfg: BitbucketConfig) -> dict[str, Any]:
    bb = parse_bitbucket_url(cfg.repository)
    return {
        "repository": cfg.repository,
        "workspace": cfg.workspace or bb.workspace,
        "repo_slug": cfg.repo_slug or bb.repo_slug,
        "project": cfg.project or bb.project,
        "default_branch": cfg.default_branch,
        "source_branch_pattern": cfg.source_branch_pattern,
        "story_branch_pattern": cfg.story_branch_pattern,
        "task_branch_pattern": cfg.task_branch_pattern,
    }


def build_plan(settings: Settings) -> dict[str, Any]:
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
            "in_progress_statuses": list(settings.related.in_progress_statuses),
            "done_statuses": list(settings.related.done_statuses),
        },
        "story_done_statuses": list(settings.story.done_statuses),
        "bitbucket": _repo_plan(settings.bitbucket),
        "component": _repo_plan(settings.component),
        "after_merge_statuses": list(settings.after_merge.statuses),
        "improvement_done_statuses": list(settings.improvement_done.statuses),
        "openspec": {
            "capabilities": list(settings.openspec.capabilities),
            "change_id_pattern": settings.openspec.change_id_pattern,
            "implementation_capability": settings.openspec.implementation_capability,
            "implementation_change_id_pattern": settings.openspec.implementation_change_id_pattern,
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
            "8 after BR/FR merge, transition source issue to In Progress via Jira MCP",
            "9 generate OpenSpec code-change spec for the component",
            "10 push spec to feature branch named after task key in specs repo",
            "11 create PR task-branch -> story-branch in specs repo",
            "12 after merge, transition task to in-progress from settings",
            "13 create task branch in component repo from component default_branch",
            "14 generate code with OpenSpec from the code-change spec",
            "15 push code to the component task branch",
            "16 create story branch in component repo; PR task-branch -> story-branch",
            "17 after merge, transition task to done from settings",
            "18 transition story to done from settings",
            "19 transition improvement to done from settings",
        ],
    }


def build_issue_plan(
    settings: Settings,
    source: JiraIssue,
    story_key: str | None = None,
    task_key: str | None = None,
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
        "implementation": _implementation_plan(settings, source, fake_story.key, task_key),
    }


def _implementation_plan(
    settings: Settings,
    source: JiraIssue,
    story_key: str,
    task_key: str | None,
) -> dict[str, Any]:
    task = task_key or "{TASK-KEY}"
    specs_task_branch = settings.specs_task_branch_name(task) if task_key else None
    specs_story_branch = settings.story_branch_name(story_key)
    component_task_branch = settings.component_task_branch_name(task) if task_key else None
    component_story_branch = settings.component_story_branch_name(story_key)
    impl_change = (
        settings.implementation_change_id(task_key, source.key) if task_key else None
    )
    return {
        "task_key": task_key,
        "openspec_change": impl_change,
        "capability": settings.openspec.implementation_capability,
        "specs_repo": {
            "task_branch": specs_task_branch,
            "story_branch": specs_story_branch,
            "pr": {
                "head": specs_task_branch,
                "base": specs_story_branch,
                "title": f"{task} → {story_key}: OpenSpec code changes",
            },
        },
        "component_repo": {
            "task_branch": component_task_branch,
            "story_branch": component_story_branch,
            "default_branch": settings.component.default_branch,
            "pr": {
                "head": component_task_branch,
                "base": component_story_branch,
                "title": f"{task} → {story_key}: implement {settings.openspec.implementation_capability}",
            },
        },
        "statuses": {
            "task_in_progress": list(settings.related.in_progress_statuses),
            "task_done": list(settings.related.done_statuses),
            "story_done": list(settings.story.done_statuses),
            "improvement_done": list(settings.improvement_done.statuses),
        },
    }
