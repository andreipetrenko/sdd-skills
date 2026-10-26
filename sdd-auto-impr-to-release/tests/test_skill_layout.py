from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_gigacode_skill_frontmatter():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, rest = text.split("---\n", 1)
    frontmatter, body = rest.split("---\n", 1)
    meta = yaml.safe_load(frontmatter)
    assert meta["name"] == "sdd-auto-impr-to-release"
    assert "оркестратор" in meta["description"].lower() or "Оркестратор" in meta["description"]
    assert "sdd-auto-impr-to-story" in meta["description"]
    assert "не вызывай REST" in body.lower() or "Не вызывай REST" in body
    assert (ROOT / "references" / "mcp.md").is_file()
    assert (ROOT / "references" / "settings.md").is_file()
    assert (ROOT / "references" / "storage.md").is_file()
    assert (ROOT / "scripts" / "run.py").is_file()
    assert (ROOT / "storage.example.yaml").is_file()
