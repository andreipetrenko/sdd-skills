from __future__ import annotations

import json
from pathlib import Path

from sdd_auto_release_to_uat.cli import main


def test_plan_and_jql(settings_file: Path, capsys):
    assert main(["--settings", str(settings_file), "jql"]) == 0
    jql = capsys.readouterr().out.strip()
    assert 'project = "REL"' in jql
    assert 'issuetype = "Epic"' in jql

    assert main(["--settings", str(settings_file), "plan"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["stories"]["ready_statuses"] == ["Ready for UAT"]
    assert "searchJiraIssuesUsingJql" in plan["mcp"]["jira_tool_aliases"]["search"]
    assert plan["target_statuses"] == ["Ready for UAT"]


def test_stories_jql(settings_file: Path, capsys):
    assert main(["--settings", str(settings_file), "stories-jql", "REL-12"]) == 0
    out = capsys.readouterr().out
    assert 'parent = "REL-12"' in out
    assert "linkedIssues" in out


def test_evaluate_all_ready(settings_file: Path, capsys):
    code = main(
        [
            "--settings",
            str(settings_file),
            "evaluate",
            "REL-12",
            "--release-status",
            "In Progress",
            "--story",
            "DEV-40:Ready for UAT",
            "--story",
            "DEV-41:Story:Ready for UAT",
        ]
    )
    assert code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["should_transition"] is True
    assert result["all_ready"] is True


def test_issue_plan_with_transitions(settings_file: Path, capsys, tmp_path: Path):
    transitions = tmp_path / "transitions.json"
    transitions.write_text(
        json.dumps(
            {
                "transitions": [
                    {"id": "51", "name": "Ready for UAT", "to": {"name": "Ready for UAT"}}
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
                "REL-12",
                "--release-status",
                "In Progress",
                "--story",
                "DEV-40:Ready for UAT",
                "--transitions",
                str(transitions),
            ]
        )
        == 0
    )
    plan = json.loads(capsys.readouterr().out)
    assert plan["stories_jql"].startswith('(parent = "REL-12"')
    assert plan["evaluation"]["should_transition"] is True
    assert plan["transition"]["matched"]["id"] == "51"


def test_match_transition(settings_file: Path, capsys):
    assert (
        main(
            [
                "--settings",
                str(settings_file),
                "match-transition",
                "--name",
                "In Progress",
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
    assert "transition" in data["jira"]
    assert "create" not in data["jira"]


def test_missing_settings_returns_2(tmp_path: Path, capsys):
    missing = tmp_path / "nope.yaml"
    assert main(["--settings", str(missing), "jql"]) == 2
    assert "not found" in capsys.readouterr().err.lower()
