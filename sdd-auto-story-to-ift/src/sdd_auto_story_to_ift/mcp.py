from __future__ import annotations

from typing import Any, Iterable

JIRA_TOOL_ALIASES = {
    "search": [
        "searchJiraIssuesUsingJql",
        "jira_search",
        "search_issues",
        "jira_search_issues",
        "searchIssues",
    ],
    "get": ["getJiraIssue", "jira_get_issue", "get_issue", "getIssue"],
    "transitions": [
        "getTransitionsForJiraIssue",
        "listJiraIssueTransitions",
        "jira_get_transitions",
        "get_transitions",
        "listTransitions",
    ],
    "transition": [
        "transitionJiraIssue",
        "jira_transition_issue",
        "transition_issue",
        "transitionIssue",
    ],
}

REQUIRED_JIRA_ACTIONS = ("search", "get", "transitions", "transition")


def resolve_tool_names(
    available: Iterable[str],
    aliases: dict[str, list[str]],
) -> dict[str, str | None]:
    """Map logical actions to the first matching MCP tool name."""
    lower = {name.lower(): name for name in available}
    resolved: dict[str, str | None] = {}
    for action, names in aliases.items():
        resolved[action] = None
        for alias in names:
            hit = lower.get(alias.lower())
            if hit:
                resolved[action] = hit
                break
    return resolved


def missing_actions(resolved: dict[str, str | None], required: Iterable[str]) -> list[str]:
    return [action for action in required if not resolved.get(action)]


def parse_transitions(payload: Any) -> list[dict[str, Any]]:
    """Normalize MCP/REST transition lists to `{id, name, to}` dicts."""
    raw_items: list[Any]
    if isinstance(payload, list):
        raw_items = payload
    elif isinstance(payload, dict):
        raw_items = (
            payload.get("transitions")
            or payload.get("values")
            or payload.get("results")
            or payload.get("items")
            or []
        )
    else:
        raw_items = []
    parsed: list[dict[str, Any]] = []
    for item in raw_items:
        if isinstance(item, str) and item.strip():
            parsed.append({"id": "", "name": item, "to": item})
            continue
        if not isinstance(item, dict):
            continue
        to_raw = item.get("to") or item.get("to_status") or item.get("target") or {}
        to_name = ""
        if isinstance(to_raw, dict):
            to_name = str(to_raw.get("name") or to_raw.get("value") or "")
        elif isinstance(to_raw, str):
            to_name = to_raw
        parsed.append(
            {
                "id": str(item.get("id") or item.get("transitionId") or item.get("transition_id") or ""),
                "name": str(item.get("name") or item.get("transition") or ""),
                "to": to_name,
            }
        )
    return parsed


def match_transition(
    transitions: Iterable[dict[str, Any]],
    wanted_statuses: Iterable[str],
) -> dict[str, Any] | None:
    """First transition whose name or destination matches a wanted status (case-insensitive)."""
    wanted = {item.casefold() for item in wanted_statuses if str(item).strip()}
    if not wanted:
        return None
    for item in transitions:
        name = str(item.get("name") or "").casefold()
        to_name = str(item.get("to") or "").casefold()
        if name in wanted or to_name in wanted:
            return item
    return None
