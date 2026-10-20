from __future__ import annotations

import pytest

from sdd_auto_story_to_release.settings import SettingsError, parse_settings


def test_stories_jql_matches_skill_2(settings):
    assert settings.stories_jql("REL-12") == (
        '(parent = "REL-12" OR issue in linkedIssues("REL-12")) '
        'AND issuetype = "Story" ORDER BY created ASC'
    )
    assert settings.release.branch_name("1.2") == "release/1.2"


def test_single_component_from_impr_style_blocks():
    settings = parse_settings(
        {
            "component": {"repository": "https://bitbucket.org/acme/app.git"},
            "related": {"component": "backend"},
        }
    )
    assert settings.lookup_component("backend") is not None
    assert settings.lookup_component("backend").default_branch == "master"
    assert settings.lookup_component("backend").story_branch_name("DEV-40") == "feature/DEV-40"


def test_unnamed_repo_without_fallback_is_error():
    with pytest.raises(SettingsError, match="без имени"):
        parse_settings({"bitbucket": {"repository": "https://bitbucket.org/acme/app.git"}})


def test_missing_repository():
    with pytest.raises(SettingsError, match="repository"):
        parse_settings({"stories": {"via": "both"}})


def test_multiple_components():
    settings = parse_settings(
        {
            "components": [
                {
                    "name": "backend",
                    "repository": "https://bitbucket.org/acme/payments.git",
                },
                {"name": "ui", "repository": "https://bitbucket.org/acme/ui.git"},
            ]
        }
    )
    assert settings.lookup_component("UI").repository.endswith("ui.git")
    assert settings.lookup_component("unknown") is None
