from __future__ import annotations

from pathlib import Path

import yaml

from sdd_auto_impr_to_release.loop import build_plan, run_once, skill_script
from sdd_auto_impr_to_release.settings import SkillRef, parse_settings
from sdd_auto_impr_to_release.storage import load_storage


ROOT = Path(__file__).resolve().parents[1]

EXAMPLE_IDS = (
    "sdd-auto-impr-to-story",
    "sdd-auto-story-to-ift",
    "sdd-auto-story-to-uat",
    "sdd-auto-story-to-release",
)


def test_example_skill_scripts_exist():
    for name in EXAMPLE_IDS:
        script = skill_script(name, start=ROOT)
        assert script.is_file()
        assert script.parent.parent.name == name


def test_plan_lists_catalog_skills(settings):
    plan = build_plan(settings)
    assert plan["atomic_skills"] == list(EXAMPLE_IDS)
    assert plan["skills"][0]["id"] == "sdd-auto-impr-to-story"
    assert "settings.skills" in plan["loop"]["rule"]


def test_once_runs_catalog_plan(settings_file: Path, tmp_path: Path):
    data = yaml.safe_load(settings_file.read_text(encoding="utf-8"))
    settings = parse_settings(data, path=settings_file)
    storage = tmp_path / "storage.yaml"
    result = run_once(settings, storage_path=storage, start=ROOT)
    assert [item["skill"] for item in result["iteration"]] == list(EXAMPLE_IDS)
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


def test_once_runs_skill_by_path(tmp_path: Path):
    plugin = tmp_path / "sdd-auto-extra"
    script = plugin / "scripts" / "run.py"
    script.parent.mkdir(parents=True)
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "print(json.dumps({'plugin': True, 'skill': 'sdd-auto-extra'}))\n",
        encoding="utf-8",
    )
    settings_path = tmp_path / "settings.yaml"
    data = {
        "skills": [{"id": "sdd-auto-extra", "path": str(plugin)}],
        "storage": {"path": "storage.yaml"},
    }
    settings_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    settings = parse_settings(data, path=settings_path)
    storage = tmp_path / "storage.yaml"
    result = run_once(settings, storage_path=storage, start=ROOT)
    assert result["iteration"][0]["skill"] == "sdd-auto-extra"
    assert result["iteration"][0]["exit_code"] == 0
    assert result["iteration"][0]["output"]["plugin"] is True
    assert load_storage(storage)["sdd-auto-extra"]["output"]["plugin"] is True


def test_skill_script_from_path_ref(tmp_path: Path):
    plugin = tmp_path / "sdd-auto-extra"
    script = plugin / "scripts" / "run.py"
    script.parent.mkdir(parents=True)
    script.write_text("print(1)\n", encoding="utf-8")
    found = skill_script(
        SkillRef(id="sdd-auto-extra", path=str(plugin)),
        start=ROOT,
        settings_path=tmp_path / "settings.yaml",
    )
    assert found == script.resolve()
