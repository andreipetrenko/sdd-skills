from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from sdd_auto_release_to_uat.models import JiraIssue
from sdd_auto_release_to_uat.settings import Settings


@dataclass(frozen=True)
class ReleaseEvaluation:
    release_key: str
    release_status: str
    stories: tuple[JiraIssue, ...]
    ready_statuses: tuple[str, ...]
    target_statuses: tuple[str, ...]
    all_ready: bool
    already_target: bool
    should_transition: bool
    skip_reason: str | None = None
    not_ready: tuple[JiraIssue, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "release_key": self.release_key,
            "release_status": self.release_status,
            "stories": [
                {
                    "key": story.key,
                    "issue_type": story.issue_type,
                    "status": story.status,
                    "summary": story.summary,
                }
                for story in self.stories
            ],
            "not_ready": [
                {"key": story.key, "status": story.status, "issue_type": story.issue_type}
                for story in self.not_ready
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


def merge_stories(*groups: Iterable[JiraIssue]) -> tuple[JiraIssue, ...]:
    seen: dict[str, JiraIssue] = {}
    for group in groups:
        for story in group:
            if story.key and story.key not in seen:
                seen[story.key] = story
    return tuple(seen.values())


def filter_stories(stories: Iterable[JiraIssue], settings: Settings) -> tuple[JiraIssue, ...]:
    wanted = settings.stories.issue_types
    return tuple(story for story in stories if issue_type_matches(story.issue_type, wanted))


def evaluate_release(
    settings: Settings,
    release: JiraIssue,
    stories: Iterable[JiraIssue],
) -> ReleaseEvaluation:
    scoped = filter_stories(stories, settings)
    already_target = status_matches(release.status, settings.target.statuses)
    not_ready = tuple(
        story
        for story in scoped
        if not status_matches(story.status, settings.stories.ready_statuses)
    )
    all_ready = bool(scoped) and not not_ready

    skip_reason: str | None = None
    should_transition = False
    if already_target:
        skip_reason = "Epic/задача релиза уже в целевом статусе"
    elif not scoped:
        skip_reason = "нет Story у релиза — переход не выполняется"
    elif not_ready:
        keys = ", ".join(f"{story.key} ({story.status})" for story in not_ready)
        skip_reason = f"не все Story в статусе ready: {keys}"
    else:
        should_transition = True

    return ReleaseEvaluation(
        release_key=release.key,
        release_status=release.status,
        stories=scoped,
        ready_statuses=settings.stories.ready_statuses,
        target_statuses=settings.target.statuses,
        all_ready=all_ready,
        already_target=already_target,
        should_transition=should_transition,
        skip_reason=skip_reason,
        not_ready=not_ready,
    )


def parse_story_token(token: str) -> JiraIssue:
    """Parse `KEY:Status` or `KEY:Type:Status` from CLI."""
    parts = token.split(":")
    if len(parts) < 2 or not parts[0].strip():
        raise ValueError(f"ожидается KEY:STATUS или KEY:TYPE:STATUS, получено {token!r}")
    key = parts[0].strip()
    if len(parts) == 2:
        return JiraIssue(key=key, summary=key, issue_type="Story", status=parts[1].strip())
    issue_type = parts[1].strip()
    status = ":".join(parts[2:]).strip()
    return JiraIssue(key=key, summary=key, issue_type=issue_type, status=status)
