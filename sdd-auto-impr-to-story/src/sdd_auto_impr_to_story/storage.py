from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sdd_auto_impr_to_story.settings import (
    ORCHESTRATOR_SKILL,
    SKILL_NAME,
    SettingsError,
    storage_path_from_data,
)


def load_storage(path: str | Path, *, create: bool = False) -> dict[str, Any]:
    storage_path = Path(path).expanduser().resolve()
    if not storage_path.is_file():
        if not create:
            raise SettingsError(f"Storage file not found: {storage_path}")
        data: dict[str, Any] = {}
        save_storage(storage_path, data)
        return data
    data = yaml.safe_load(storage_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SettingsError("storage.yaml must be a mapping")
    return data


def save_storage(path: str | Path, data: dict[str, Any]) -> Path:
    storage_path = Path(path).expanduser().resolve()
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return storage_path


def get_section(data: dict[str, Any], skill: str = SKILL_NAME) -> dict[str, Any]:
    raw = data.get(skill)
    return dict(raw) if isinstance(raw, dict) else {}


def put_section(
    path: str | Path,
    payload: dict[str, Any],
    *,
    skill: str = SKILL_NAME,
    create: bool = True,
) -> dict[str, Any]:
    data = load_storage(path, create=create)
    section = get_section(data, skill)
    section.update(payload)
    data[skill] = section
    save_storage(path, data)
    return section


def record_output(
    path: str | Path | None,
    command: str,
    output: Any,
    extra: dict[str, Any] | None = None,
) -> None:
    if path is None:
        return
    payload: dict[str, Any] = {"command": command, "output": output}
    if extra:
        payload.update(extra)
    if isinstance(output, dict) and output.get("release_key"):
        payload.setdefault("release_key", output["release_key"])
    put_section(path, payload)


def find_storage_file(
    explicit: str | Path | None = None,
    *,
    settings_path: str | Path | None = None,
    create: bool = False,
) -> Path | None:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if create and not path.is_file():
            save_storage(path, {})
        return path
    if settings_path:
        settings = Path(settings_path).expanduser().resolve()
        if settings.is_file():
            data = yaml.safe_load(settings.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                from_settings = storage_path_from_data(data, settings_path=settings)
                if from_settings is not None:
                    if create and not from_settings.is_file():
                        save_storage(from_settings, {})
                    return from_settings
    cwd = Path.cwd()
    for candidate in (
        cwd / "storage.yaml",
        cwd / ORCHESTRATOR_SKILL / "storage.yaml",
        cwd / ".gigacode/skills" / ORCHESTRATOR_SKILL / "storage.yaml",
        cwd / ".gigacode_vsc/skills" / ORCHESTRATOR_SKILL / "storage.yaml",
    ):
        if candidate.is_file():
            return candidate.resolve()
    return None
