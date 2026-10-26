from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from sdd_auto_impr_to_release.settings import ATOMIC_SKILLS, Settings, SettingsError
from sdd_auto_impr_to_release.storage import put_section


DEFAULT_SKILL_COMMAND = "plan"


def skill_script(skill: str, *, start: Path) -> Path:
    """Resolve sibling skill script from catalog root or .gigacode/skills/."""
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


def build_plan(settings: Settings) -> dict[str, Any]:
    return {
        "orchestrator": "sdd-auto-impr-to-release",
        "loop": {
            "rule": (
                "Run the atomic skills in order, then repeat. "
                "No stop-condition and no schedule."
            ),
        },
        "settings": str(settings.path) if settings.path else None,
        "storage": str(settings.storage_path) if settings.storage_path else None,
        "atomic_skills": list(settings.atomic_skills),
        "skill_command": DEFAULT_SKILL_COMMAND,
        "steps": [
            f"{index}. {name}"
            for index, name in enumerate(settings.atomic_skills, start=1)
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
    for skill in settings.atomic_skills:
        script = skill_script(skill, start=start)
        argv = [sys.executable, str(script)]
        if settings_arg:
            argv.extend(["--settings", settings_arg])
        argv.extend(["--storage", str(storage_path), skill_command])
        proc = subprocess.run(argv, capture_output=True, text=True, check=False)
        output: Any
        stdout = proc.stdout or ""
        try:
            output = json.loads(stdout) if stdout.strip() else None
        except json.JSONDecodeError:
            output = stdout
        record = {
            "skill": skill,
            "command": skill_command,
            "argv": argv[1:],
            "exit_code": proc.returncode,
            "output": output,
        }
        if proc.returncode != 0 and proc.stderr:
            record["stderr"] = proc.stderr
        put_section(
            storage_path,
            skill,
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
        "sdd-auto-impr-to-release",
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
