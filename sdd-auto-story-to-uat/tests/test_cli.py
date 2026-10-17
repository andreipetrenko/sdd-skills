from __future__ import annotations

import json
from pathlib import Path

from sdd_auto_story_to_uat.cli import main


def test_plan_and_jql(settings_file: Path, capsys):
    assert main(["--settings", str(settings_file), "jql"]) == 0
    jql = capsys.readouterr().out.strip()
    assert 'project = "REL"' in jql
    assert 'issuetype = "Task"' in jql

    assert main(["--settings", str(settings_file), "plan"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["target_statuses"] == ["Ready for UAT"]
    assert plan["bitbucket"][0]["repo_slug"] == "payments"
    assert "searchJiraIssuesUsingJql" in plan["mcp"]["jira_tool_aliases"]["search"]
    assert "listBitbucketRepoPullRequests" in plan["mcp"]["bitbucket_tool_aliases"]["list_prs"]


def test_stories_jql(settings_file: Path, capsys):
    assert main(["--settings", str(settings_file), "stories-jql", "REL-12"]) == 0
    out = capsys.readouterr().out
    assert 'parent = "REL-12"' in out
    assert "linkedIssues" in out


def test_release_number_from_summary(settings_file: Path, capsys):
    assert (
        main(
            [
                "--settings",
                str(settings_file),
                "release-number",
                "REL-12",
                "--summary",
                "Релиз 1.2",
            ]
        )
        == 0
    )
    assert capsys.readouterr().out.strip() == "1.2"


def test_evaluate_all_ready(settings_file: Path, capsys):
    code = main(
        [
            "--settings",
            str(settings_file),
            "evaluate",
            "DEV-40",
            "--release",
            "REL-12",
            "--release-number",
            "1.2",
            "--story-status",
            "Ready for IFT",
            "--pr",
            "feature/DEV-40:MERGED:release/1.2",
        ]
    )
    assert code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["should_transition"] is True
    assert result["release_number"] == "1.2"


def test_issue_plan_with_transitions(settings_file: Path, capsys, tmp_path: Path):
    transitions = tmp_path / "transitions.json"
    transitions.write_text(
        json.dumps(
            {
                "transitions": [
                    {"id": "41", "name": "Ready for UAT", "to": {"name": "Ready for UAT"}}
                ]
            }
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "--settings",
                str(settings_file),
                "issue-plan",
                "DEV-40",
                "--release",
                "REL-12",
                "--release-number",
                "1.2",
                "--story-status",
                "Ready for IFT",
                "--pr",
                "feature/DEV-40:MERGED:release/1.2",
                "--transitions",
                str(transitions),
            ]
        )
        == 0
    )
    plan = json.loads(capsys.readouterr().out)
    assert plan["stories_jql"].startswith("(parent = \"REL-12\"")
    assert plan["evaluation"]["should_transition"] is True
    assert plan["transition"]["matched"]["id"] == "41"


def test_match_transition(settings_file: Path, capsys):
    assert (
        main(
            [
                "--settings",
                str(settings_file),
                "match-transition",
                "--name",
                "Ready for IFT",
                "--name",
                "Ready for UAT",
            ]
        )
        == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert data["matched"]["name"] == "Ready for UAT"


def test_mcp_aliases(settings_file: Path, capsys):
    assert main(["--settings", str(settings_file), "mcp-aliases"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert "search" in data["jira"]
    assert "list_prs" in data["bitbucket"]


def test_missing_settings_returns_2(tmp_path: Path, capsys):
    missing = tmp_path / "nope.yaml"
    assert main(["--settings", str(missing), "jql"]) == 2
    assert "not found" in capsys.readouterr().err.lower()
