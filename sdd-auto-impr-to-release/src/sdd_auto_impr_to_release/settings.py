from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class SettingsError(ValueError):
    pass


ORCHESTRATOR_SKILL = "sdd-auto-impr-to-release"


@dataclass(frozen=True)
class SkillRef:
    """One attached skill: id (storage/section key) and optional path to the skill dir or run.py."""

    id: str
    path: str | None = None


@dataclass(frozen=True)
class Settings:
    data: dict[str, Any]
    skills: tuple[SkillRef, ...]
    storage_path: Path | None
    path: Path | None = None

    @property
    def atomic_skills(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.skills)

    def section(self, skill: str) -> dict[str, Any]:
        raw = self.data.get(skill)
        return dict(raw) if isinstance(raw, dict) else {}


def load_settings(path: str | Path) -> Settings:
    settings_path = Path(path).expanduser().resolve()
    if not settings_path.is_file():
        raise SettingsError(f"Settings file not found: {settings_path}")
    data = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SettingsError("settings.yaml must be a mapping")
    return parse_settings(data, path=settings_path)


def parse_settings(data: dict[str, Any], path: Path | None = None) -> Settings:
    if "skills" not in data and "skill" not in data:
        raise SettingsError(
            "skills (каталог id или path подключаемых скиллов) is required"
        )
    skills = parse_skill_catalog(data.get("skills") if "skills" in data else data.get("skill"))
    storage = storage_path_from_data(data, settings_path=path)
    return Settings(data=data, skills=skills, storage_path=storage, path=path)


def parse_skill_catalog(raw: Any) -> tuple[SkillRef, ...]:
    if raw is None:
        return ()
    if isinstance(raw, (str, dict)):
        items = [raw]
    elif isinstance(raw, list):
        items = raw
    else:
        raise SettingsError("skills must be a list of skill ids or paths")
    refs: list[SkillRef] = []
    for item in items:
        ref = parse_skill_ref(item)
        if ref:
            refs.append(ref)
    return tuple(refs)


def parse_skill_ref(raw: Any) -> SkillRef | None:
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        if _looks_like_path(text):
            return SkillRef(id=_id_from_path(text), path=text)
        return SkillRef(id=text, path=None)
    if not isinstance(raw, dict):
        raise SettingsError("skills[] item must be an id string, a path, or {id, path}")
    path_raw = raw.get("path") or raw.get("dir")
    ident = raw.get("id") or raw.get("name") or raw.get("skill")
    path = str(path_raw).strip() if path_raw else None
    if ident:
        return SkillRef(id=str(ident).strip(), path=path or None)
    if path:
        return SkillRef(id=_id_from_path(path), path=path)
    raise SettingsError("skills[] needs id or path")


def catalog_section_names(data: dict[str, Any]) -> set[str]:
    names = {ORCHESTRATOR_SKILL}
    raw = data.get("skills") if "skills" in data else data.get("skill")
    try:
        for ref in parse_skill_catalog(raw):
            names.add(ref.id)
    except SettingsError:
        return names
    return names


def slice_settings(data: dict[str, Any], skill: str) -> dict[str, Any]:
    """Shared keys plus the named skill section. Other catalog skill sections are dropped."""
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


def find_settings_file(explicit: str | Path | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    cwd = Path.cwd()
    candidates = [
        cwd / "settings.yaml",
        cwd / ORCHESTRATOR_SKILL / "settings.yaml",
        cwd / ".gigacode/skills" / ORCHESTRATOR_SKILL / "settings.yaml",
        cwd / ".gigacode_vsc/skills" / ORCHESTRATOR_SKILL / "settings.yaml",
        cwd / "assets" / "settings.example.yaml",
        cwd / ORCHESTRATOR_SKILL / "assets" / "settings.example.yaml",
        cwd / ".gigacode/skills" / ORCHESTRATOR_SKILL / "assets/settings.example.yaml",
        cwd / ORCHESTRATOR_SKILL / "settings.example.yaml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SettingsError(
        "settings.yaml not found. Copy settings.example.yaml to settings.yaml "
        "or pass --settings."
    )


def _looks_like_path(text: str) -> bool:
    return text.startswith(".") or text.startswith("/") or "/" in text or text.endswith(".py")


def _id_from_path(text: str) -> str:
    path = Path(text.rstrip("/"))
    name = path.name
    if name == "run.py":
        return path.parent.parent.name
    if name == "scripts":
        return path.parent.name
    return name
