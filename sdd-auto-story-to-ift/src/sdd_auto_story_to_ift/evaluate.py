from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from sdd_auto_story_to_ift.models import JiraIssue
from sdd_auto_story_to_ift.settings import Settings


@dataclass(frozen=True)
class StoryEvaluation:
    story_key: str
    story_status: str
    children: tuple[JiraIssue, ...]
    ready_statuses: tuple[str, ...]
    target_statuses: tuple[str, ...]
    all_ready: bool
    already_target: bool
    should_transition: bool
    skip_reason: str | None = None
    not_ready: tuple[JiraIssue, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "story_key": self.story_key,
            "story_status": self.story_status,
            "children": [
                {
                    "key": child.key,
                    "issue_type": child.issue_type,
                    "status": child.status,
                    "summary": child.summary,
                }
                for child in self.children
            ],
            "not_ready": [
                {"key": child.key, "status": child.status, "issue_type": child.issue_type}
                for child in self.not_ready
            ],
            "ready_statuses": list(self.ready_statuses),
            "target_statuses": list(self.target_statuses),
            "all_ready": self.all_ready,
            "already_target": self.already_target,
            "should_transition": self.should_transition,
            "skip_reason": self.skip_reason,
        }


def status_matches(status: str, wanted: Iterable[str]) -> bool:
    target = {item.casefold() for item in wanted if str(item).strip()}
    return bool(status) and status.casefold() in target


def issue_type_matches(issue_type: str, wanted: Iterable[str]) -> bool:
    target = {item.casefold() for item in wanted if str(item).strip()}
    return bool(issue_type) and issue_type.casefold() in target


def merge_children(*groups: Iterable[JiraIssue]) -> tuple[JiraIssue, ...]:
    seen: dict[str, JiraIssue] = {}
    for group in groups:
        for child in group:
            if child.key and child.key not in seen:
                seen[child.key] = child
    return tuple(seen.values())


def filter_children(children: Iterable[JiraIssue], settings: Settings) -> tuple[JiraIssue, ...]:
    wanted = settings.children.issue_types
    return tuple(child for child in children if issue_type_matches(child.issue_type, wanted))


def evaluate_story(
    settings: Settings,
    story: JiraIssue,
    children: Iterable[JiraIssue],
) -> StoryEvaluation:
    scoped = filter_children(children, settings)
    already_target = status_matches(story.status, settings.target.statuses)
    not_ready = tuple(
        child for child in scoped if not status_matches(child.status, settings.children.ready_statuses)
    )
    all_ready = bool(scoped) and not not_ready

    skip_reason: str | None = None
    should_transition = False
    if already_target:
        skip_reason = "Story уже в целевом статусе"
    elif not scoped:
        skip_reason = "нет дочерних задач указанного типа — переход не выполняется"
    elif not_ready:
        keys = ", ".join(f"{child.key} ({child.status})" for child in not_ready)
        skip_reason = f"не все дочерние в статусе ready: {keys}"
    else:
        should_transition = True

    return StoryEvaluation(
        story_key=story.key,
        story_status=story.status,
        children=scoped,
        ready_statuses=settings.children.ready_statuses,
        target_statuses=settings.target.statuses,
        all_ready=all_ready,
        already_target=already_target,
        should_transition=should_transition,
        skip_reason=skip_reason,
        not_ready=not_ready,
    )


def parse_child_token(token: str) -> JiraIssue:
    """Parse `KEY:Status` or `KEY:Type:Status` from CLI."""
    parts = token.split(":")
    if len(parts) < 2 or not parts[0].strip():
        raise ValueError(f"ожидается KEY:STATUS или KEY:TYPE:STATUS, получено {token!r}")
    key = parts[0].strip()
    if len(parts) == 2:
        return JiraIssue(key=key, summary=key, issue_type="Task", status=parts[1].strip())
    issue_type = parts[1].strip()
    status = ":".join(parts[2:]).strip()
    return JiraIssue(key=key, summary=key, issue_type=issue_type, status=status)
