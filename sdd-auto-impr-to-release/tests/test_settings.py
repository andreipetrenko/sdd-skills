from __future__ import annotations

from pathlib import Path

import yaml

from sdd_auto_impr_to_release.settings import (
    ATOMIC_SKILLS,
    parse_settings,
    slice_settings,
)


ROOT = Path(__file__).resolve().parents[1]


def test_example_settings_parse():
    data = yaml.safe_load((ROOT / "settings.example.yaml").read_text(encoding="utf-8"))
    settings = parse_settings(data)
    assert settings.atomic_skills == ATOMIC_SKILLS
    assert settings.storage_path is not None
    assert settings.storage_path.name == "storage.yaml"
    assert settings.section("sdd-auto-story-to-ift")["source"]["project"] == "DEV"
    assert settings.section("sdd-auto-impr-to-story")["source"]["project"] == "IMPR"


def test_slice_drops_other_skill_sections():
    data = yaml.safe_load((ROOT / "settings.example.yaml").read_text(encoding="utf-8"))
    sliced = slice_settings(data, "sdd-auto-story-to-ift")
    assert sliced["source"]["project"] == "DEV"
    assert sliced["target"]["statuses"] == ["Ready for IFT"]
    assert sliced["bitbucket"]["repository"].endswith("specs.git")
    assert "sdd-auto-story-to-uat" not in sliced
    assert "sdd-auto-impr-to-story" not in sliced


def test_slice_keeps_standalone_document():
    sliced = slice_settings(
        {"source": {"project": "DEV", "issue_type": "Story"}, "target": {"statuses": ["X"]}},
        "sdd-auto-story-to-ift",
    )
    assert sliced["source"]["project"] == "DEV"
    assert sliced["target"]["statuses"] == ["X"]
