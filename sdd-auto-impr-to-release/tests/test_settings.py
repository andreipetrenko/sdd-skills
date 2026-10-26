from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sdd_auto_impr_to_release.settings import (
    SettingsError,
    parse_settings,
    parse_skill_catalog,
    slice_settings,
)


ROOT = Path(__file__).resolve().parents[1]

EXAMPLE_IDS = (
    "sdd-auto-impr-to-story",
    "sdd-auto-story-to-ift",
    "sdd-auto-story-to-uat",
    "sdd-auto-story-to-release",
)


def test_example_settings_parse():
    data = yaml.safe_load((ROOT / "settings.example.yaml").read_text(encoding="utf-8"))
    settings = parse_settings(data)
    assert settings.atomic_skills == EXAMPLE_IDS
    assert [item.path for item in settings.skills] == [None, None, None, None]
    assert settings.storage_path is not None
    assert settings.storage_path.name == "storage.yaml"
    assert settings.section("sdd-auto-story-to-ift")["source"]["project"] == "DEV"
    assert settings.section("sdd-auto-impr-to-story")["source"]["project"] == "IMPR"


def test_skills_required():
    with pytest.raises(SettingsError, match="skills"):
        parse_settings({"jira": {"base_url": "https://jira.example.com"}})


def test_skills_from_ids_and_paths():
    refs = parse_skill_catalog(
        [
            "sdd-auto-impr-to-story",
            "../sdd-auto-foo",
            {"id": "bar", "path": "./bar/scripts/run.py"},
        ]
    )
    assert refs[0].id == "sdd-auto-impr-to-story"
    assert refs[0].path is None
    assert refs[1].id == "sdd-auto-foo"
    assert refs[1].path == "../sdd-auto-foo"
    assert refs[2].id == "bar"
    assert refs[2].path == "./bar/scripts/run.py"


def test_empty_skills_catalog():
    settings = parse_settings({"skills": []})
    assert settings.skills == ()


def test_slice_drops_catalog_skill_sections():
    data = yaml.safe_load((ROOT / "settings.example.yaml").read_text(encoding="utf-8"))
    sliced = slice_settings(data, "sdd-auto-story-to-ift")
    assert sliced["source"]["project"] == "DEV"
    assert sliced["target"]["statuses"] == ["Ready for IFT"]
    assert sliced["bitbucket"]["repository"].endswith("specs.git")
    assert "sdd-auto-story-to-uat" not in sliced
    assert "sdd-auto-impr-to-story" not in sliced
    assert "skills" in sliced


def test_slice_drops_fifth_catalog_section():
    sliced = slice_settings(
        {
            "skills": ["sdd-auto-story-to-ift", "sdd-auto-extra"],
            "jira": {"base_url": "https://jira.example.com"},
            "sdd-auto-story-to-ift": {"source": {"project": "DEV"}},
            "sdd-auto-extra": {"source": {"project": "ZZ"}},
        },
        "sdd-auto-story-to-ift",
    )
    assert sliced["source"]["project"] == "DEV"
    assert "sdd-auto-extra" not in sliced


def test_slice_keeps_standalone_document():
    sliced = slice_settings(
        {"source": {"project": "DEV", "issue_type": "Story"}, "target": {"statuses": ["X"]}},
        "sdd-auto-story-to-ift",
    )
    assert sliced["source"]["project"] == "DEV"
    assert sliced["target"]["statuses"] == ["X"]
