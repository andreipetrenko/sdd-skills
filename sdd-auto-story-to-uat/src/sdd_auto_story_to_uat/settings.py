from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class SettingsError(ValueError):
    pass


DEFAULT_STORY_ISSUE_TYPES = ("Story",)
DEFAULT_CHILD_ISSUE_TYPES = ("Task", "Sub-task", "Subtask")
DEFAULT_STORY_TARGET_STATUSES = ("Ready for UAT",)
DEFAULT_RELEASE_BRANCH_PATTERNS = ("release/{number}",)
DEFAULT_MERGED_STATES = ("MERGED", "merged")
DEFAULT_IGNORED_PR_STATES = ("DECLINED", "declined", "SUPERSEDED", "superseded")
DEFAULT_IGNORE_DEST_PREFIXES = ("feature/", "task/")
DEFAULT_NUMBER_PATTERN = r"(\d+(?:\.\d+)*)"


@dataclass(frozen=True)
class IssueFilter:
    """Jira search parameters: space (project), type, label, status."""

    project: str
    issue_type: str
    label: str | None = None
    status: str | None = None

    def jql(self) -> str:
        parts = [
            f'project = "{_escape_jql(self.project)}"',
            f'issuetype = "{_escape_jql(self.issue_type)}"',
        ]
        if self.label:
            parts.append(f'labels = "{_escape_jql(self.label)}"')
        if self.status:
            parts.append(f'status = "{_escape_jql(self.status)}"')
        return " AND ".join(parts) + " ORDER BY created ASC"


@dataclass(frozen=True)
class StoriesConfig:
    issue_types: tuple[str, ...] = DEFAULT_STORY_ISSUE_TYPES
    project: str | None = None
    label: str | None = None
    status: str | None = None
    via: str = "both"
    link_type: str | None = None
    jql_pattern: str | None = None

    def jql(self, release_key: str, release_number: str = "") -> str:
        if self.jql_pattern:
            return self.jql_pattern.format(
                release_key=release_key,
                release_number=release_number,
            )
        key = _escape_jql(release_key)
        type_clause = _issuetype_clause(self.issue_types)
        if self.via == "parent":
            scope = f'parent = "{key}"'
        elif self.via == "linked":
            scope = _linked_clause(key, self.link_type)
        else:
            scope = f'(parent = "{key}" OR {_linked_clause(key, self.link_type)})'
        parts = [scope, type_clause]
        if self.project:
            parts.append(f'project = "{_escape_jql(self.project)}"')
        if self.label:
            parts.append(f'labels = "{_escape_jql(self.label)}"')
        if self.status:
            parts.append(f'status = "{_escape_jql(self.status)}"')
        return " AND ".join(parts) + " ORDER BY created ASC"


@dataclass(frozen=True)
class ChildrenConfig:
    issue_types: tuple[str, ...] = DEFAULT_CHILD_ISSUE_TYPES

    def jql(self, parent_key: str) -> str:
        return (
            f'parent = "{_escape_jql(parent_key)}" AND '
            f"{_issuetype_clause(self.issue_types)} ORDER BY created ASC"
        )


@dataclass(frozen=True)
class ReleaseConfig:
    number: str | None = None
    number_field: str | None = None
    number_pattern: str = DEFAULT_NUMBER_PATTERN
    branch_patterns: tuple[str, ...] = DEFAULT_RELEASE_BRANCH_PATTERNS


@dataclass(frozen=True)
class BitbucketConfig:
    repositories: tuple[str, ...] = ()
    workspace: str | None = None
    repo_slug: str | None = None
    project: str | None = None


@dataclass(frozen=True)
class PrConfig:
    include_child_keys: bool = True
    merged_states: tuple[str, ...] = DEFAULT_MERGED_STATES
    ignore_states: tuple[str, ...] = DEFAULT_IGNORED_PR_STATES
    ignore_destination_prefixes: tuple[str, ...] = DEFAULT_IGNORE_DEST_PREFIXES


@dataclass(frozen=True)
class TargetConfig:
    statuses: tuple[str, ...] = DEFAULT_STORY_TARGET_STATUSES


@dataclass(frozen=True)
class Settings:
    jira_base_url: str | None
    source: IssueFilter
    stories: StoriesConfig = field(default_factory=StoriesConfig)
    children: ChildrenConfig = field(default_factory=ChildrenConfig)
    release: ReleaseConfig = field(default_factory=ReleaseConfig)
    bitbucket: BitbucketConfig = field(default_factory=BitbucketConfig)
    pr: PrConfig = field(default_factory=PrConfig)
    target: TargetConfig = field(default_factory=TargetConfig)
    max_issues: int = 20
    max_stories: int = 100
    max_children: int = 100
    max_prs: int = 100
    path: Path | None = None

    def stories_jql(self, release_key: str, release_number: str = "") -> str:
        return self.stories.jql(release_key, release_number)

    def children_jql(self, story_key: str) -> str:
        return self.children.jql(story_key)


