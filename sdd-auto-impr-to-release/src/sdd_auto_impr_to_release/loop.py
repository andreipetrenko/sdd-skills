from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from sdd_auto_impr_to_release.settings import ORCHESTRATOR_SKILL, Settings, SettingsError
from sdd_auto_impr_to_release.storage import put_section


DEFAULT_SKILL_COMMAND = "plan"


def skill_script(name: str, *, start: Path) -> Path:
    """Resolve a skill name to <name>/scripts/run.py next to the orchestrator."""
    bases = [start, start.parent]
    if start.name == name:
        bases.append(start.parent)
    seen: set[Path] = set()
    for base in bases:
        resolved = base.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        candidate = resolved / name / "scripts" / "run.py"
        if candidate.is_file():
            return candidate
        sibling = resolved.parent / name / "scripts" / "run.py"
        if sibling.is_file():
            return sibling
    raise SettingsError(
        f"skill not found in repo: {name}/scripts/run.py (looked next to {start})"
    )


def build_plan(settings: Settings) -> dict[str, Any]:
    return {
        "orchestrator": ORCHESTRATOR_SKILL,
        "loop": {
            "rule": (
                "Each name in settings.skills is an atomic skill. "
                "List order is not a pipeline. "
                "No stop-condition and no schedule."
            ),
        },
        "settings": str(settings.path) if settings.path else None,
        "storage": str(settings.storage_path) if settings.storage_path else None,
        "skills": list(settings.skills),
        "atomic_skills": list(settings.atomic_skills),
        "skill_command": DEFAULT_SKILL_COMMAND,
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
    for name in settings.skills:
        script = skill_script(name, start=start)
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
            "skill": name,
            "command": skill_command,
            "argv": argv[1:],
            "exit_code": proc.returncode,
            "output": output,
        }
        if proc.returncode != 0 and proc.stderr:
            record["stderr"] = proc.stderr
        put_section(
            storage_path,
            name,
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
