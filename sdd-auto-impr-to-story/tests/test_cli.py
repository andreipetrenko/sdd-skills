from __future__ import annotations

import json
from pathlib import Path

from sdd_auto_impr_to_story.cli import main


def test_plan_and_jql(settings_file: Path, capsys):
    assert main(["--settings", str(settings_file), "jql"]) == 0
    jql = capsys.readouterr().out.strip()
    assert 'project = "IMPR"' in jql
    assert 'issuetype = "Improvement"' in jql

    assert main(["--settings", str(settings_file), "plan"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["bitbucket"]["repo_slug"] == "app"
    assert "searchJiraIssuesUsingJql" in plan["mcp"]["jira_tool_aliases"]["search"]


def test_issue_plan(settings_file: Path, capsys):
    code = main(
        [
            "--settings",
            str(settings_file),
            "issue-plan",
            "IMPR-12",
            "--summary",
            "CSV export",
            "--description",
            "Need a file download",
            "--story",
            "DEV-40",
            "--task",
            "DEV-55",
            "--component",
            "payments",
        ]
    )
    assert code == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["pr"]["head"] == "feature/IMPR-12"
    assert plan["pr"]["base"] == "feature/DEV-40"
    assert plan["component"] == "payments"
    assert plan["implementation"]["component_repo"]["task_branch"] == "task/DEV-55"


def test_scaffold_and_validate(settings_file: Path, tmp_path: Path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    assert (
        main(
            [
                "--settings",
                str(settings_file),
                "scaffold-specs",
                "IMPR-12",
                "--summary",
                "Notify when invoice is overdue",
                "--description",
                "- Finance must see overdue invoices",
                "--story",
                "DEV-40",
                "--repo",
                str(repo),
            ]
        )
        == 0
    )
    target = Path(capsys.readouterr().out.strip())
    assert (target / "proposal.md").is_file()
    assert main(
        ["--settings", str(settings_file), "validate-specs", "IMPR-12", "--repo", str(repo)]
    ) == 0
    assert "looks valid" in capsys.readouterr().out


def test_mcp_aliases(settings_file: Path, capsys):
    assert main(["--settings", str(settings_file), "mcp-aliases"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert "search" in data["jira"]
    assert "create_pr" in data["bitbucket"]


def test_missing_settings_returns_2(tmp_path: Path, capsys):
    missing = tmp_path / "nope.yaml"
    assert main(["--settings", str(missing), "jql"]) == 2
    assert "not found" in capsys.readouterr().err.lower()
