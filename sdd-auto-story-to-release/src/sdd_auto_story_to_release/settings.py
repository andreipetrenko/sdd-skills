from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class SettingsError(ValueError):
    pass


SKILL_NAME = "sdd-auto-story-to-release"
ORCHESTRATOR_SKILL = "sdd-auto-impr-to-release"


DEFAULT_STORY_ISSUE_TYPES = ("Story",)
DEFAULT_RELEASE_BRANCH_PATTERNS = ("release/{number}",)
DEFAULT_NUMBER_PATTERN = r"(\d+(?:\.\d+)*)"
DEFAULT_STORY_BRANCH_PATTERN = "feature/{key}"
DEFAULT_COMPONENT_DEFAULT_BRANCH = "master"


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
class ReleaseConfig:
    number: str | None = None
    number_field: str | None = None
    number_pattern: str = DEFAULT_NUMBER_PATTERN
    branch_patterns: tuple[str, ...] = DEFAULT_RELEASE_BRANCH_PATTERNS

    def branch_name(self, number: str) -> str:
        return self.branch_patterns[0].format(number=number)


@dataclass(frozen=True)
class ComponentRepo:
    repository: str
    name: str | None = None
    default_branch: str = DEFAULT_COMPONENT_DEFAULT_BRANCH
    story_branch_pattern: str = DEFAULT_STORY_BRANCH_PATTERN

    def story_branch_name(self, key: str) -> str:
        return self.story_branch_pattern.format(key=key)


@dataclass(frozen=True)
class Settings:
    jira_base_url: str | None
    stories: StoriesConfig = field(default_factory=StoriesConfig)
    release: ReleaseConfig = field(default_factory=ReleaseConfig)
    components: tuple[ComponentRepo, ...] = ()
    fallback_component: str | None = None
    max_stories: int = 100
    path: Path | None = None

    def stories_jql(self, release_key: str, release_number: str = "") -> str:
        return self.stories.jql(release_key, release_number)

    def lookup_component(self, name: str) -> ComponentRepo | None:
        wanted = name.casefold()
        for item in self.components:
            if item.name and item.name.casefold() == wanted:
                return item
        return None


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
    items = [raw] if isinstance(raw, (str, dict)) else raw if isinstance(raw, list) else []
    for item in items:
        ident = _catalog_id(item)
        if ident:
            names.add(ident)
    return names


def _catalog_id(raw: Any) -> str | None:
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        if text.startswith(".") or text.startswith("/") or "/" in text or text.endswith(".py"):
            path = Path(text.rstrip("/"))
            name = path.name
            if name == "run.py":
                return path.parent.parent.name
            if name == "scripts":
                return path.parent.name
            return name
        return text
    if isinstance(raw, dict):
        ident = raw.get("id") or raw.get("name") or raw.get("skill")
        if ident:
            return str(ident).strip()
        path = raw.get("path") or raw.get("dir")
        if path:
            return _catalog_id(str(path))
    return None


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
    stories = _stories_config(data.get("stories") or data.get("story"))
    release = _release_config(data.get("release"))
    fallback = _fallback_component(data)
    components = _component_repos(data, fallback)
    if not components:
        raise SettingsError(
            "component.repository или components[].repository "
            "(ссылка на репозиторий компонента) is required"
        )
    unnamed = [item for item in components if not item.name]
    if unnamed and not fallback:
        raise SettingsError(
            "репозиторий компонента задан без имени: укажи components[].name "
            "или related.component / component.name, как в sdd-auto-impr-to-story. "
            "Иначе Jira Component нельзя сопоставить с репой."
        )
    if unnamed and fallback:
        components = tuple(
            ComponentRepo(
                repository=item.repository,
                name=item.name or fallback,
                default_branch=item.default_branch,
                story_branch_pattern=item.story_branch_pattern,
            )
            for item in components
        )
    limits = data.get("limits") or {}
    return Settings(
        jira_base_url=base_url.rstrip("/") if base_url else None,
        stories=stories,
        release=release,
        components=components,
        fallback_component=fallback,
        max_stories=int(limits.get("max_stories") or 100),
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


def _stories_config(raw: Any) -> StoriesConfig:
    if raw is None:
        return StoriesConfig()
    if not isinstance(raw, dict):
        raise SettingsError("stories must be a mapping")
    via = str(raw.get("via") or "both").strip().lower()
    if via not in {"parent", "linked", "both"}:
        raise SettingsError("stories.via must be parent, linked or both")
    return StoriesConfig(
        issue_types=_parse_list(
            raw.get("issue_types") or raw.get("issue_type") or raw.get("type"),
            DEFAULT_STORY_ISSUE_TYPES,
        ),
        project=(str(raw.get("project") or raw.get("space") or "").strip() or None),
        label=_first_label(raw.get("label") or raw.get("labels")),
        status=str(raw["status"]) if raw.get("status") else None,
        via=via,
        link_type=str(raw["link_type"]) if raw.get("link_type") else None,
        jql_pattern=str(raw["jql_pattern"]) if raw.get("jql_pattern") else None,
    )


def _release_config(raw: Any) -> ReleaseConfig:
    if raw is None:
        return ReleaseConfig()
    if isinstance(raw, str):
        return ReleaseConfig(number=raw)
    if not isinstance(raw, dict):
        raise SettingsError("release must be a mapping")
    patterns = _parse_list(
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


def _fallback_component(data: dict[str, Any]) -> str | None:
    related = data.get("related") or {}
    component = data.get("component") or {}
    if isinstance(related, dict) and related.get("component"):
        return str(related["component"])
    if isinstance(component, dict) and (component.get("name") or component.get("component")):
        return str(component.get("name") or component.get("component"))
    return None


def _component_repos(data: dict[str, Any], fallback: str | None) -> tuple[ComponentRepo, ...]:
    items: list[ComponentRepo] = []
    raw_list = data.get("components")
    if isinstance(raw_list, list):
        for entry in raw_list:
            parsed = _one_component(entry, fallback)
            if parsed:
                items.append(parsed)
    single = data.get("component")
    if single:
        parsed = _one_component(single, fallback)
        if parsed and all(item.repository != parsed.repository or item.name != parsed.name for item in items):
            items.append(parsed)
    if not items:
        git = data.get("bitbucket") or data.get("git")
        if isinstance(git, dict) and git.get("repository"):
            parsed = _one_component(git, fallback)
            if parsed:
                items.append(parsed)
        elif isinstance(git, str):
            items.append(
                ComponentRepo(repository=git.strip(), name=fallback)
            )
    return tuple(items)


def _one_component(raw: Any, fallback: str | None) -> ComponentRepo | None:
    if isinstance(raw, str) and raw.strip():
        return ComponentRepo(repository=raw.strip(), name=fallback)
    if not isinstance(raw, dict) or not raw.get("repository"):
        return None
    name = raw.get("name") or raw.get("component") or fallback
    return ComponentRepo(
        repository=str(raw["repository"]).strip(),
        name=str(name) if name else None,
        default_branch=str(
            raw.get("default_branch") or DEFAULT_COMPONENT_DEFAULT_BRANCH
        ),
        story_branch_pattern=str(
            raw.get("story_branch_pattern") or DEFAULT_STORY_BRANCH_PATTERN
        ),
    )


def _parse_list(raw: Any, default: tuple[str, ...]) -> tuple[str, ...]:
    if raw is None:
        return default
    if isinstance(raw, str):
        values = tuple(part.strip() for part in raw.split(",") if part.strip())
        return values or default
    if isinstance(raw, list):
        values = tuple(str(item).strip() for item in raw if str(item).strip())
        return values or default
    return default


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
