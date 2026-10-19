from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class SettingsError(ValueError):
    pass


DEFAULT_STORY_ISSUE_TYPES = ("Story",)
DEFAULT_STORY_READY_STATUSES = ("Ready for UAT",)
DEFAULT_RELEASE_TARGET_STATUSES = ("Ready for UAT",)


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
    ready_statuses: tuple[str, ...] = DEFAULT_STORY_READY_STATUSES

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
class TargetConfig:
    statuses: tuple[str, ...] = DEFAULT_RELEASE_TARGET_STATUSES


@dataclass(frozen=True)
class Settings:
    jira_base_url: str | None
    source: IssueFilter
    stories: StoriesConfig = field(default_factory=StoriesConfig)
    target: TargetConfig = field(default_factory=TargetConfig)
    max_issues: int = 20
    max_stories: int = 100
    path: Path | None = None

    def stories_jql(self, release_key: str, release_number: str = "") -> str:
        return self.stories.jql(release_key, release_number)


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
    source = _issue_filter(
        data.get("source") or data.get("release_task") or data.get("epic"),
        "source",
    )
    stories = _stories_config(data.get("stories") or data.get("story"))
    target = TargetConfig(
        statuses=_parse_statuses(
            data.get("target")
            or (data.get("release") or {}).get("target")
            or (data.get("release") or {}).get("target_status")
            or (data.get("epic") or {}).get("target_status"),
            DEFAULT_RELEASE_TARGET_STATUSES,
        )
    )
    limits = data.get("limits") or {}
    return Settings(
        jira_base_url=base_url.rstrip("/") if base_url else None,
        source=source,
        stories=stories,
        target=target,
        max_issues=int(limits.get("max_issues") or data.get("max_issues") or 20),
        max_stories=int(limits.get("max_stories") or 100),
        path=path,
    )


def find_settings_file(explicit: str | Path | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    candidates = [
        Path.cwd() / "settings.yaml",
        Path.cwd() / "sdd-auto-release-to-uat" / "settings.yaml",
        Path.cwd() / ".gigacode/skills/sdd-auto-release-to-uat/settings.yaml",
        Path.cwd() / ".gigacode_vsc/skills/sdd-auto-release-to-uat/settings.yaml",
        Path.cwd() / "assets" / "settings.example.yaml",
        Path.cwd() / "sdd-auto-release-to-uat" / "assets" / "settings.example.yaml",
        Path.cwd() / ".gigacode/skills/sdd-auto-release-to-uat/assets/settings.example.yaml",
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
        project=(str(raw.get("project") or raw.get("space") or "").strip() or None),
        label=_first_label(raw.get("label") or raw.get("labels")),
        status=str(raw["status"]) if raw.get("status") else None,
        via=via,
        link_type=str(raw["link_type"]) if raw.get("link_type") else None,
        jql_pattern=str(raw["jql_pattern"]) if raw.get("jql_pattern") else None,
        ready_statuses=_parse_statuses(
            raw.get("ready")
            or raw.get("ready_status")
            or raw.get("ready_statuses"),
            DEFAULT_STORY_READY_STATUSES,
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
        if isinstance(raw.get("ready_status"), str):
            return (str(raw["ready_status"]),)
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
