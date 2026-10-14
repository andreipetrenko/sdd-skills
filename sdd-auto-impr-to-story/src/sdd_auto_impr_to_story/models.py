from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class JiraIssue:
    key: str
    summary: str
    description: str
    issue_type: str
    status: str
    labels: tuple[str, ...] = ()
    components: tuple[str, ...] = ()
    url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)

    @classmethod
    def from_jira(cls, payload: dict[str, Any], base_url: str | None = None) -> JiraIssue:
        return cls.from_mcp(payload, base_url=base_url)

    @classmethod
    def from_mcp(cls, payload: dict[str, Any], base_url: str | None = None) -> JiraIssue:
        """Parse a Jira REST issue or a flattened Jira MCP payload."""
        fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
        key = str(
            payload.get("key")
            or payload.get("issueKey")
            or payload.get("issue_key")
            or fields.get("key")
            or ""
        )
        summary = str(
            fields.get("summary") or payload.get("summary") or payload.get("title") or ""
        )
        description = _description_text(
            fields.get("description") if "description" in fields else payload.get("description")
        )
        issue_type = _name(fields.get("issuetype") or payload.get("issuetype") or payload.get("issue_type"))
        status = _name(fields.get("status") or payload.get("status"))
        labels = tuple(fields.get("labels") or payload.get("labels") or [])
        components = tuple(
            _name(item)
            for item in (fields.get("components") or payload.get("components") or [])
            if _name(item)
        )
        url = payload.get("url") or payload.get("self")
        if base_url and key:
            url = f"{base_url.rstrip('/')}/browse/{key}"
        return cls(
            key=key,
            summary=summary,
            description=description,
            issue_type=issue_type,
            status=status,
            labels=tuple(str(item) for item in labels),
            components=components,
            url=str(url) if url else None,
            raw=payload,
        )


@dataclass
class ProcessResult:
    source_key: str
    story_key: str | None = None
    related_key: str | None = None
    source_branch: str | None = None
    story_branch: str | None = None
    openspec_change: str | None = None
    pr_number: int | None = None
    pr_url: str | None = None
    done: bool = False
    skipped: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_key": self.source_key,
            "story_key": self.story_key,
            "related_key": self.related_key,
            "source_branch": self.source_branch,
            "story_branch": self.story_branch,
            "openspec_change": self.openspec_change,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "done": self.done,
            "skipped": self.skipped,
            "error": self.error,
        }


def _name(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("name") or value.get("value") or "")
    return str(value)


def _description_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Jira Cloud ADF
        chunks: list[str] = []
        _walk_adf(value, chunks)
        return "\n".join(part for part in chunks if part).strip()
    return str(value)


def _walk_adf(node: Any, chunks: list[str]) -> None:
    if isinstance(node, dict):
        if node.get("type") == "text" and node.get("text"):
            chunks.append(str(node["text"]))
        elif node.get("type") in {"paragraph", "heading", "blockquote", "listItem"}:
            inner: list[str] = []
            for child in node.get("content") or []:
                _walk_adf(child, inner)
            chunks.append("".join(inner))
        else:
            for child in node.get("content") or []:
                _walk_adf(child, chunks)
    elif isinstance(node, list):
        for child in node:
            _walk_adf(child, chunks)
