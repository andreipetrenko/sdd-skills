from __future__ import annotations

import pytest

from sdd_auto_story_to_ift.settings import SettingsError, parse_settings


def test_jql_and_children_jql(settings):
    assert (
        settings.source.jql()
        == 'project = "DEV" AND issuetype = "Story" AND labels = "sdd-story" AND status = "In Progress" ORDER BY created ASC'
    )
    assert settings.children_jql("DEV-40") == (
        'parent = "DEV-40" AND issuetype in ("Task", "Sub-task", "Subtask") ORDER BY created ASC'
    )


def test_space_alias_and_defaults():
    settings = parse_settings(
        {
            "source": {"space": "DEV", "type": "Story", "label": "x", "status": "Open"},
        }
    )
    assert settings.source.project == "DEV"
    assert settings.children.issue_types == ("Task", "Sub-task", "Subtask")
    assert settings.children.ready_statuses == ("Готов",)
    assert settings.target.statuses == ("Ready for IFT",)
    assert settings.jira_base_url is None
    assert settings.max_issues == 20
    assert settings.max_children == 100


def test_missing_required_fields():
    with pytest.raises(SettingsError, match="source.project"):
        parse_settings({"source": {"issue_type": "Story"}})
    with pytest.raises(SettingsError, match="source.issue_type"):
        parse_settings({"source": {"project": "DEV"}})
    with pytest.raises(SettingsError, match="source must be a mapping"):
        parse_settings({})


def test_jql_escapes_quotes():
    settings = parse_settings(
        {
            "source": {"project": "DEV", "issue_type": 'Foo "Bar"', "status": "Готов"},
        }
    )
    assert '\\"' in settings.source.jql()


def test_status_and_type_aliases():
    settings = parse_settings(
        {
            "source": {"project": "DEV", "issue_type": "Story"},
            "children": {
                "type": "Task, Подзадача",
                "ready": {"statuses": ["Готов", "Done"]},
            },
            "story": {"target_status": "Ready for IFT"},
        }
    )
    assert settings.children.issue_types == ("Task", "Подзадача")
    assert settings.children.ready_statuses == ("Готов", "Done")
    assert settings.target.statuses == ("Ready for IFT",)


def test_single_child_type_jql():
    settings = parse_settings(
        {
            "source": {"project": "DEV", "issue_type": "Story"},
            "children": {"issue_type": "Task"},
        }
    )
    assert settings.children_jql("DEV-1") == 'parent = "DEV-1" AND issuetype = "Task" ORDER BY created ASC'
