from __future__ import annotations

import json
from pathlib import Path

from sdd_auto_story_to_release.cli import main


def test_plan_and_stories_jql(settings_file: Path, capsys):
    assert main(["--settings", str(settings_file), "plan"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["release"]["branch_patterns"] == ["release/{number}"]
    assert "createBitbucketRepoBranch" in plan["mcp"]["bitbucket_tool_aliases"]["create_branch"]

    assert main(["--settings", str(settings_file), "stories-jql", "REL-12"]) == 0
    out = capsys.readouterr().out
    assert 'parent = "REL-12"' in out
    assert "linkedIssues" in out


def test_compose_cli(settings_file: Path, capsys):
    assert (
        main(
            [
                "--settings",
                str(settings_file),
                "compose",
                "REL-12",
                "--release-number",
                "1.2",
                "--story",
                "DEV-40:backend",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["release_number"] == "1.2"
    assert result["branches"][0]["name"] == "release/1.2"
    assert result["pull_requests"][0]["head"] == "feature/DEV-40"
    assert result["pull_requests"][0]["base"] == "release/1.2"


def test_issue_plan_and_aliases(settings_file: Path, capsys):
    assert (
        main(
            [
                "--settings",
                str(settings_file),
                "issue-plan",
                "REL-12",
                "--release-number",
                "1.2",
                "--story",
                "DEV-40:backend",
            ]
        )
        == 0
    )
    plan = json.loads(capsys.readouterr().out)
    assert plan["mcp"]["create_pr"][0]["base"] == "release/1.2"

    assert main(["--settings", str(settings_file), "mcp-aliases"]) == 0
    aliases = json.loads(capsys.readouterr().out)
    assert "search" in aliases["jira"]
    assert "create_pr" in aliases["bitbucket"]
    assert "transition" not in aliases["jira"]


def test_missing_settings_returns_2(tmp_path: Path, capsys):
    missing = tmp_path / "nope.yaml"
    assert main(["--settings", str(missing), "plan"]) == 2
    assert "not found" in capsys.readouterr().err.lower()
