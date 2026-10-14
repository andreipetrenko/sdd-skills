from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class SettingsError(ValueError):
    pass


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


@dataclass(frozen=True)
class BitbucketConfig:
    repository: str
    workspace: str | None = None
    repo_slug: str | None = None
    project: str | None = None
    default_branch: str = "main"
    source_branch_pattern: str = "feature/{key}"
    story_branch_pattern: str = "feature/{key}"


@dataclass(frozen=True)
class OpenspecConfig:
    capabilities: tuple[str, ...] = ("business-requirements", "functional-requirements")
    change_id_pattern: str = "{source_key}"


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
    after_merge: AfterMergeConfig = field(default_factory=AfterMergeConfig)
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

    def change_id(self, source_key: str) -> str:
        raw = self.openspec.change_id_pattern.format(source_key=source_key)
        return _kebab(raw)


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

    source = _issue_filter(data.get("source"), "source")
    story_raw = data.get("story")
    story_filter = _issue_filter(story_raw, "story")
    story_data = story_raw if isinstance(story_raw, dict) else {}
    story = StoryConfig(
        project=story_filter.project,
        issue_type=story_filter.issue_type,
        label=story_filter.label,
        status=story_filter.status,
        link_type=str(story_data.get("link_type") or "Relates"),
        summary_pattern=str(story_data.get("summary_pattern") or "{source_key}: {source_summary}"),
    )

    git_raw = data.get("bitbucket") or data.get("git") or data.get("repository")
    if isinstance(git_raw, str):
        git_raw = {"repository": git_raw}
    if not isinstance(git_raw, dict) or not git_raw.get("repository"):
        raise SettingsError("bitbucket.repository (ссылка на репозиторий) is required")
    bitbucket = BitbucketConfig(
        repository=str(git_raw["repository"]).strip(),
        workspace=(str(git_raw["workspace"]) if git_raw.get("workspace") else None),
        repo_slug=(str(git_raw.get("repo_slug") or git_raw.get("repository_slug") or "") or None),
        project=(str(git_raw["project"]) if git_raw.get("project") else None),
        default_branch=str(git_raw.get("default_branch") or "main"),
        source_branch_pattern=str(git_raw.get("source_branch_pattern") or "feature/{key}"),
        story_branch_pattern=str(git_raw.get("story_branch_pattern") or "feature/{key}"),
    )

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
    )

    after_raw = data.get("after_merge") if data.get("after_merge") is not None else data.get("done")
    after_raw = after_raw or {}
    statuses: tuple[str, ...]
    if isinstance(after_raw, str):
        statuses = (after_raw,)
    elif isinstance(after_raw, dict) and isinstance(after_raw.get("status"), str):
        statuses = (str(after_raw["status"]),)
    elif isinstance(after_raw, dict) and after_raw.get("statuses"):
        statuses = tuple(str(item) for item in after_raw["statuses"])
    else:
        statuses = ("В работе", "In Progress")

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
    )

    max_issues = int((data.get("limits") or {}).get("max_issues") or data.get("max_issues") or 20)
    return Settings(
        jira_base_url=base_url.rstrip("/") if base_url else None,
        source=source,
        story=story,
        bitbucket=bitbucket,
        related=related,
        after_merge=AfterMergeConfig(statuses=statuses),
        openspec=openspec,
        max_issues=max_issues,
        path=path,
    )


def find_settings_file(explicit: str | Path | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    candidates = [
        Path.cwd() / "settings.yaml",
        Path.cwd() / "sdd-auto-impr-to-story" / "settings.yaml",
        Path.cwd() / ".gigacode/skills/sdd-auto-impr-to-story/settings.yaml",
        Path.cwd() / ".gigacode_vsc/skills/sdd-auto-impr-to-story/settings.yaml",
        Path.cwd() / "assets" / "settings.example.yaml",
        Path.cwd() / "sdd-auto-impr-to-story" / "assets" / "settings.example.yaml",
        Path.cwd() / ".gigacode/skills/sdd-auto-impr-to-story/assets/settings.example.yaml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SettingsError(
        "settings.yaml not found. Copy settings.example.yaml to settings.yaml "
        "or pass --settings."
    )


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
