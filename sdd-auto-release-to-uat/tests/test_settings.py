from __future__ import annotations

import pytest

from sdd_auto_release_to_uat.settings import SettingsError, parse_settings


def test_jql_and_stories_jql(settings):
    assert (
        settings.source.jql()
        == 'project = "REL" AND issuetype = "Epic" AND labels = "release" AND status = "In Progress" ORDER BY created ASC'
    )
    assert settings.stories_jql("REL-12") == (
        '(parent = "REL-12" OR issue in linkedIssues("REL-12")) '
        'AND issuetype = "Story" ORDER BY created ASC'
    )


def test_space_alias_and_defaults():
    settings = parse_settings(
        {
            "source": {"space": "REL", "type": "Epic", "label": "x"},
        }
    )
    assert settings.source.project == "REL"
    assert settings.stories.issue_types == ("Story",)
    assert settings.stories.ready_statuses == ("Ready for UAT",)
    assert settings.target.statuses == ("Ready for UAT",)
    assert settings.jira_base_url is None


def test_missing_required_fields():
    with pytest.raises(SettingsError, match="source.project"):
        parse_settings({"source": {"issue_type": "Epic"}})
    with pytest.raises(SettingsError, match="source must be a mapping"):
        parse_settings({})


def test_stories_via_and_ready_aliases():
    settings = parse_settings(
        {
            "source": {"project": "REL", "issue_type": "Task"},
            "stories": {
                "via": "linked",
                "link_type": "Relates",
                "ready": {"statuses": ["Ready for UAT", "UAT"]},
            },
            "epic": {"target_status": "Ready for UAT"},
        }
    )
    assert settings.source.issue_type == "Task"
    assert settings.stories_jql("REL-1") == (
        'issue in linkedIssues("REL-1", "Relates") AND issuetype = "Story" ORDER BY created ASC'
    )
    assert settings.stories.ready_statuses == ("Ready for UAT", "UAT")


def test_invalid_via():
    with pytest.raises(SettingsError, match="stories.via"):
        parse_settings(
            {
                "source": {"project": "REL", "issue_type": "Epic"},
                "stories": {"via": "epic"},
            }
        )
