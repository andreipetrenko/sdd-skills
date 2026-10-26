from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from sdd_auto_impr_to_release.settings import (
    ORCHESTRATOR_SKILL,
    Settings,
    SettingsError,
    SkillRef,
)
from sdd_auto_impr_to_release.storage import put_section


DEFAULT_SKILL_COMMAND = "plan"


def skill_script(
    skill: str | SkillRef,
    *,
    start: Path,
    settings_path: Path | None = None,
) -> Path:
    """Resolve a skill's scripts/run.py by catalog id or explicit path."""
    ref = skill if isinstance(skill, SkillRef) else SkillRef(id=skill)
    if ref.path:
        found = _script_from_given_path(ref.path, start=start, settings_path=settings_path)
        if found:
            return found
        raise SettingsError(
            f"atomic skill script not found for {ref.id}: {ref.path}"
        )
    return _script_by_id(ref.id, start=start)


def _script_by_id(skill: str, *, start: Path) -> Path:
    bases = [start, start.parent]
    if start.name == skill:
        bases.append(start.parent)
    seen: set[Path] = set()
    for base in bases:
        resolved = base.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        candidate = resolved / skill / "scripts" / "run.py"
        if candidate.is_file():
            return candidate
        sibling = resolved.parent / skill / "scripts" / "run.py"
        if sibling.is_file():
            return sibling
    raise SettingsError(
        f"atomic skill script not found: {skill}/scripts/run.py "
        f"(looked next to {start})"
    )


def _script_from_given_path(
    raw: str,
    *,
    start: Path,
    settings_path: Path | None,
) -> Path | None:
    path = Path(raw).expanduser()
    candidates: list[Path] = []
    if path.is_absolute():
        candidates.append(path)
    else:
        if settings_path:
            candidates.append(Path(settings_path).parent / path)
        candidates.append(start / path)
        candidates.append(start.parent / path)
    for candidate in candidates:
        found = _as_run_script(candidate)
        if found:
            return found
    return None


def _as_run_script(path: Path) -> Path | None:
    try:
        resolved = path.resolve()
    except OSError:
        return None
    if resolved.is_file():
        return resolved
    script = resolved / "scripts" / "run.py"
    if script.is_file():
        return script
    return None


def build_plan(settings: Settings) -> dict[str, Any]:
    return {
        "orchestrator": ORCHESTRATOR_SKILL,
        "loop": {
            "rule": (
                "Run the skills listed in settings.skills, in that order, then repeat. "
                "No stop-condition and no schedule."
            ),
        },
        "settings": str(settings.path) if settings.path else None,
        "storage": str(settings.storage_path) if settings.storage_path else None,
        "skills": [
            {"id": item.id, "path": item.path}
            for item in settings.skills
        ],
        "atomic_skills": list(settings.atomic_skills),
        "skill_command": DEFAULT_SKILL_COMMAND,
        "steps": [
            f"{index}. {item.id}"
            for index, item in enumerate(settings.skills, start=1)
        ],
    }


def run_once(
    settings: Settings,
    *,
    storage_path: Path,
    start: Path,
    skill_command: str = DEFAULT_SKILL_COMMAND,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    settings_arg = str(settings.path) if settings.path else None
    for ref in settings.skills:
        script = skill_script(ref, start=start, settings_path=settings.path)
        argv = [sys.executable, str(script)]
        if settings_arg:
            argv.extend(["--settings", settings_arg])
        argv.extend(["--storage", str(storage_path), skill_command])
        proc = subprocess.run(argv, capture_output=True, text=True, check=False)
        stdout = proc.stdout or ""
        try:
            output: Any = json.loads(stdout) if stdout.strip() else None
        except json.JSONDecodeError:
            output = stdout
        record = {
            "skill": ref.id,
            "path": ref.path,
            "command": skill_command,
            "argv": argv[1:],
            "exit_code": proc.returncode,
            "output": output,
        }
        if proc.returncode != 0 and proc.stderr:
            record["stderr"] = proc.stderr
        put_section(
            storage_path,
            ref.id,
            {
                "command": skill_command,
                "exit_code": proc.returncode,
                "output": output,
            },
        )
        results.append(record)
    summary = {"iteration": results}
    put_section(
        storage_path,
        ORCHESTRATOR_SKILL,
        {"command": "once", "output": {"skills": [item["skill"] for item in results]}},
    )
    return summary


def run_loop(
    settings: Settings,
    *,
    storage_path: Path,
    start: Path,
    skill_command: str = DEFAULT_SKILL_COMMAND,
) -> None:
    while True:
        run_once(
            settings,
            storage_path=storage_path,
            start=start,
            skill_command=skill_command,
        )
