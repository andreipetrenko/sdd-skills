from __future__ import annotations

from pathlib import Path

import yaml

from sdd_auto_story_to_release.settings import parse_settings

ROOT = Path(__file__).resolve().parents[1]


def test_gigacode_skill_frontmatter():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, rest = text.split("---\n", 1)
    frontmatter, body = rest.split("---\n", 1)
    meta = yaml.safe_load(frontmatter)
    assert meta["name"] == "sdd-auto-story-to-release"
    assert "Jira" in meta["description"]
    assert "не вызывай REST" in body.lower() or "Не вызывай REST" in body
    assert (ROOT / "references" / "mcp.md").is_file()
    assert (ROOT / "scripts" / "run.py").is_file()


def test_example_settings_parse():
    data = yaml.safe_load((ROOT / "settings.example.yaml").read_text(encoding="utf-8"))
    settings = parse_settings(data)
    assert settings.stories.via == "both"
    assert settings.release.branch_name("1.2") == "release/1.2"
    assert settings.components[0].name == "backend"
    assert settings.fallback_component == "backend"
