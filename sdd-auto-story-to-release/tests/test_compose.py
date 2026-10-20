from __future__ import annotations

from sdd_auto_story_to_release.compose import compose, extract_release_number, parse_story_token
from sdd_auto_story_to_release.models import JiraIssue
from sdd_auto_story_to_release.settings import parse_settings


def _release(summary: str = "Release 1.2") -> JiraIssue:
    return JiraIssue(key="REL-12", summary=summary, issue_type="Story")


def _story(key: str, *components: str, issue_type: str = "Story") -> JiraIssue:
    return JiraIssue(key=key, summary=key, issue_type=issue_type, components=components)


def test_compose_branch_and_pr_per_component(settings):
    result = compose(
        settings,
        _release(),
        [_story("DEV-40", "backend"), _story("DEV-41", "backend")],
    )
    assert result.release_number == "1.2"
    assert len(result.branches) == 1
    assert result.branches[0].name == "release/1.2"
    assert result.branches[0].start_point == "master"
    assert {pr.story_key for pr in result.pull_requests} == {"DEV-40", "DEV-41"}
    assert all(pr.head == f"feature/{pr.story_key}" for pr in result.pull_requests)
    assert all(pr.base == "release/1.2" for pr in result.pull_requests)
    assert result.skipped == ()


def test_story_with_two_components_gets_two_prs():
    settings = parse_settings(
        {
            "components": [
                {"name": "backend", "repository": "https://bitbucket.org/acme/pay.git"},
                {"name": "ui", "repository": "https://bitbucket.org/acme/ui.git"},
            ]
        }
    )
    result = compose(settings, _release(), [_story("DEV-40", "backend", "ui")])
    assert len(result.branches) == 2
    assert len(result.pull_requests) == 2
    repos = {pr.repository for pr in result.pull_requests}
    assert repos == {
        "https://bitbucket.org/acme/pay.git",
        "https://bitbucket.org/acme/ui.git",
    }


def test_empty_composition_skips(settings):
    result = compose(settings, _release(), [])
    assert result.branches == ()
    assert result.pull_requests == ()
    assert "нет Story" in result.skipped[0].reason


def test_missing_component_skips_story(settings):
    result = compose(settings, _release(), [_story("DEV-40")])
    # fallback related.component = backend is applied
    assert [pr.story_key for pr in result.pull_requests] == ["DEV-40"]

    no_fallback = parse_settings(
        {
            "components": [
                {"name": "ui", "repository": "https://bitbucket.org/acme/ui.git"}
            ]
        }
    )
    result = compose(no_fallback, _release(), [_story("DEV-40")])
    assert result.pull_requests == ()
    assert "нет Jira Component" in result.skipped[0].reason


def test_unknown_component_repo_is_skipped():
    settings = parse_settings(
        {
            "components": [
                {"name": "backend", "repository": "https://bitbucket.org/acme/pay.git"}
            ]
        }
    )
    result = compose(settings, _release(), [_story("DEV-40", "ui")])
    assert result.pull_requests == ()
    assert "нет репозитория" in result.skipped[0].reason


def test_other_issue_types_ignored(settings):
    result = compose(
        settings,
        _release(),
        [_story("DEV-40", "backend", issue_type="Bug"), _story("DEV-41", "backend")],
    )
    assert [story.key for story in result.stories] == ["DEV-41"]
    assert [pr.story_key for pr in result.pull_requests] == ["DEV-41"]


def test_extract_number_and_token(settings):
    assert extract_release_number(settings, _release("Релиз 1.4.0")) == "1.4.0"
    token = parse_story_token("DEV-40:backend")
    assert token.key == "DEV-40"
    assert token.components == ("backend",)
