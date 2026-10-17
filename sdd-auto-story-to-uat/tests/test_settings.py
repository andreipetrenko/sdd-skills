from __future__ import annotations

import pytest

from sdd_auto_story_to_uat.settings import SettingsError, parse_settings


def test_jql_and_stories_jql(settings):
    assert (
        settings.source.jql()
        == 'project = "REL" AND issuetype = "Task" AND labels = "release" AND status = "In Progress" ORDER BY created ASC'
    )
    assert settings.stories_jql("REL-12") == (
        '(parent = "REL-12" OR issue in linkedIssues("REL-12")) '
        'AND issuetype = "Story" ORDER BY created ASC'
    )


def test_space_alias_and_defaults():
    settings = parse_settings(
        {
            "source": {"space": "REL", "type": "Task", "label": "x"},
            "git": "https://bitbucket.org/acme/app.git",
        }
    )
    assert settings.source.project == "REL"
    assert settings.stories.issue_types == ("Story",)
    assert settings.release.branch_patterns == ("release/{number}",)
    assert settings.target.statuses == ("Ready for UAT",)
    assert settings.bitbucket.repositories == ("https://bitbucket.org/acme/app.git",)


def test_missing_required_fields():
    with pytest.raises(SettingsError, match="source.project"):
        parse_settings({"source": {"issue_type": "Task"}, "bitbucket": {"repository": "https://bitbucket.org/a/b.git"}})
    with pytest.raises(SettingsError, match="bitbucket.repository"):
        parse_settings({"source": {"project": "REL", "issue_type": "Task"}})


def test_stories_via_and_custom_jql():
    settings = parse_settings(
        {
            "source": {"project": "REL", "issue_type": "Task"},
            "stories": {
                "via": "linked",
                "link_type": "Relates",
                "project": "DEV",
                "status": "Ready for IFT",
            },
            "bitbucket": {"repository": "https://bitbucket.org/a/b.git"},
        }
    )
    assert settings.stories_jql("REL-1") == (
        'issue in linkedIssues("REL-1", "Relates") AND issuetype = "Story" '
        'AND project = "DEV" AND status = "Ready for IFT" ORDER BY created ASC'
    )
    patterned = parse_settings(
        {
            "source": {"project": "REL", "issue_type": "Task"},
            "stories": {"jql_pattern": 'fixVersion = "{release_number}" AND issuetype = Story'},
            "bitbucket": {"repository": "https://bitbucket.org/a/b.git"},
        }
    )
    assert patterned.stories_jql("REL-1", "1.2") == 'fixVersion = "1.2" AND issuetype = Story'


def test_invalid_via():
    with pytest.raises(SettingsError, match="stories.via"):
        parse_settings(
            {
                "source": {"project": "REL", "issue_type": "Task"},
                "stories": {"via": "epic"},
                "bitbucket": {"repository": "https://bitbucket.org/a/b.git"},
            }
        )
