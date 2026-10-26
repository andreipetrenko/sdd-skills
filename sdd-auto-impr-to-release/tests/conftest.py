from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sdd_auto_impr_to_release.settings import parse_settings


ROOT = Path(__file__).resolve().parents[1]


def sample_settings_dict(**overrides) -> dict:
    data = yaml.safe_load((ROOT / "settings.example.yaml").read_text(encoding="utf-8"))
    data.update(overrides)
    return data


@pytest.fixture
def settings_dict() -> dict:
    return sample_settings_dict()


@pytest.fixture
def settings(settings_dict, tmp_path: Path):
    path = tmp_path / "settings.yaml"
    path.write_text(yaml.safe_dump(settings_dict, allow_unicode=True), encoding="utf-8")
    return parse_settings(settings_dict, path=path)


@pytest.fixture
def settings_file(tmp_path: Path, settings_dict) -> Path:
    settings_dict = dict(settings_dict)
    settings_dict["storage"] = {"path": "storage.yaml"}
    path = tmp_path / "settings.yaml"
    path.write_text(yaml.safe_dump(settings_dict, allow_unicode=True), encoding="utf-8")
    return path