def load_settings(path: str | Path) -> Settings:
    settings_path = Path(path).expanduser().resolve()
    if not settings_path.is_file():
        raise SettingsError(f"Settings file not found: {settings_path}")
    data = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SettingsError("settings.yaml must be a mapping")
    return parse_settings(data, path=settings_path)


def parse_settings(data: dict[str, Any], path: Path | None = None) -> Settings:
    jira = data.get("jira") or {}
    base_url = str(jira.get("base_url") or "").strip() or None
    source = _issue_filter(data.get("source") or data.get("release_task"), "source")
    stories = _stories_config(data.get("stories") or data.get("story"))
    children = _children_config(data.get("children") or (data.get("pr") or {}).get("children"))
    release = _release_config(data.get("release"))
    bitbucket = _bitbucket_config(data.get("bitbucket") or data.get("git") or data.get("repository"))
    pr = _pr_config(data.get("pr"))
    target = TargetConfig(
        statuses=_parse_statuses(
            data.get("target")
            or (data.get("story") or {}).get("target")
            or (data.get("story") or {}).get("target_status")
            or (data.get("story") or {}).get("target_statuses"),
            DEFAULT_STORY_TARGET_STATUSES,
        )
    )
    limits = data.get("limits") or {}
    return Settings(
        jira_base_url=base_url.rstrip("/") if base_url else None,
        source=source,
        stories=stories,
        children=children,
        release=release,
        bitbucket=bitbucket,
        pr=pr,
        target=target,
        max_issues=int(limits.get("max_issues") or data.get("max_issues") or 20),
        max_stories=int(limits.get("max_stories") or 100),
        max_children=int(limits.get("max_children") or 100),
        max_prs=int(limits.get("max_prs") or 100),
        path=path,
    )


