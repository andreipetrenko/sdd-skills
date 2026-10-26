from __future__ import annotations

import json
from pathlib import Path

from sdd_auto_impr_to_release.cli import main


def test_plan(settings_file: Path, capsys):
    assert main(["--settings", str(settings_file), "plan"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["atomic_skills"][0] == "sdd-auto-impr-to-story"
    assert plan["atomic_skills"][-1] == "sdd-auto-story-to-release"


def test_once(settings_file: Path, tmp_path: Path, capsys):
    storage = tmp_path / "storage.yaml"
    assert (
        main(
            [
                "--settings",
                str(settings_file),
                "--storage",
                str(storage),
                "once",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert len(result["iteration"]) == 4
    assert storage.is_file()


def test_missing_settings_returns_2(tmp_path: Path, capsys):
    missing = tmp_path / "nope.yaml"
    assert main(["--settings", str(missing), "plan"]) == 2
    assert "not found" in capsys.readouterr().err.lower()
