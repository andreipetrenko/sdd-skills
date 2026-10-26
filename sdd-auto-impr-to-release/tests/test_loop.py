from __future__ import annotations

from pathlib import Path

import yaml

from sdd_auto_impr_to_release.loop import build_plan, run_once, skill_script
from sdd_auto_impr_to_release.settings import ATOMIC_SKILLS, parse_settings
from sdd_auto_impr_to_release.storage import load_storage


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def test_catalog_order():
    assert ATOMIC_SKILLS == (
        "sdd-auto-impr-to-story",
        "sdd-auto-story-to-ift",
        "sdd-auto-story-to-uat",
        "sdd-auto-story-to-release",
    )


def test_skill_scripts_exist():
    for name in ATOMIC_SKILLS:
        script = skill_script(name, start=ROOT)
        assert script.is_file()
        assert script.parent.parent.name == name


def test_plan_lists_atomic_skills(settings):
    plan = build_plan(settings)
    assert plan["atomic_skills"] == list(ATOMIC_SKILLS)
    assert "No stop-condition" in plan["loop"]["rule"]


def test_once_runs_atomic_plan(settings_file: Path, tmp_path: Path):
    data = yaml.safe_load(settings_file.read_text(encoding="utf-8"))
    settings = parse_settings(data, path=settings_file)
    storage = tmp_path / "storage.yaml"
    result = run_once(settings, storage_path=storage, start=ROOT)
    assert [item["skill"] for item in result["iteration"]] == list(ATOMIC_SKILLS)
    assert all(item["exit_code"] == 0 for item in result["iteration"])
    assert all(item["command"] == "plan" for item in result["iteration"])
    stored = load_storage(storage)
    assert stored["sdd-auto-impr-to-story"]["command"] == "plan"
    assert stored["sdd-auto-story-to-ift"]["output"]["target_statuses"] == ["Ready for IFT"]
    assert stored["sdd-auto-story-to-uat"]["output"]["target_statuses"] == ["Ready for UAT"]
    assert stored["sdd-auto-story-to-release"]["output"]["input"].startswith("release Story")
