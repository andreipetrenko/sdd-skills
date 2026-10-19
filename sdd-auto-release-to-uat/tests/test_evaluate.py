from __future__ import annotations

from sdd_auto_release_to_uat.evaluate import evaluate_release, parse_story_token
from sdd_auto_release_to_uat.models import JiraIssue, stories_from_issue
from sdd_auto_release_to_uat.settings import parse_settings


def _release(status: str = "In Progress") -> JiraIssue:
    return JiraIssue(key="REL-12", summary="Release epic", issue_type="Epic", status=status)


def _story(key: str, status: str, issue_type: str = "Story") -> JiraIssue:
    return JiraIssue(key=key, summary=key, issue_type=issue_type, status=status)


def test_all_stories_ready_triggers_transition(settings):
    result = evaluate_release(
        settings,
        _release(),
        [_story("DEV-40", "Ready for UAT"), _story("DEV-41", "ready for uat")],
    )
    assert result.all_ready is True
    assert result.should_transition is True
    assert result.skip_reason is None


def test_any_not_ready_skips(settings):
    result = evaluate_release(
        settings,
        _release(),
        [_story("DEV-40", "Ready for UAT"), _story("DEV-41", "Ready for IFT")],
    )
    assert result.should_transition is False
    assert result.all_ready is False
    assert "DEV-41" in (result.skip_reason or "")


def test_empty_stories_does_not_transition(settings):
    result = evaluate_release(settings, _release(), [])
    assert result.should_transition is False
    assert "нет Story" in (result.skip_reason or "")


def test_already_target_skips_even_if_stories_ready(settings):
    result = evaluate_release(
        settings,
        _release("Ready for UAT"),
        [_story("DEV-40", "Ready for UAT")],
    )
    assert result.already_target is True
    assert result.should_transition is False


def test_other_issue_types_are_ignored(settings):
    result = evaluate_release(
        settings,
        _release(),
        [_story("DEV-40", "Open", "Bug"), _story("DEV-41", "Ready for UAT")],
    )
    assert [story.key for story in result.stories] == ["DEV-41"]
    assert result.should_transition is True


def test_parse_story_token_with_type():
    story = parse_story_token("DEV-40:Story:Ready for UAT")
    assert story.key == "DEV-40"
    assert story.issue_type == "Story"
    assert story.status == "Ready for UAT"


def test_stories_from_get_payload():
    payload = {
        "key": "REL-12",
        "fields": {
            "summary": "Release",
            "issuetype": {"name": "Epic"},
            "status": {"name": "In Progress"},
            "issuelinks": [
                {
                    "outwardIssue": {
                        "key": "DEV-40",
                        "fields": {
                            "summary": "one",
                            "issuetype": {"name": "Story"},
                            "status": {"name": "Ready for UAT"},
                        },
                    }
                }
            ],
        },
    }
    found = stories_from_issue(payload)
    assert found[0].key == "DEV-40"


def test_custom_ready_and_target_statuses():
    settings = parse_settings(
        {
            "source": {"project": "REL", "issue_type": "Epic"},
            "stories": {"ready_status": "UAT Ready"},
            "target": "Go UAT",
        }
    )
    result = evaluate_release(
        settings,
        _release(),
        [_story("DEV-40", "UAT Ready")],
    )
    assert result.should_transition is True
    assert result.target_statuses == ("Go UAT",)
