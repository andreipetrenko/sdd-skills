from __future__ import annotations

from sdd_auto_impr_to_story.fields import build_related_fields, build_story_fields, resolve_component
from sdd_auto_impr_to_story.models import JiraIssue, _description_text


def test_story_and_related_payloads(settings):
    source = JiraIssue(
        key="IMPR-12",
        summary="Add export to CSV",
        description="Users need a CSV export from the report page.",
        issue_type="Improvement",
        status="To Do",
        labels=("ready-for-sdd",),
        components=("payments",),
        url="https://jira.example.com/browse/IMPR-12",
    )
    fields = build_story_fields(settings, source)
    assert fields["project"] == "DEV"
    assert fields["issue_type"] == "Story"
    assert fields["summary"].startswith("IMPR-12:")
    assert "sdd-from-IMPR-12" in fields["labels"]
    assert "CSV export" in fields["description"]

    story = JiraIssue(
        key="DEV-40",
        summary=fields["summary"],
        description=fields["description"],
        issue_type="Story",
        status="To Do",
        labels=tuple(fields["labels"]),
    )
    component = resolve_component(settings, source, story)
    assert component == "payments"
    related = build_related_fields(settings, source, story, component)
    assert related["issue_type"] == "Task"
    assert related["components"] == ["payments"]
    assert "[payments]" in related["summary"]
    assert "DEV-40" in related["summary"]
    assert "sdd-impl-DEV-40" in related["labels"]


def test_component_fallback_to_settings(settings):
    source = JiraIssue(
        key="IMPR-1",
        summary="x",
        description="",
        issue_type="Improvement",
        status="To Do",
    )
    assert resolve_component(settings, source) == "backend"


def test_adf_description_flattens():
    adf = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Hello"}],
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "World"}],
            },
        ],
    }
    assert _description_text(adf) == "Hello\nWorld"


def test_from_mcp_accepts_rest_and_flat_payloads():
    rest = JiraIssue.from_mcp(
        {
            "key": "IMPR-12",
            "fields": {
                "summary": "Export",
                "description": "Need CSV",
                "issuetype": {"name": "Improvement"},
                "status": {"name": "To Do"},
                "labels": ["ready-for-sdd"],
                "components": [{"name": "payments"}],
            },
        },
        base_url="https://jira.example.com",
    )
    assert rest.key == "IMPR-12"
    assert rest.components == ("payments",)
    assert rest.url == "https://jira.example.com/browse/IMPR-12"

    flat = JiraIssue.from_mcp(
        {
            "issueKey": "IMPR-13",
            "summary": "Flat",
            "description": "From MCP",
            "issue_type": "Improvement",
            "status": "Open",
            "labels": ["x"],
            "components": ["ui"],
        }
    )
    assert flat.key == "IMPR-13"
    assert flat.issue_type == "Improvement"
    assert flat.components == ("ui",)
