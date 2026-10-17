from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sdd_auto_story_to_ift.settings import parse_settings


def sample_settings_dict(**overrides) -> dict:
    data = {
        "jira": {"base_url": "https://jira.example.com"},
        "source": {
            "project": "DEV",
            "issue_type": "Story",
            "label": "sdd-story",
            "status": "In Progress",
        },
        "children": {
            "issue_type": ["Task", "Sub-task", "Subtask"],
            "ready_status": "Готов",
        },
        "target": {"statuses": ["Ready for IFT"]},
        "limits": {"max_issues": 10, "max_children": 50},
    }
    data.update(overrides)
    return data


@pytest.fixture
def settings_dict() -> dict:
    return sample_settings_dict()


@pytest.fixture
def settings(settings_dict):
    return parse_settings(settings_dict)


@pytest.fixture
def settings_file(tmp_path: Path, settings_dict) -> Path:
    path = tmp_path / "settings.yaml"
    path.write_text(yaml.safe_dump(settings_dict, allow_unicode=True), encoding="utf-8")
    return path
