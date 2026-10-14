from __future__ import annotations

from pathlib import Path

import yaml

from sdd_auto_impr_to_story.settings import parse_settings

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT


def test_gigacode_skill_frontmatter():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, rest = text.split("---\n", 1)
    frontmatter, body = rest.split("---\n", 1)
    meta = yaml.safe_load(frontmatter)
    assert meta["name"] == "sdd-auto-impr-to-story"
    assert "Jira" in meta["description"]
    assert "Bitbucket" in meta["description"]
    assert "MCP" in body
    assert "не вызывай REST" in body.lower() or "Не вызывай REST" in body
    assert (SKILL_DIR / "references" / "mcp.md").is_file()
    assert (SKILL_DIR / "scripts" / "run.py").is_file()


def test_example_settings_parse():
    data = yaml.safe_load((ROOT / "settings.example.yaml").read_text(encoding="utf-8"))
    settings = parse_settings(data)
    assert settings.source.project == "IMPR"
    assert settings.bitbucket.repository.endswith("specs.git")
    assert "В работе" in settings.after_merge.statuses
    assert "In Progress" in settings.after_merge.statuses
    assert settings.component.repository.endswith("payments.git")
    assert "Сделан" in settings.related.done_statuses
    assert "Сделан" in settings.story.done_statuses
    assert "Сделан" in settings.improvement_done.statuses
