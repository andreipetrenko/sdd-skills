from __future__ import annotations

import pytest

from sdd_auto_impr_to_story.settings import SettingsError, parse_settings


def test_jql_and_branch_patterns(settings):
    assert (
        settings.source.jql()
        == 'project = "IMPR" AND issuetype = "Improvement" AND labels = "ready-for-sdd" AND status = "To Do" ORDER BY created ASC'
    )
    assert settings.source_branch_name("IMPR-12") == "feature/IMPR-12"
    assert settings.story_branch_name("DEV-40") == "feature/DEV-40"
    assert settings.change_id("IMPR-12") == "impr-12"
    assert settings.story_label_for("IMPR-12") == "sdd-from-IMPR-12"
    assert settings.related_label_for("DEV-40") == "sdd-impl-DEV-40"


def test_space_alias_and_repository_shortcut():
    settings = parse_settings(
        {
            "source": {"space": "IMPR", "type": "Improvement", "label": "x", "status": "Open"},
            "story": {"project": "DEV", "issue_type": "Story"},
            "git": "https://bitbucket.org/acme/app.git",
            "related": {"issue_type": "Task", "link_type": "Blocks"},
        }
    )
    assert settings.source.project == "IMPR"
    assert settings.bitbucket.repository == "https://bitbucket.org/acme/app.git"
    assert settings.related.link_type == "Blocks"
    assert settings.jira_base_url is None
    assert settings.after_merge.statuses == ("В работе", "In Progress")


def test_missing_required_fields():
    with pytest.raises(SettingsError, match="bitbucket.repository"):
        parse_settings(
            {
                "source": {"project": "A", "issue_type": "Improvement"},
                "story": {"project": "B", "issue_type": "Story"},
                "related": {"issue_type": "Task", "link_type": "Relates"},
            }
        )
    with pytest.raises(SettingsError, match="related.issue_type"):
        parse_settings(
            {
                "source": {"project": "A", "issue_type": "Improvement"},
                "story": {"project": "B", "issue_type": "Story"},
                "bitbucket": {"repository": "https://bitbucket.org/a/b.git"},
                "related": {"link_type": "Relates"},
            }
        )


def test_jql_escapes_quotes():
    settings = parse_settings(
        {
            "source": {"project": "IMPR", "issue_type": 'Foo "Bar"', "status": "Сделан"},
            "story": {"project": "DEV", "issue_type": "Story"},
            "bitbucket": {"repository": "https://bitbucket.org/a/b.git"},
            "related": {"issue_type": "Task", "link_type": "Relates"},
        }
    )
    assert '\\"' in settings.source.jql()


def test_done_yaml_key_aliases_after_merge():
    settings = parse_settings(
        {
            "source": {"project": "IMPR", "issue_type": "Improvement"},
            "story": {"project": "DEV", "issue_type": "Story"},
            "bitbucket": {"repository": "https://bitbucket.org/a/b.git"},
            "related": {"issue_type": "Task", "link_type": "Relates"},
            "done": {"statuses": ["В работе"]},
        }
    )
    assert settings.after_merge.statuses == ("В работе",)
