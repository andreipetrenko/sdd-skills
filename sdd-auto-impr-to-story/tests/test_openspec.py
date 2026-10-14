from __future__ import annotations

from pathlib import Path

from sdd_auto_impr_to_story.models import JiraIssue
from sdd_auto_impr_to_story.openspec import scaffold_change, validate_change


def test_scaffold_writes_br_and_fr(settings, tmp_path: Path):
    source = JiraIssue(
        key="IMPR-12",
        summary="Notify when invoice is overdue",
        description=(
            "- Finance must see overdue invoices\n"
            "- The system sends a reminder email after 3 days\n"
        ),
        issue_type="Improvement",
        status="To Do",
    )
    target = scaffold_change(tmp_path, settings, source, "DEV-40")
    assert (target / "proposal.md").is_file()
    br = target / "specs" / "business-requirements" / "spec.md"
    fr = target / "specs" / "functional-requirements" / "spec.md"
    assert br.is_file()
    assert fr.is_file()
    br_text = br.read_text(encoding="utf-8")
    fr_text = fr.read_text(encoding="utf-8")
    assert "### Requirement:" in br_text
    assert "#### Scenario:" in br_text
    assert "SHALL" in br_text
    assert "### Requirement:" in fr_text
    assert "#### Scenario:" in fr_text
    proposal = (target / "proposal.md").read_text(encoding="utf-8")
    assert "## Why" in proposal
    assert "DEV-40" in proposal
    assert "bitbucket.org/acme/app.git" in proposal
    assert validate_change(target) == []


def test_validate_detects_missing_scenarios(tmp_path: Path):
    change = tmp_path / "openspec" / "changes" / "x"
    change.mkdir(parents=True)
    (change / "proposal.md").write_text(
        "# Proposal\n\n## Why\n\n## What Changes\n\n## Capabilities\n",
        encoding="utf-8",
    )
    spec = change / "specs" / "business-requirements" / "spec.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("### Requirement: X\nThe system SHALL y.\n", encoding="utf-8")
    errors = validate_change(change)
    assert any("Scenario" in item for item in errors)
