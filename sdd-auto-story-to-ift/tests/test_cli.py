from __future__ import annotations

import json
from pathlib import Path

from sdd_auto_story_to_ift.cli import main


def test_plan_and_jql(settings_file: Path, capsys):
    assert main(["--settings", str(settings_file), "jql"]) == 0
    jql = capsys.readouterr().out.strip()
    assert 'project = "DEV"' in jql
    assert 'issuetype = "Story"' in jql

    assert main(["--settings", str(settings_file), "plan"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["children"]["ready_statuses"] == ["Готов"]
    assert "searchJiraIssuesUsingJql" in plan["mcp"]["jira_tool_aliases"]["search"]
    assert plan["target_statuses"] == ["Ready for IFT"]


def test_children_jql(settings_file: Path, capsys):
    assert main(["--settings", str(settings_file), "children-jql", "DEV-40"]) == 0
    assert 'parent = "DEV-40"' in capsys.readouterr().out


def test_evaluate_all_ready(settings_file: Path, capsys):
    code = main(
        [
            "--settings",
            str(settings_file),
            "evaluate",
            "DEV-40",
            "--story-status",
            "In Progress",
            "--child",
            "DEV-41:Готов",
            "--child",
            "DEV-42:Sub-task:Готов",
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
                    {"id": "31", "name": "Ready for IFT", "to": {"name": "Ready for IFT"}}
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
                "--story-status",
                "In Progress",
                "--child",
                "DEV-41:Готов",
                "--transitions",
                str(transitions),
            ]
        )
        == 0
    )
    plan = json.loads(capsys.readouterr().out)
    assert plan["children_jql"].startswith('parent = "DEV-40"')
    assert plan["evaluation"]["should_transition"] is True
    assert plan["transition"]["matched"]["id"] == "31"


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
                "Ready for IFT",
            ]
        )
        == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert data["matched"]["name"] == "Ready for IFT"


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
