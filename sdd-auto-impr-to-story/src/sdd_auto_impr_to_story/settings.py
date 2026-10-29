from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class SettingsError(ValueError):
    pass


SKILL_NAME = "sdd-auto-impr-to-story"
ORCHESTRATOR_SKILL = "sdd-auto-impr-to-release"


@dataclass(frozen=True)
class IssueFilter:
    """Jira search or create parameters: space (project), type, label, status."""

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
class StoryConfig(IssueFilter):
    link_type: str = "Relates"
    summary_pattern: str = "{source_key}: {source_summary}"
    done_statuses: tuple[str, ...] = ("Сделан", "Done")


@dataclass(frozen=True)
class RelatedConfig:
    issue_type: str
    link_type: str
    component: str | None = None
    component_from_source: bool = True
    project: str | None = None
    label: str | None = None
    status: str | None = None
    summary_pattern: str = "[{component}] {story_key}: {story_summary}"
    in_progress_statuses: tuple[str, ...] = ("В работе", "In Progress")
    done_statuses: tuple[str, ...] = ("Сделан", "Done")


@dataclass(frozen=True)
class BitbucketConfig:
    repository: str
    workspace: str | None = None
    repo_slug: str | None = None
    project: str | None = None
    default_branch: str = "main"
    source_branch_pattern: str = "feature/{key}"
    story_branch_pattern: str = "feature/{key}"
    task_branch_pattern: str = "feature/{key}"


@dataclass(frozen=True)
class OpenspecConfig:
    capabilities: tuple[str, ...] = ("business-requirements", "functional-requirements")
    change_id_pattern: str = "{source_key}"
    implementation_capability: str = "code-changes"
    implementation_change_id_pattern: str = "{task_key}"


@dataclass(frozen=True)
class AfterMergeConfig:
    statuses: tuple[str, ...] = ("В работе", "In Progress")