def find_settings_file(explicit: str | Path | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    candidates = [
        Path.cwd() / "settings.yaml",
        Path.cwd() / "sdd-auto-story-to-uat" / "settings.yaml",
        Path.cwd() / ".gigacode/skills/sdd-auto-story-to-uat/settings.yaml",
        Path.cwd() / ".gigacode_vsc/skills/sdd-auto-story-to-uat/settings.yaml",
        Path.cwd() / "assets" / "settings.example.yaml",
        Path.cwd() / "sdd-auto-story-to-uat" / "assets" / "settings.example.yaml",
        Path.cwd() / ".gigacode/skills/sdd-auto-story-to-uat/assets/settings.example.yaml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SettingsError(
        "settings.yaml not found. Copy settings.example.yaml to settings.yaml "
        "or pass --settings."
    )


def _stories_config(raw: Any) -> StoriesConfig:
    if raw is None:
        return StoriesConfig()
    if not isinstance(raw, dict):
        raise SettingsError("stories must be a mapping")
    via = str(raw.get("via") or "both").strip().lower()
    if via not in {"parent", "linked", "both"}:
        raise SettingsError("stories.via must be parent, linked or both")
    return StoriesConfig(
        issue_types=_parse_issue_types(
            raw.get("issue_types") or raw.get("issue_type") or raw.get("type"),
            DEFAULT_STORY_ISSUE_TYPES,
        ),
        project=(
            str(raw.get("project") or raw.get("space") or "").strip() or None
        ),
        label=_first_label(raw.get("label") or raw.get("labels")),
        status=str(raw["status"]) if raw.get("status") else None,
        via=via,
        link_type=str(raw["link_type"]) if raw.get("link_type") else None,
        jql_pattern=str(raw["jql_pattern"]) if raw.get("jql_pattern") else None,
    )


def _children_config(raw: Any) -> ChildrenConfig:
    if raw is None:
        return ChildrenConfig()
    if not isinstance(raw, dict):
        raise SettingsError("children must be a mapping")
    return ChildrenConfig(
        issue_types=_parse_issue_types(
            raw.get("issue_types") or raw.get("issue_type") or raw.get("type"),
            DEFAULT_CHILD_ISSUE_TYPES,
        )
    )


def _release_config(raw: Any) -> ReleaseConfig:
    if raw is None:
        return ReleaseConfig()
    if isinstance(raw, str):
        return ReleaseConfig(number=raw)
    if not isinstance(raw, dict):
        raise SettingsError("release must be a mapping")
    patterns = _parse_issue_types(
        raw.get("branch_patterns")
        or raw.get("branch_pattern")
        or raw.get("release_branch_pattern"),
        DEFAULT_RELEASE_BRANCH_PATTERNS,
    )
    number = raw.get("number") or raw.get("release_number")
    return ReleaseConfig(
        number=str(number) if number else None,
        number_field=str(raw["number_field"]) if raw.get("number_field") else None,
        number_pattern=str(raw.get("number_pattern") or DEFAULT_NUMBER_PATTERN),
        branch_patterns=patterns,
    )


def _bitbucket_config(raw: Any) -> BitbucketConfig:
    if raw is None:
        raise SettingsError("bitbucket.repository (ссылка на репозиторий) is required")
    if isinstance(raw, str):
        raw = {"repository": raw}
    if not isinstance(raw, dict):
        raise SettingsError("bitbucket must be a mapping")
    repos: list[str] = []
    if raw.get("repository"):
        repos.append(str(raw["repository"]).strip())
    extra = raw.get("repositories") or raw.get("repos") or []
    if isinstance(extra, str):
        extra = [extra]
    for item in extra:
        value = str(item).strip()
        if value and value not in repos:
            repos.append(value)
    if not repos:
        raise SettingsError("bitbucket.repository (ссылка на репозиторий) is required")
    return BitbucketConfig(
        repositories=tuple(repos),
        workspace=(str(raw["workspace"]) if raw.get("workspace") else None),
        repo_slug=(str(raw.get("repo_slug") or raw.get("repository_slug") or "") or None),
        project=(str(raw["project"]) if raw.get("project") else None),
    )


def _pr_config(raw: Any) -> PrConfig:
    if raw is None:
        return PrConfig()
    if not isinstance(raw, dict):
        raise SettingsError("pr must be a mapping")
    return PrConfig(
        include_child_keys=bool(raw.get("include_child_keys", True)),
        merged_states=_parse_issue_types(
            raw.get("merged_states") or raw.get("merged_state"),
            DEFAULT_MERGED_STATES,
        ),
        ignore_states=_parse_issue_types(
            raw.get("ignore_states") or raw.get("ignore_state"),
            DEFAULT_IGNORED_PR_STATES,
        ),
        ignore_destination_prefixes=_parse_issue_types(
            raw.get("ignore_destination_prefixes") or raw.get("ignore_destination_prefix"),
            DEFAULT_IGNORE_DEST_PREFIXES,
        ),
    )


def _parse_issue_types(raw: Any, default: tuple[str, ...]) -> tuple[str, ...]:
    if raw is None:
        return default
    if isinstance(raw, str):
        values = tuple(part.strip() for part in raw.split(",") if part.strip())
        return values or default
    if isinstance(raw, list):
        values = tuple(str(item).strip() for item in raw if str(item).strip())
        return values or default
    return default


def _parse_statuses(raw: Any, default: tuple[str, ...]) -> tuple[str, ...]:
    if raw is None:
        return default
    if isinstance(raw, str):
        return (raw,)
    if isinstance(raw, list):
        values = tuple(str(item) for item in raw if str(item).strip())
        return values or default
    if isinstance(raw, dict):
        if isinstance(raw.get("status"), str):
            return (str(raw["status"]),)
        if raw.get("statuses"):
            return tuple(str(item) for item in raw["statuses"])
        if isinstance(raw.get("target_status"), str):
            return (str(raw["target_status"]),)
        if raw.get("target_statuses"):
            return tuple(str(item) for item in raw["target_statuses"])
    return default


def _issue_filter(raw: Any, name: str) -> IssueFilter:
    if not isinstance(raw, dict):
        raise SettingsError(f"{name} must be a mapping with project, issue_type, label, status")
    project = str(raw.get("project") or raw.get("space") or "").strip()
    issue_type = str(raw.get("issue_type") or raw.get("type") or "").strip()
    if not project:
        raise SettingsError(f"{name}.project (пространство) is required")
    if not issue_type:
        raise SettingsError(f"{name}.issue_type is required")
    return IssueFilter(
        project=project,
        issue_type=issue_type,
        label=_first_label(raw.get("label") or raw.get("labels")),
        status=str(raw["status"]) if raw.get("status") else None,
    )


def _first_label(label: Any) -> str | None:
    if isinstance(label, list):
        label = label[0] if label else None
    return str(label) if label else None


def _issuetype_clause(issue_types: tuple[str, ...]) -> str:
    if len(issue_types) == 1:
        return f'issuetype = "{_escape_jql(issue_types[0])}"'
    inner = ", ".join(f'"{_escape_jql(item)}"' for item in issue_types)
    return f"issuetype in ({inner})"


def _linked_clause(key: str, link_type: str | None) -> str:
    if link_type:
        return f'issue in linkedIssues("{key}", "{_escape_jql(link_type)}")'
    return f'issue in linkedIssues("{key}")'


def _escape_jql(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
