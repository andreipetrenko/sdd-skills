from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from sdd_auto_story_to_release.bitbucket import repo_plan
from sdd_auto_story_to_release.models import JiraIssue, field_values
from sdd_auto_story_to_release.settings import ComponentRepo, Settings


@dataclass(frozen=True)
class Skip:
    story_key: str | None
    component: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"story_key": self.story_key, "component": self.component, "reason": self.reason}


@dataclass(frozen=True)
class BranchPlan:
    component: str
    repository: str
    name: str
    start_point: str
    bitbucket: dict[str, str | None]

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "repository": self.repository,
            "name": self.name,
            "start_point": self.start_point,
            "bitbucket": self.bitbucket,
        }


@dataclass(frozen=True)
class PrPlan:
    story_key: str
    component: str
    repository: str
    head: str
    base: str
    title: str
    bitbucket: dict[str, str | None]

    def to_dict(self) -> dict[str, Any]:
        return {
            "story_key": self.story_key,
            "component": self.component,
            "repository": self.repository,
            "head": self.head,
            "base": self.base,
            "title": self.title,
            "bitbucket": self.bitbucket,
        }


@dataclass(frozen=True)
class Composition:
    release_key: str
    release_number: str
    stories: tuple[JiraIssue, ...]
    branches: tuple[BranchPlan, ...]
    pull_requests: tuple[PrPlan, ...]
    skipped: tuple[Skip, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "release_key": self.release_key,
            "release_number": self.release_number,
            "stories": [
                {
                    "key": story.key,
                    "summary": story.summary,
                    "issue_type": story.issue_type,
                    "status": story.status,
                    "components": list(story.components),
                }
                for story in self.stories
            ],
            "branches": [item.to_dict() for item in self.branches],
            "pull_requests": [item.to_dict() for item in self.pull_requests],
            "skipped": [item.to_dict() for item in self.skipped],
        }


def extract_release_number(
    settings: Settings,
    release: JiraIssue | None = None,
    explicit: str | None = None,
) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    if settings.release.number:
        return settings.release.number
    if release is None:
        raise ValueError("номер релиза не задан: укажи release.number или --release-number")
    if settings.release.number_field:
        for value in field_values(release, settings.release.number_field):
            found = _first_number(value, settings.release.number_pattern)
            if found:
                return found
        raise ValueError(
            f"не удалось взять номер релиза из поля {settings.release.number_field}"
        )
    for value in field_values(release, "fixVersions"):
        found = _first_number(value, settings.release.number_pattern)
        if found:
            return found
    for candidate in (release.summary, release.key, release.description, *release.labels):
        found = _first_number(candidate, settings.release.number_pattern)
        if found:
            return found
    raise ValueError(
        f"не удалось извлечь номер релиза из {release.key}: задай release.number "
        "или --release-number"
    )


def issue_type_matches(issue_type: str, wanted: Iterable[str]) -> bool:
    target = {item.casefold() for item in wanted if str(item).strip()}
    return bool(issue_type) and issue_type.casefold() in target


def story_components(story: JiraIssue, settings: Settings) -> tuple[str, ...]:
    if story.components:
        return story.components
    if settings.fallback_component:
        return (settings.fallback_component,)
    return ()


def compose(
    settings: Settings,
    release: JiraIssue,
    stories: Iterable[JiraIssue],
    *,
    release_number: str | None = None,
) -> Composition:
    number = extract_release_number(settings, release, explicit=release_number)
    release_branch = settings.release.branch_name(number)
    scoped = tuple(
        story
        for story in stories
        if issue_type_matches(story.issue_type, settings.stories.issue_types)
    )
    skipped: list[Skip] = []
    branches: dict[tuple[str, str], BranchPlan] = {}
    prs: list[PrPlan] = []

    if not scoped:
        skipped.append(
            Skip(
                story_key=None,
                component=None,
                reason="нет Story в составе релиза — ветки и PR не создаются",
            )
        )
        return Composition(
            release_key=release.key,
            release_number=number,
            stories=scoped,
            branches=(),
            pull_requests=(),
            skipped=tuple(skipped),
        )

    for story in scoped:
        names = story_components(story, settings)
        if not names:
            skipped.append(
                Skip(
                    story_key=story.key,
                    component=None,
                    reason="у Story нет Jira Component, и related.component / component.name не задан",
                )
            )
            continue
        for name in names:
            repo = settings.lookup_component(name)
            if repo is None:
                skipped.append(
                    Skip(
                        story_key=story.key,
                        component=name,
                        reason=f"нет репозитория для компонента {name} в settings",
                    )
                )
                continue
            _add_branch(branches, name, repo, release_branch)
            prs.append(_pr_plan(story.key, name, repo, release_branch))

    return Composition(
        release_key=release.key,
        release_number=number,
        stories=scoped,
        branches=tuple(branches.values()),
        pull_requests=tuple(prs),
        skipped=tuple(skipped),
    )


def parse_story_token(token: str) -> JiraIssue:
    """Parse `KEY:component` or `KEY:Type:component` from CLI."""
    parts = token.split(":")
    if len(parts) < 2 or not parts[0].strip():
        raise ValueError(f"ожидается KEY:COMPONENT или KEY:TYPE:COMPONENT, получено {token!r}")
    key = parts[0].strip()
    if len(parts) == 2:
        return JiraIssue(key=key, summary=key, issue_type="Story", components=(parts[1].strip(),))
    return JiraIssue(
        key=key,
        summary=key,
        issue_type=parts[1].strip(),
        components=(parts[2].strip(),) if parts[2].strip() else (),
    )


def _add_branch(
    branches: dict[tuple[str, str], BranchPlan],
    name: str,
    repo: ComponentRepo,
    release_branch: str,
) -> None:
    key = (repo.repository, release_branch)
    if key not in branches:
        branches[key] = BranchPlan(
            component=name,
            repository=repo.repository,
            name=release_branch,
            start_point=repo.default_branch,
            bitbucket=repo_plan(repo),
        )


def _pr_plan(story_key: str, name: str, repo: ComponentRepo, release_branch: str) -> PrPlan:
    head = repo.story_branch_name(story_key)
    return PrPlan(
        story_key=story_key,
        component=name,
        repository=repo.repository,
        head=head,
        base=release_branch,
        title=f"{story_key} → {release_branch}",
        bitbucket=repo_plan(repo),
    )


def _first_number(text: str, pattern: str) -> str | None:
    if not text:
        return None
    match = re.search(pattern, text)
    if not match:
        return None
    return match.group(1) if match.lastindex else match.group(0)
