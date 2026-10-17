from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sdd_auto_story_to_uat.settings import parse_settings


def sample_settings_dict(**overrides) -> dict:
    data = {
        "jira": {"base_url": "https://jira.example.com"},
        "source": {
            "project": "REL",
            "issue_type": "Task",
            "label": "release",
            "status": "In Progress",
        },
        "stories": {"issue_type": "Story", "via": "both"},
        "release": {"branch_pattern": "release/{number}"},
        "bitbucket": {
            "repository": "https://bitbucket.org/acme/payments.git",
        },
        "pr": {"include_child_keys": True},
        "target": {"statuses": ["Ready for UAT"]},
        "limits": {"max_issues": 10, "max_stories": 50, "max_prs": 40},
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
