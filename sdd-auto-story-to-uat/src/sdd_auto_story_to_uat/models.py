from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class JiraIssue:
    key: str
    summary: str
    description: str = ""
    issue_type: str = ""
    status: str = ""
    labels: tuple[str, ...] = ()
    parent_key: str | None = None
    url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)

    @classmethod
    def from_jira(cls, payload: dict[str, Any], base_url: str | None = None) -> JiraIssue:
        return cls.from_mcp(payload, base_url=base_url)

    @classmethod
    def from_mcp(cls, payload: dict[str, Any], base_url: str | None = None) -> JiraIssue:
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
        issue_type = _name(
            fields.get("issuetype") or payload.get("issuetype") or payload.get("issue_type")
        )
        status = _name(fields.get("status") or payload.get("status"))
        labels = tuple(fields.get("labels") or payload.get("labels") or [])
        parent = fields.get("parent") or payload.get("parent")
        parent_key = None
        if isinstance(parent, dict):
            parent_key = str(parent.get("key") or parent.get("issueKey") or "") or None
        elif isinstance(parent, str) and parent.strip():
            parent_key = parent
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
            parent_key=parent_key,
            url=str(url) if url else None,
            raw=payload,
        )


@dataclass(frozen=True)
class PullRequest:
    id: str = ""
    title: str = ""
    state: str = ""
    source_branch: str = ""
    destination_branch: str = ""
    description: str = ""
    url: str | None = None
    repository: str | None = None
    merged: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)

    @classmethod
    def from_mcp(cls, payload: dict[str, Any], repository: str | None = None) -> PullRequest:
        source = _branch(
            payload.get("fromRef")
            or payload.get("source")
            or payload.get("from")
            or payload.get("head")
            or payload.get("source_branch")
            or payload.get("sourceBranch")
        )
        dest = _branch(
            payload.get("toRef")
            or payload.get("destination")
            or payload.get("to")
            or payload.get("base")
            or payload.get("destination_branch")
            or payload.get("destinationBranch")
            or payload.get("target")
        )
        state = str(
            payload.get("state")
            or payload.get("status")
            or payload.get("pr_status")
            or ""
        )
        if isinstance(payload.get("status"), dict):
            state = str(payload["status"].get("name") or payload["status"].get("value") or state)
        merged_flag = payload.get("merged")
        if merged_flag is None:
            merged_flag = payload.get("is_merged") or payload.get("isMerged")
        url = payload.get("url")
        links = payload.get("links")
        if not url and isinstance(links, dict):
            html = links.get("html")
            if isinstance(html, dict):
                url = html.get("href")
            elif isinstance(html, str):
                url = html
        return cls(
            id=str(payload.get("id") or payload.get("pr_id") or payload.get("number") or ""),
            title=str(payload.get("title") or payload.get("name") or ""),
            state=state,
            source_branch=source,
            destination_branch=dest,
            description=_description_text(payload.get("description") or payload.get("body") or ""),
            url=str(url) if url else None,
            repository=repository
            or (str(payload["repository"]) if payload.get("repository") else None)
            or (str(payload["repo"]) if payload.get("repo") else None),
            merged=bool(merged_flag) if merged_flag is not None else None,
            raw=payload,
        )


def issues_from_search(payload: Any, base_url: str | None = None) -> list[JiraIssue]:
    raw_items: list[Any]
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        raw_items = (
            payload.get("issues")
            or payload.get("values")
            or payload.get("results")
            or payload.get("items")
            or []
        )
        if not raw_items and payload.get("key"):
            raw_items = [payload]
    else:
        raw_items = []
    issues: list[JiraIssue] = []
    for item in raw_items:
        if isinstance(item, dict):
            issue = JiraIssue.from_mcp(item, base_url=base_url)
            if issue.key:
                issues.append(issue)
    return issues


def stories_from_issue(payload: dict[str, Any], base_url: str | None = None) -> list[JiraIssue]:
    """Stories linked to a release from a Jira MCP `get` payload."""
    fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
    found: list[JiraIssue] = []
    for item in fields.get("subtasks") or payload.get("subtasks") or []:
        if isinstance(item, dict):
            found.append(JiraIssue.from_mcp(item, base_url=base_url))
    for link in fields.get("issuelinks") or payload.get("issuelinks") or payload.get("issue_links") or []:
        if not isinstance(link, dict):
            continue
        other = link.get("outwardIssue") or link.get("inwardIssue") or link.get("issue")
        if isinstance(other, dict):
            found.append(JiraIssue.from_mcp(other, base_url=base_url))
    return [item for item in found if item.key]


def pull_requests_from_payload(
    payload: Any, repository: str | None = None
) -> list[PullRequest]:
    raw_items: list[Any]
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        raw_items = (
            payload.get("values")
            or payload.get("prs")
            or payload.get("pullRequests")
            or payload.get("pull_requests")
            or payload.get("results")
            or payload.get("items")
            or []
        )
        if not raw_items and (payload.get("id") or payload.get("title") or payload.get("fromRef")):
            raw_items = [payload]
    else:
        raw_items = []
    prs: list[PullRequest] = []
    for item in raw_items:
        if isinstance(item, dict):
            prs.append(PullRequest.from_mcp(item, repository=repository))
    return prs


def field_values(issue: JiraIssue, field_name: str) -> list[str]:
    """Read a Jira field (fixVersion, customfield_*, summary) from raw MCP payload."""
    payload = issue.raw or {}
    fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
    raw = fields.get(field_name)
    if raw is None:
        raw = payload.get(field_name)
    if field_name in {"fixVersion", "fixVersions"} and raw is None:
        raw = fields.get("fixVersions") or fields.get("fixVersion") or payload.get("fixVersions")
    return _stringify_field(raw)


def _stringify_field(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    if isinstance(raw, list):
        values: list[str] = []
        for item in raw:
            values.extend(_stringify_field(item))
        return values
    if isinstance(raw, dict):
        name = raw.get("name") or raw.get("value") or raw.get("displayName")
        return [str(name)] if name else []
    return [str(raw)]


def _name(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("name") or value.get("value") or "")
    return str(value)


def _branch(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.removeprefix("refs/heads/")
    if isinstance(value, dict):
        nested = value.get("branch")
        if isinstance(nested, dict):
            return _branch(nested.get("name") or nested.get("displayId"))
        for key in ("displayId", "name", "branch", "id"):
            if value.get(key) and not isinstance(value.get(key), dict):
                return _branch(value[key])
        return ""
    return str(value).removeprefix("refs/heads/")


def _description_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
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
