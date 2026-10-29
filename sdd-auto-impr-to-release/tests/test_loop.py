from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sdd_auto_impr_to_release.loop import build_plan, run_once, skill_script
from sdd_auto_impr_to_release.settings import SettingsError, parse_settings
from sdd_auto_impr_to_release.storage import load_storage


ROOT = Path(__file__).resolve().parents[1]

EXAMPLE_IDS = (
    "sdd-auto-impr-to-story",
    "sdd-auto-story-to-ift",
    "sdd-auto-story-to-uat",
    "sdd-auto-story-to-release",
)


def test_name_resolves_to_repo_skill():
    for name in EXAMPLE_IDS:
        script = skill_script(name, start=ROOT)
        assert script.is_file()
        assert script.parent.parent.name == name
        assert script.parent.parent.parent == ROOT.parent


def test_unknown_name_is_not_found():
    with pytest.raises(SettingsError, match="not found"):
        skill_script("sdd-auto-does-not-exist", start=ROOT)


def test_plan_lists_skill_names(settings):
    plan = build_plan(settings)
    assert plan["skills"] == list(EXAMPLE_IDS)
    assert "not a pipeline" in plan["loop"]["rule"]
    assert "steps" not in plan


def test_once_runs_attached_skills(settings_file: Path, tmp_path: Path):
    data = yaml.safe_load(settings_file.read_text(encoding="utf-8"))
    settings = parse_settings(data, path=settings_file)
    storage = tmp_path / "storage.yaml"
    result = run_once(settings, storage_path=storage, start=ROOT)
    assert {item["skill"] for item in result["iteration"]} == set(EXAMPLE_IDS)
    assert all(item["exit_code"] == 0 for item in result["iteration"])
    stored = load_storage(storage)
    assert stored["sdd-auto-impr-to-story"]["command"] == "plan"
    assert stored["sdd-auto-story-to-ift"]["output"]["target_statuses"] == ["Ready for IFT"]


def test_once_subset_from_settings(tmp_path: Path):
    data = yaml.safe_load((ROOT / "settings.example.yaml").read_text(encoding="utf-8"))
    data["skills"] = ["sdd-auto-story-to-ift"]
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    settings = parse_settings(data, path=settings_path)
    storage = tmp_path / "storage.yaml"
    result = run_once(settings, storage_path=storage, start=ROOT)
    assert [item["skill"] for item in result["iteration"]] == ["sdd-auto-story-to-ift"]
    assert result["iteration"][0]["exit_code"] == 0
