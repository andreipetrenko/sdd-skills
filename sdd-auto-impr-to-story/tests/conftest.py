from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sdd_auto_impr_to_story.settings import parse_settings


def sample_settings_dict(**overrides) -> dict:
    data = {
        "jira": {"base_url": "https://jira.example.com"},
        "source": {
            "project": "IMPR",
            "issue_type": "Improvement",
            "label": "ready-for-sdd",
            "status": "To Do",
        },
        "story": {
            "project": "DEV",
            "issue_type": "Story",
            "label": "sdd-story",
            "status": "To Do",
            "link_type": "Relates",
            "done_status": "Сделан",
        },
        "bitbucket": {
            "repository": "https://bitbucket.org/acme/app.git",
            "default_branch": "main",
            "source_branch_pattern": "feature/{key}",
            "story_branch_pattern": "feature/{key}",
            "task_branch_pattern": "feature/{key}",
        },
        "component": {
            "repository": "https://bitbucket.org/acme/payments.git",
            "default_branch": "master",
            "task_branch_pattern": "task/{key}",
            "story_branch_pattern": "feature/{key}",
        },
        "related": {
            "issue_type": "Task",
            "link_type": "Relates",
            "component": "backend",
            "component_from_source": True,
            "label": "sdd-impl",
            "status": "To Do",
            "in_progress_status": "В работе",
            "done_status": "Сделан",
        },
        "after_merge": {"statuses": ["В работе", "In Progress"]},
        "improvement_done": {"statuses": ["Сделан", "Done"]},
        "openspec": {
            "capabilities": ["business-requirements", "functional-requirements"]
        },
        "limits": {"max_issues": 10},
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
