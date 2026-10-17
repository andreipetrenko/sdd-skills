from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sdd_auto_story_to_ift.evaluate import evaluate_story, parse_child_token
from sdd_auto_story_to_ift.mcp import JIRA_TOOL_ALIASES, match_transition, parse_transitions
from sdd_auto_story_to_ift.models import JiraIssue, children_from_issue, issues_from_search
from sdd_auto_story_to_ift.plan import build_issue_plan, build_plan
from sdd_auto_story_to_ift.settings import SettingsError, find_settings_file, load_settings


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "mcp-aliases":
        print(json.dumps({"jira": JIRA_TOOL_ALIASES}, ensure_ascii=False, indent=2))
        return 0
    try:
        settings_path = find_settings_file(args.settings)
        settings = load_settings(settings_path)
    except SettingsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        if args.command == "plan":
            print(json.dumps(build_plan(settings), ensure_ascii=False, indent=2))
            return 0
        if args.command == "jql":
            print(settings.source.jql())
            return 0
        if args.command == "children-jql":
            print(settings.children_jql(args.issue))
            return 0
        if args.command == "issue-plan":
            story, children = _story_and_children(args)
            transitions = _load_json_arg(args.transitions) if args.transitions else None
            print(
                json.dumps(
                    build_issue_plan(settings, story, children, transitions=transitions),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.command == "evaluate":
            story, children = _story_and_children(args)
            result = evaluate_story(settings, story, children)
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "match-transition":
            raw = _load_json_arg(args.transitions) if args.transitions else args.name
            matched = match_transition(parse_transitions(raw), settings.target.statuses)
            print(json.dumps({"matched": matched}, ensure_ascii=False, indent=2))
            return 0 if matched else 1
        parser.print_help()
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdd-auto-story-to-ift",
        description=(
            "Локальные хелперы скилла: JQL поиска Story и дочерних задач, "
            "план и оценка перехода. Запись в Jira — только через MCP."
        ),
    )
    parser.add_argument("--settings", help="Path to settings.yaml")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("plan", help="Печатает план MCP-конвейера из settings.yaml")
    sub.add_parser("jql", help="Печатает JQL поиска Story (пункт 1)")

    children = sub.add_parser("children-jql", help="Печатает JQL дочерних задач Story")
    children.add_argument("issue", help="Ключ Story")

    issue = sub.add_parser("issue-plan", help="План по одной Story: JQL детей, оценка, MCP")
    _add_story_args(issue)

    evaluate = sub.add_parser(
        "evaluate",
        help="Решает, нужно ли переводить Story, по статусам детей",
    )
    _add_story_args(evaluate)

    match = sub.add_parser(
        "match-transition",
        help="Выбирает переход Jira по имени/назначению из target.statuses",
    )
    match.add_argument(
        "--name",
        action="append",
        default=[],
        help="Имя перехода или целевого статуса (можно несколько)",
    )
    match.add_argument(
        "--transitions",
        help="JSON файл или строка со списком transitions MCP/REST",
    )

    sub.add_parser("mcp-aliases", help="Печатает алиасы Jira MCP")
    return parser


def _add_story_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("issue", help="Ключ Story")
    parser.add_argument("--story-status", default="", help="Текущий статус Story")
    parser.add_argument("--summary", default="")
    parser.add_argument(
        "--child",
        action="append",
        default=[],
        help="Дочерняя задача KEY:STATUS или KEY:TYPE:STATUS (можно несколько)",
    )
    parser.add_argument(
        "--json",
        help="JSON файл/строка с payload Story (MCP get/search) и/или children/issues",
    )
    parser.add_argument(
        "--transitions",
        help="JSON файл или строка со списком transitions (только issue-plan)",
    )


def _story_and_children(args: argparse.Namespace) -> tuple[JiraIssue, list[JiraIssue]]:
    payload = _load_json_arg(args.json) if args.json else None
    story: JiraIssue | None = None
    children: list[JiraIssue] = []
    if isinstance(payload, dict):
        story_payload = payload.get("story") or payload.get("issue") or payload
        if isinstance(story_payload, dict) and (
            story_payload.get("key")
            or story_payload.get("issueKey")
            or story_payload.get("issue_key")
            or (isinstance(story_payload.get("fields"), dict))
        ):
            story = JiraIssue.from_mcp(story_payload)
            children.extend(children_from_issue(story_payload))
        children.extend(issues_from_search(payload.get("children") or payload.get("issues") or []))
    elif isinstance(payload, list):
        children.extend(issues_from_search(payload))

    if story is None:
        story = JiraIssue(
            key=args.issue,
            summary=args.summary or args.issue,
            issue_type="Story",
            status=args.story_status or "",
        )
    elif args.story_status:
        story = JiraIssue(
            key=story.key or args.issue,
            summary=story.summary or args.summary or args.issue,
            description=story.description,
            issue_type=story.issue_type or "Story",
            status=args.story_status,
            labels=story.labels,
            parent_key=story.parent_key,
            url=story.url,
            raw=story.raw,
        )

    for token in args.child:
        children.append(parse_child_token(token))

    if story.key != args.issue and args.issue:
        story = JiraIssue(
            key=args.issue,
            summary=story.summary,
            description=story.description,
            issue_type=story.issue_type,
            status=story.status,
            labels=story.labels,
            parent_key=story.parent_key,
            url=story.url,
            raw=story.raw,
        )
    return story, children


def _load_json_arg(value: str) -> Any:
    path = Path(value)
    raw = path.read_text(encoding="utf-8") if path.is_file() else value
    return json.loads(raw)


if __name__ == "__main__":
    raise SystemExit(main())
