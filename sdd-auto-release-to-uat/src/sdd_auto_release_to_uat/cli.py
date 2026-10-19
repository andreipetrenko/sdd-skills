from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sdd_auto_release_to_uat.evaluate import evaluate_release, parse_story_token
from sdd_auto_release_to_uat.mcp import JIRA_TOOL_ALIASES, match_transition, parse_transitions
from sdd_auto_release_to_uat.models import JiraIssue, issues_from_search, stories_from_issue
from sdd_auto_release_to_uat.plan import build_issue_plan, build_plan
from sdd_auto_release_to_uat.settings import SettingsError, find_settings_file, load_settings


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
        if args.command == "stories-jql":
            print(settings.stories_jql(args.release))
            return 0
        if args.command == "issue-plan":
            release, stories = _release_and_stories(args)
            transitions = _load_json_arg(args.transitions) if args.transitions else None
            print(
                json.dumps(
                    build_issue_plan(settings, release, stories, transitions=transitions),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.command == "evaluate":
            release, stories = _release_and_stories(args)
            result = evaluate_release(settings, release, stories)
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
        prog="sdd-auto-release-to-uat",
        description=(
            "Локальные хелперы скилла: JQL релиза и Story, план и оценка перехода. "
            "Запись в Jira — только через MCP."
        ),
    )
    parser.add_argument("--settings", help="Path to settings.yaml")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("plan", help="Печатает план MCP-конвейера из settings.yaml")
    sub.add_parser("jql", help="Печатает JQL поиска release Epic/задачи (пункт 1)")

    stories = sub.add_parser("stories-jql", help="Печатает JQL Story под релизом")
    stories.add_argument("release", help="Ключ Epic/задачи релиза")

    issue = sub.add_parser("issue-plan", help="План по одному релизу: JQL Story, оценка, MCP")
    _add_eval_args(issue)

    evaluate = sub.add_parser(
        "evaluate",
        help="Решает, нужно ли переводить Epic/задачу, по статусам Story",
    )
    _add_eval_args(evaluate)

    match = sub.add_parser(
        "match-transition",
        help="Выбирает переход Jira по имени/назначению из target.statuses",
    )
    match.add_argument("--name", action="append", default=[], help="Имя перехода")
    match.add_argument("--transitions", help="JSON файл или строка со списком transitions")

    sub.add_parser("mcp-aliases", help="Печатает алиасы Jira MCP")
    return parser


def _add_eval_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("release", help="Ключ Epic/задачи релиза")
    parser.add_argument("--release-status", default="", help="Текущий статус релиза")
    parser.add_argument("--summary", default="")
    parser.add_argument(
        "--story",
        action="append",
        default=[],
        help="Story KEY:STATUS или KEY:TYPE:STATUS (можно несколько)",
    )
    parser.add_argument("--json", help="JSON файл/строка с release и stories")
    parser.add_argument("--transitions", help="JSON transitions (только issue-plan)")


def _release_and_stories(args: argparse.Namespace) -> tuple[JiraIssue, list[JiraIssue]]:
    payload = _load_json_arg(args.json) if args.json else None
    release: JiraIssue | None = None
    stories: list[JiraIssue] = []
    if isinstance(payload, dict):
        release_payload = payload.get("release") or payload.get("epic") or payload.get("issue")
        if isinstance(release_payload, dict):
            release = JiraIssue.from_mcp(release_payload)
            stories.extend(stories_from_issue(release_payload))
        elif payload.get("key") or payload.get("issueKey") or isinstance(payload.get("fields"), dict):
            release = JiraIssue.from_mcp(payload)
            stories.extend(stories_from_issue(payload))
        stories.extend(issues_from_search(payload.get("stories") or payload.get("issues") or []))
    elif isinstance(payload, list):
        stories.extend(issues_from_search(payload))

    if release is None:
        release = JiraIssue(
            key=args.release,
            summary=args.summary or args.release,
            issue_type="Epic",
            status=args.release_status or "",
        )
    elif args.release_status:
        release = JiraIssue(
            key=release.key or args.release,
            summary=release.summary or args.summary or args.release,
            description=release.description,
            issue_type=release.issue_type or "Epic",
            status=args.release_status,
            labels=release.labels,
            parent_key=release.parent_key,
            url=release.url,
            raw=release.raw,
        )

    for token in args.story:
        stories.append(parse_story_token(token))

    if args.release and release.key != args.release:
        release = JiraIssue(
            key=args.release,
            summary=release.summary,
            description=release.description,
            issue_type=release.issue_type,
            status=release.status,
            labels=release.labels,
            parent_key=release.parent_key,
            url=release.url,
            raw=release.raw,
        )
    return release, stories


def _load_json_arg(value: str) -> Any:
    path = Path(value)
    raw = path.read_text(encoding="utf-8") if path.is_file() else value
    return json.loads(raw)


if __name__ == "__main__":
    raise SystemExit(main())
