from __future__ import annotations

from pathlib import Path

from sdd_auto_impr_to_release.storage import get_section, load_storage, put_section


def test_put_and_get_section(tmp_path: Path):
    path = tmp_path / "storage.yaml"
    put_section(path, "sdd-auto-story-to-release", {"release_key": "REL-12", "command": "plan"})
    data = load_storage(path)
    assert get_section(data, "sdd-auto-story-to-release")["release_key"] == "REL-12"
    put_section(path, "sdd-auto-story-to-release", {"output": {"ok": True}})
    data = load_storage(path)
    section = get_section(data, "sdd-auto-story-to-release")
    assert section["release_key"] == "REL-12"
    assert section["output"] == {"ok": True}