@dataclass(frozen=True)
class Settings:
    jira_base_url: str | None
    source: IssueFilter
    story: StoryConfig
    bitbucket: BitbucketConfig
    related: RelatedConfig
    component: BitbucketConfig
    after_merge: AfterMergeConfig = field(default_factory=AfterMergeConfig)
    improvement_done: AfterMergeConfig = field(
        default_factory=lambda: AfterMergeConfig(statuses=("Сделан", "Done"))
    )
    openspec: OpenspecConfig = field(default_factory=OpenspecConfig)
    max_issues: int = 20
    path: Path | None = None

    @property
    def source_idempotency_label(self) -> str:
        return "sdd-from-{key}"

    def story_label_for(self, source_key: str) -> str:
        return f"sdd-from-{source_key}"

    def related_label_for(self, story_key: str) -> str:
        base = self.related.label or "sdd-impl"
        return f"{base}-{story_key}"

    def source_branch_name(self, key: str) -> str:
        return self.bitbucket.source_branch_pattern.format(key=key)

    def story_branch_name(self, key: str) -> str:
        return self.bitbucket.story_branch_pattern.format(key=key)

    def specs_task_branch_name(self, key: str) -> str:
        return self.bitbucket.task_branch_pattern.format(key=key)

    def component_task_branch_name(self, key: str) -> str:
        return self.component.task_branch_pattern.format(key=key)

    def component_story_branch_name(self, key: str) -> str:
        return self.component.story_branch_pattern.format(key=key)

    def change_id(self, source_key: str) -> str:
        raw = self.openspec.change_id_pattern.format(source_key=source_key)
        return _kebab(raw)

    def implementation_change_id(self, task_key: str, source_key: str = "") -> str:
        raw = self.openspec.implementation_change_id_pattern.format(
            task_key=task_key,
            source_key=source_key,
        )
        return _kebab(raw)


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
    story_raw = data.get("story")
    story_filter = _issue_filter(story_raw, "story")
    story_data = story_raw if isinstance(story_raw, dict) else {}
    story_done = _parse_statuses(
        story_data.get("done") or story_data.get("done_status") or story_data.get("done_statuses"),
        ("Сделан", "Done"),
    )
    story = StoryConfig(
        project=story_filter.project,
        issue_type=story_filter.issue_type,
        label=story_filter.label,
        status=story_filter.status,
        link_type=str(story_data.get("link_type") or "Relates"),
        summary_pattern=str(story_data.get("summary_pattern") or "{source_key}: {source_summary}"),
        done_statuses=story_done,
    )

    git_raw = data.get("bitbucket") or data.get("git") or data.get("repository")
    bitbucket = _bitbucket_config(git_raw, "bitbucket", default_branch="main")

    related_raw = data.get("related") or {}
    if not isinstance(related_raw, dict) or not related_raw.get("issue_type"):
        raise SettingsError("related.issue_type is required")
    if not related_raw.get("link_type"):
        raise SettingsError("related.link_type is required")
    related = RelatedConfig(
        issue_type=str(related_raw["issue_type"]),
        link_type=str(related_raw["link_type"]),
        component=(str(related_raw["component"]) if related_raw.get("component") else None),
        component_from_source=bool(related_raw.get("component_from_source", True)),
        project=(str(related_raw["project"]) if related_raw.get("project") else None),
        label=(str(related_raw["label"]) if related_raw.get("label") else None),
        status=(str(related_raw["status"]) if related_raw.get("status") else None),
        summary_pattern=str(
            related_raw.get("summary_pattern")
            or "[{component}] {story_key}: {story_summary}"
        ),
        in_progress_statuses=_parse_statuses(
            related_raw.get("in_progress")
            or related_raw.get("in_progress_status")
            or related_raw.get("in_progress_statuses"),
            ("В работе", "In Progress"),
        ),
        done_statuses=_parse_statuses(
            related_raw.get("done")
            or related_raw.get("done_status")
            or related_raw.get("done_statuses"),
            ("Сделан", "Done"),
        ),
    )

    component = _bitbucket_config(
        data.get("component") or data.get("component_repo"),
        "component",
        default_branch="master",
        default_task_pattern="task/{key}",
    )

    after_raw = data.get("after_merge")
    if after_raw is None:
        after_raw = data.get("done")
    statuses = _parse_statuses(after_raw, ("В работе", "In Progress"))
    improvement_done = _parse_statuses(
        data.get("improvement_done")
        or (data.get("source") or {}).get("done")
        or (data.get("source") or {}).get("done_status")
        or (data.get("source") or {}).get("done_statuses"),
        ("Сделан", "Done"),
    )

    openspec_raw = data.get("openspec") or {}
    capabilities = tuple(
        str(item)
        for item in (
            openspec_raw.get("capabilities")
            or ["business-requirements", "functional-requirements"]
        )
    )
    openspec = OpenspecConfig(
        capabilities=capabilities or ("business-requirements", "functional-requirements"),
        change_id_pattern=str(openspec_raw.get("change_id_pattern") or "{source_key}"),
        implementation_capability=str(
            openspec_raw.get("implementation_capability") or "code-changes"
        ),
        implementation_change_id_pattern=str(
            openspec_raw.get("implementation_change_id_pattern") or "{task_key}"
        ),
    )

    max_issues = int((data.get("limits") or {}).get("max_issues") or data.get("max_issues") or 20)
    return Settings(
        jira_base_url=base_url.rstrip("/") if base_url else None,
        source=source,
        story=story,
        bitbucket=bitbucket,
        related=related,
        component=component,
        after_merge=AfterMergeConfig(statuses=statuses),
        improvement_done=AfterMergeConfig(statuses=improvement_done),
        openspec=openspec,
        max_issues=max_issues,
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


def _bitbucket_config(
    raw: Any,
    name: str,
    *,
    default_branch: str,
    default_task_pattern: str = "feature/{key}",
) -> BitbucketConfig:
    if isinstance(raw, str):
        raw = {"repository": raw}
    if not isinstance(raw, dict) or not raw.get("repository"):
        raise SettingsError(f"{name}.repository (ссылка на репозиторий) is required")
    source_pattern = str(raw.get("source_branch_pattern") or "feature/{key}")
    return BitbucketConfig(
        repository=str(raw["repository"]).strip(),
        workspace=(str(raw["workspace"]) if raw.get("workspace") else None),
        repo_slug=(str(raw.get("repo_slug") or raw.get("repository_slug") or "") or None),
        project=(str(raw["project"]) if raw.get("project") else None),
        default_branch=str(raw.get("default_branch") or default_branch),
        source_branch_pattern=source_pattern,
        story_branch_pattern=str(raw.get("story_branch_pattern") or "feature/{key}"),
        task_branch_pattern=str(raw.get("task_branch_pattern") or default_task_pattern),
    )


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


def _escape_jql(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _kebab(value: str) -> str:
    cleaned = []
    prev_dash = False
    for char in value.strip().lower():
        if char.isalnum():
            cleaned.append(char)
            prev_dash = False
        elif not prev_dash:
            cleaned.append("-")
            prev_dash = True
    return "".join(cleaned).strip("-") or "change"
