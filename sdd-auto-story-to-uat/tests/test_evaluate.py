from __future__ import annotations

from sdd_auto_story_to_uat.evaluate import (
    evaluate_story,
    extract_release_number,
    is_release_destination,
    parse_pr_token,
)
from sdd_auto_story_to_uat.models import JiraIssue, PullRequest, pull_requests_from_payload
from sdd_auto_story_to_uat.settings import parse_settings


def _story(status: str = "Ready for IFT") -> JiraIssue:
    return JiraIssue(key="DEV-40", summary="UAT story", issue_type="Story", status=status)


def _pr(state: str, dest: str, source: str = "feature/DEV-40", title: str = "DEV-40") -> PullRequest:
    return PullRequest(title=title, state=state, source_branch=source, destination_branch=dest)


def test_all_prs_merged_to_release_triggers_transition(settings):
    result = evaluate_story(
        settings,
        _story(),
        [_pr("MERGED", "release/1.2"), _pr("MERGED", "release/1.2.0", source="task/DEV-41", title="DEV-41")],
        release_number="1.2",
        release_key="REL-12",
        child_keys=["DEV-41"],
    )
    assert result.should_transition is True
    assert result.all_merged_to_release is True
    assert result.skip_reason is None


def test_open_pr_skips(settings):
    result = evaluate_story(
        settings,
        _story(),
        [_pr("MERGED", "release/1.2"), _pr("OPEN", "release/1.2", source="hotfix/DEV-40")],
        release_number="1.2",
    )
    assert result.should_transition is False
    assert "не все PR" in (result.skip_reason or "")


def test_merged_to_main_skips(settings):
    result = evaluate_story(
        settings,
        _story(),
        [_pr("MERGED", "main")],
        release_number="1.2",
    )
    assert result.should_transition is False


def test_feature_destination_is_ignored(settings):
    result = evaluate_story(
        settings,
        _story(),
        [_pr("MERGED", "feature/DEV-40"), _pr("MERGED", "release/1.2")],
        release_number="1.2",
    )
    assert len(result.considered) == 1
    assert result.should_transition is True


def test_declined_pr_is_ignored(settings):
    result = evaluate_story(
        settings,
        _story(),
        [_pr("DECLINED", "release/1.2"), _pr("MERGED", "release/1.2")],
        release_number="1.2",
    )
    assert result.should_transition is True


def test_no_prs_does_not_transition(settings):
    result = evaluate_story(settings, _story(), [], release_number="1.2")
    assert result.should_transition is False
    assert "нет PR" in (result.skip_reason or "")


def test_already_target_skips(settings):
    result = evaluate_story(
        settings,
        _story("Ready for UAT"),
        [_pr("MERGED", "release/1.2")],
        release_number="1.2",
    )
    assert result.already_target is True
    assert result.should_transition is False


def test_unrelated_pr_is_ignored(settings):
    result = evaluate_story(
        settings,
        _story(),
        [_pr("MERGED", "release/1.2", source="feature/OTHER-1", title="OTHER-1")],
        release_number="1.2",
    )
    assert result.considered == ()
    assert result.should_transition is False


def test_release_destination_patterns():
    assert is_release_destination("release/1.2", "1.2", ("release/{number}",))
    assert is_release_destination("release/1.2.0", "1.2", ("release/{number}",))
    assert is_release_destination("refs/heads/release/1.2", "1.2", ("release/{number}",))
    assert not is_release_destination("release/10", "1", ("release/{number}",))
    assert not is_release_destination("feature/1.2", "1.2", ("release/{number}",))


def test_extract_release_number_from_summary(settings):
    release = JiraIssue(key="REL-12", summary="Release 1.2.0", issue_type="Task")
    assert extract_release_number(settings, release) == "1.2.0"


def test_extract_release_number_from_fix_version(settings):
    release = JiraIssue.from_mcp(
        {
            "key": "REL-12",
            "fields": {
                "summary": "Prepare release",
                "issuetype": {"name": "Task"},
                "fixVersions": [{"name": "1.4"}],
            },
        }
    )
    assert extract_release_number(settings, release) == "1.4"


def test_extract_explicit_and_settings_number():
    settings = parse_settings(
        {
            "source": {"project": "REL", "issue_type": "Task"},
            "release": {"number": "9.9"},
            "bitbucket": {"repository": "https://bitbucket.org/a/b.git"},
        }
    )
    assert extract_release_number(settings, explicit="2.0") == "2.0"
    assert extract_release_number(settings) == "9.9"


def test_parse_pr_token_and_mcp_payload():
    token = parse_pr_token("feature/DEV-40:MERGED:release/1.2")
    assert token.source_branch == "feature/DEV-40"
    assert token.state == "MERGED"
    assert token.destination_branch == "release/1.2"
    parsed = pull_requests_from_payload(
        {
            "values": [
                {
                    "id": 17,
                    "title": "DEV-40 payments",
                    "state": "MERGED",
                    "fromRef": {"displayId": "feature/DEV-40"},
                    "toRef": {"id": "refs/heads/release/1.2"},
                }
            ]
        }
    )
    assert parsed[0].source_branch == "feature/DEV-40"
    assert parsed[0].destination_branch == "release/1.2"
