from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class SettingsError(ValueError):
    pass


SKILL_NAME = "sdd-auto-story-to-ift"
ORCHESTRATOR_SKILL = "sdd-auto-impr-to-release"


DEFAULT_CHILD_ISSUE_TYPES = ("Task", "Sub-task", "Subtask")
DEFAULT_CHILD_READY_STATUSES = ("Готов",)
DEFAULT_STORY_TARGET_STATUSES = ("Ready for IFT",)


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
class ChildrenConfig:
    issue_types: tuple[str, ...] = DEFAULT_CHILD_ISSUE_TYPES
    ready_statuses: tuple[str, ...] = DEFAULT_CHILD_READY_STATUSES

    def jql(self, parent_key: str) -> str:
        type_clause = _issuetype_clause(self.issue_types)
        return (
            f'parent = "{_escape_jql(parent_key)}" AND {type_clause} ORDER BY created ASC'
        )


@dataclass(frozen=True)
class TargetConfig:
    statuses: tuple[str, ...] = DEFAULT_STORY_TARGET_STATUSES


@dataclass(frozen=True)
class Settings:
    jira_base_url: str | None
    source: IssueFilter
    children: ChildrenConfig = field(default_factory=ChildrenConfig)
    target: TargetConfig = field(default_factory=TargetConfig)
    max_issues: int = 20
    max_children: int = 100
    path: Path | None = None

    def children_jql(self, parent_key: str) -> str:
        return self.children.jql(parent_key)


def load_settings(path: str | Path) -> Settings:
    settings_path = Path(path).expanduser().resolve()
    if not settings_path.is_file():
        raise SettingsError(f"Settings file not found: {settings_path}")
    data = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SettingsError("settings.yaml must be a mapping")
    return parse_settings(data, path=settings_path)


def catalog_section_names(data: dict[str, Any]) -> set[str]:
    names = {ORCHESTRATOR_SKILL, SKILL_NAME}
    if not isinstance(data, dict):
        return names
    raw = data.get("skills") if "skills" in data else data.get("skill")
    if raw is None:
        return names
    items = [raw] if isinstance(raw, str) else raw if isinstance(raw, list) else []
    for item in items:
        ident = _catalog_id(item)
        if ident:
            names.add(ident)
    return names


def _catalog_id(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text or text.startswith(".") or text.startswith("/") or "/" in text or text.endswith(".py"):
        return None
    return text


def slice_settings(data: dict[str, Any], skill: str = SKILL_NAME) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    drop = catalog_section_names(data) | {skill}
    merged = {key: value for key, value in data.items() if key not in drop}
    section = data.get(skill)
    if isinstance(section, dict):
        merged.update(section)
    return merged


def storage_path_from_data(
    data: dict[str, Any],
    *,
    settings_path: Path | None = None,
) -> Path | None:
    raw = data.get("storage")
    value: Any = None
    if isinstance(raw, str):
        value = raw
    elif isinstance(raw, dict):
        value = raw.get("path")
    if not value:
        return None
    path = Path(str(value)).expanduser()
    if not path.is_absolute() and settings_path is not None:
        path = settings_path.parent / path
    return path.resolve()


def parse_settings(data: dict[str, Any], path: Path | None = None) -> Settings:
    data = slice_settings(data)
    jira = data.get("jira") or {}
    base_url = str(jira.get("base_url") or "").strip() or None

    source = _issue_filter(data.get("source"), "source")
    children = _children_config(data.get("children"))
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
    max_issues = int(limits.get("max_issues") or data.get("max_issues") or 20)
    max_children = int(limits.get("max_children") or data.get("max_children") or 100)
    return Settings(
        jira_base_url=base_url.rstrip("/") if base_url else None,
        source=source,
        children=children,
        target=target,
        max_issues=max_issues,
        max_children=max_children,
        path=path,
    )


def find_settings_file(explicit: str | Path | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    cwd = Path.cwd()
    candidates = [
        cwd / "settings.yaml",
        cwd / ORCHESTRATOR_SKILL / "settings.yaml",
        cwd / ".gigacode/skills" / ORCHESTRATOR_SKILL / "settings.yaml",
        cwd / ".gigacode_vsc/skills" / ORCHESTRATOR_SKILL / "settings.yaml",
        cwd / SKILL_NAME / "settings.yaml",
        cwd / ".gigacode/skills" / SKILL_NAME / "settings.yaml",
        cwd / ".gigacode_vsc/skills" / SKILL_NAME / "settings.yaml",
        cwd / "assets" / "settings.example.yaml",
        cwd / ORCHESTRATOR_SKILL / "settings.example.yaml",
        cwd / ORCHESTRATOR_SKILL / "assets" / "settings.example.yaml",
        cwd / SKILL_NAME / "settings.example.yaml",
        cwd / SKILL_NAME / "assets" / "settings.example.yaml",
        cwd / ".gigacode/skills" / ORCHESTRATOR_SKILL / "assets/settings.example.yaml",
        cwd / ".gigacode/skills" / SKILL_NAME / "assets/settings.example.yaml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SettingsError(
        "settings.yaml not found. Copy the shared settings.example.yaml "
        f"from {ORCHESTRATOR_SKILL} to settings.yaml or pass --settings."
    )


def _children_config(raw: Any) -> ChildrenConfig:
    if raw is None:
        return ChildrenConfig()
    if not isinstance(raw, dict):
        raise SettingsError("children must be a mapping")
    issue_types = _parse_issue_types(
        raw.get("issue_types")
        or raw.get("issue_type")
        or raw.get("types")
        or raw.get("type"),
        DEFAULT_CHILD_ISSUE_TYPES,
    )
    ready = _parse_statuses(
        raw.get("ready")
        or raw.get("ready_status")
        or raw.get("ready_statuses")
        or raw.get("status"),
        DEFAULT_CHILD_READY_STATUSES,
    )
    return ChildrenConfig(issue_types=issue_types, ready_statuses=ready)


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
    label = raw.get("label") or raw.get("labels")
    if isinstance(label, list):
        label = label[0] if label else None
    status = raw.get("status")
    return IssueFilter(
        project=project,
        issue_type=issue_type,
        label=str(label) if label else None,
        status=str(status) if status else None,
    )


def _issuetype_clause(issue_types: tuple[str, ...]) -> str:
    if len(issue_types) == 1:
        return f'issuetype = "{_escape_jql(issue_types[0])}"'
    inner = ", ".join(f'"{_escape_jql(item)}"' for item in issue_types)
    return f"issuetype in ({inner})"


def _escape_jql(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
