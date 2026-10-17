from __future__ import annotations

from sdd_auto_story_to_ift.evaluate import evaluate_story, parse_child_token
from sdd_auto_story_to_ift.mcp import match_transition, parse_transitions
from sdd_auto_story_to_ift.models import JiraIssue, children_from_issue, issues_from_search
from sdd_auto_story_to_ift.settings import parse_settings


def _story(status: str = "In Progress") -> JiraIssue:
    return JiraIssue(key="DEV-40", summary="IFT story", issue_type="Story", status=status)


def test_all_children_ready_triggers_transition(settings):
    children = [
        JiraIssue(key="DEV-41", summary="a", issue_type="Task", status="Готов"),
        JiraIssue(key="DEV-42", summary="b", issue_type="Sub-task", status="готов"),
    ]
    result = evaluate_story(settings, _story(), children)
    assert result.all_ready is True
    assert result.should_transition is True
    assert result.skip_reason is None


def test_any_not_ready_skips(settings):
    children = [
        JiraIssue(key="DEV-41", summary="a", issue_type="Task", status="Готов"),
        JiraIssue(key="DEV-42", summary="b", issue_type="Task", status="В работе"),
    ]
    result = evaluate_story(settings, _story(), children)
    assert result.should_transition is False
    assert result.all_ready is False
    assert "DEV-42" in (result.skip_reason or "")


def test_no_children_does_not_transition(settings):
    result = evaluate_story(settings, _story(), [])
    assert result.should_transition is False
    assert "нет дочерних" in (result.skip_reason or "")


def test_already_target_skips_even_if_children_ready(settings):
    children = [JiraIssue(key="DEV-41", summary="a", issue_type="Task", status="Готов")]
    result = evaluate_story(settings, _story("Ready for IFT"), children)
    assert result.already_target is True
    assert result.should_transition is False


def test_other_issue_types_are_ignored(settings):
    children = [
        JiraIssue(key="DEV-41", summary="a", issue_type="Bug", status="Open"),
        JiraIssue(key="DEV-42", summary="b", issue_type="Task", status="Готов"),
    ]
    result = evaluate_story(settings, _story(), children)
    assert [child.key for child in result.children] == ["DEV-42"]
    assert result.should_transition is True


def test_parse_child_token_with_type():
    child = parse_child_token("DEV-41:Sub-task:Готов")
    assert child.key == "DEV-41"
    assert child.issue_type == "Sub-task"
    assert child.status == "Готов"


def test_match_transition_by_destination_name():
    matched = match_transition(
        parse_transitions(
            {
                "transitions": [
                    {"id": "11", "name": "Start", "to": {"name": "In Progress"}},
                    {"id": "31", "name": "Move to IFT", "to": {"name": "Ready for IFT"}},
                ]
            }
        ),
        ("Ready for IFT",),
    )
    assert matched is not None
    assert matched["id"] == "31"


def test_children_from_get_and_search_payloads():
    story_payload = {
        "key": "DEV-40",
        "fields": {
            "summary": "Story",
            "issuetype": {"name": "Story"},
            "status": {"name": "In Progress"},
            "subtasks": [
                {
                    "key": "DEV-41",
                    "fields": {
                        "summary": "child",
                        "issuetype": {"name": "Sub-task"},
                        "status": {"name": "Готов"},
                    },
                }
            ],
        },
    }
    from_get = children_from_issue(story_payload)
    assert from_get[0].key == "DEV-41"
    from_search = issues_from_search(
        {
            "issues": [
                {
                    "issueKey": "DEV-42",
                    "summary": "task",
                    "issue_type": "Task",
                    "status": "Готов",
                }
            ]
        }
    )
    assert from_search[0].key == "DEV-42"


def test_custom_ready_and_target_statuses():
    settings = parse_settings(
        {
            "source": {"project": "DEV", "issue_type": "Story"},
            "children": {"issue_type": "Task", "ready_status": "Done"},
            "target": "IFT",
        }
    )
    result = evaluate_story(
        settings,
        _story(),
        [JiraIssue(key="DEV-41", summary="a", issue_type="Task", status="Done")],
    )
    assert result.should_transition is True
    assert result.target_statuses == ("IFT",)
