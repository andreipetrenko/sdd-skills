from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class SettingsError(ValueError):
    pass


ORCHESTRATOR_SKILL = "sdd-auto-impr-to-release"

# Catalog / addition order of atomic skills in this repo.
ATOMIC_SKILLS = (
    "sdd-auto-impr-to-story",
    "sdd-auto-story-to-ift",
    "sdd-auto-story-to-uat",
    "sdd-auto-story-to-release",
)

SKILL_SECTIONS = frozenset(ATOMIC_SKILLS) | {ORCHESTRATOR_SKILL}


@dataclass(frozen=True)
class Settings:
    data: dict[str, Any]
    storage_path: Path | None
    path: Path | None = None
    atomic_skills: tuple[str, ...] = ATOMIC_SKILLS

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
    storage = storage_path_from_data(data, settings_path=path)
    return Settings(data=data, storage_path=storage, path=path)


def slice_settings(data: dict[str, Any], skill: str) -> dict[str, Any]:
    """Shared keys plus the named skill section. Other skill sections are dropped."""
    if not isinstance(data, dict):
        return {}
    merged = {key: value for key, value in data.items() if key not in SKILL_SECTIONS}
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
