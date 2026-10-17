from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from sdd_auto_story_to_uat.models import JiraIssue, PullRequest, field_values
from sdd_auto_story_to_uat.settings import Settings


@dataclass(frozen=True)
class StoryEvaluation:
    story_key: str
    story_status: str
    release_key: str | None
    release_number: str
    match_keys: tuple[str, ...]
    prs: tuple[PullRequest, ...]
    considered: tuple[PullRequest, ...]
    not_ready: tuple[PullRequest, ...]
    all_merged_to_release: bool
    already_target: bool
    should_transition: bool
    skip_reason: str | None = None
    target_statuses: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "story_key": self.story_key,
            "story_status": self.story_status,
            "release_key": self.release_key,
            "release_number": self.release_number,
            "match_keys": list(self.match_keys),
            "prs": [_pr_dict(item) for item in self.prs],
            "considered": [_pr_dict(item) for item in self.considered],
            "not_ready": [_pr_dict(item) for item in self.not_ready],
            "all_merged_to_release": self.all_merged_to_release,
            "already_target": self.already_target,
            "should_transition": self.should_transition,
            "skip_reason": self.skip_reason,
            "target_statuses": list(self.target_statuses),
        }


def status_matches(status: str, wanted: Iterable[str]) -> bool:
    target = {item.casefold() for item in wanted if str(item).strip()}
    return bool(status) and status.casefold() in target


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


def pr_mentions_keys(pr: PullRequest, keys: Iterable[str]) -> bool:
    haystacks = (
        pr.title,
        pr.source_branch,
        pr.destination_branch,
        pr.description,
        pr.id,
    )
    blob = " ".join(haystacks).casefold()
    for key in keys:
        token = key.strip()
        if not token:
            continue
        if re.search(rf"(?<![A-Z0-9-]){re.escape(token)}(?![A-Z0-9])", blob, flags=re.I):
            return True
    return False


def is_ignored_state(pr: PullRequest, settings: Settings) -> bool:
    return pr.state.casefold() in {item.casefold() for item in settings.pr.ignore_states}


def is_ignored_destination(pr: PullRequest, settings: Settings) -> bool:
    dest = pr.destination_branch.casefold()
    return any(dest.startswith(prefix.casefold()) for prefix in settings.pr.ignore_destination_prefixes)


def is_merged(pr: PullRequest, settings: Settings) -> bool:
    if pr.merged is True:
        return True
    return pr.state.casefold() in {item.casefold() for item in settings.pr.merged_states}


def is_release_destination(branch: str, number: str, patterns: Iterable[str]) -> bool:
    cleaned = branch.strip().removeprefix("refs/heads/")
    if not cleaned or not number:
        return False
    for pattern in patterns:
        expected = pattern.format(number=number)
        if cleaned.casefold() == expected.casefold():
            return True
        prefix, sep, _suffix = pattern.partition("{number}")
        if not sep:
            if number.casefold() in cleaned.casefold() and cleaned.casefold() == pattern.casefold():
                return True
            continue
        if not cleaned.casefold().startswith(prefix.casefold()):
            continue
        rest = cleaned[len(prefix) :]
        if _version_prefix_match(rest, number):
            return True
    return False


def evaluate_story(
    settings: Settings,
    story: JiraIssue,
    prs: Iterable[PullRequest],
    *,
    release_number: str,
    release_key: str | None = None,
    child_keys: Iterable[str] = (),
) -> StoryEvaluation:
    match_keys = (story.key, *(key for key in child_keys if key and key != story.key))
    if not settings.pr.include_child_keys:
        match_keys = (story.key,)
    belonging = tuple(pr for pr in prs if pr_mentions_keys(pr, match_keys))
    considered = tuple(
        pr
        for pr in belonging
        if not is_ignored_state(pr, settings) and not is_ignored_destination(pr, settings)
    )
    already_target = status_matches(story.status, settings.target.statuses)
    not_ready = tuple(
        pr
        for pr in considered
        if not (is_merged(pr, settings) and is_release_destination(
            pr.destination_branch, release_number, settings.release.branch_patterns
        ))
    )
    all_ready = bool(considered) and not not_ready

    skip_reason: str | None = None
    should_transition = False
    if already_target:
        skip_reason = "Story уже в целевом статусе"
    elif not release_number:
        skip_reason = "номер релиза не задан"
    elif not considered:
        skip_reason = "нет PR Story, которые нужно учитывать — переход не выполняется"
    elif not_ready:
        details = ", ".join(
            f"{pr.id or pr.title or pr.source_branch}:{pr.state}->{pr.destination_branch}"
            for pr in not_ready
        )
        skip_reason = f"не все PR влиты в release-ветку с номером {release_number}: {details}"
    else:
        should_transition = True

    return StoryEvaluation(
        story_key=story.key,
        story_status=story.status,
        release_key=release_key,
        release_number=release_number,
        match_keys=match_keys,
        prs=belonging,
        considered=considered,
        not_ready=not_ready,
        all_merged_to_release=all_ready,
        already_target=already_target,
        should_transition=should_transition,
        skip_reason=skip_reason,
        target_statuses=settings.target.statuses,
    )


def parse_pr_token(token: str) -> PullRequest:
    """Parse `STATE:DEST`, `SOURCE:STATE:DEST` or `ID:SOURCE:STATE:DEST`."""
    parts = token.split(":")
    if len(parts) < 2 or not parts[-1].strip():
        raise ValueError(f"ожидается STATE:DEST или SOURCE:STATE:DEST, получено {token!r}")
    if len(parts) == 2:
        return PullRequest(state=parts[0].strip(), destination_branch=parts[1].strip())
    if len(parts) == 3:
        source, state, dest = (part.strip() for part in parts)
        return PullRequest(
            title=source,
            source_branch=source,
            state=state,
            destination_branch=dest,
        )
    ident, source, state = (part.strip() for part in parts[:3])
    dest = ":".join(parts[3:]).strip()
    return PullRequest(
        id=ident,
        title=source,
        source_branch=source,
        state=state,
        destination_branch=dest,
    )


def _first_number(text: str, pattern: str) -> str | None:
    if not text:
        return None
    match = re.search(pattern, text)
    if not match:
        return None
    return match.group(1) if match.lastindex else match.group(0)


def _version_prefix_match(rest: str, number: str) -> bool:
    if rest == number:
        return True
    folded_rest, folded_number = rest.casefold(), number.casefold()
    if not folded_rest.startswith(folded_number):
        return False
    if len(rest) == len(number):
        return True
    return rest[len(number)] in {".", "/", "-", "_"}


def _pr_dict(pr: PullRequest) -> dict[str, Any]:
    return {
        "id": pr.id,
        "title": pr.title,
        "state": pr.state,
        "source_branch": pr.source_branch,
        "destination_branch": pr.destination_branch,
        "merged": pr.merged,
        "repository": pr.repository,
        "url": pr.url,
    }
