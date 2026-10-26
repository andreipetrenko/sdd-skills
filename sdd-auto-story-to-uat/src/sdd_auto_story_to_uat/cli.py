from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sdd_auto_story_to_uat.evaluate import (
    evaluate_story,
    extract_release_number,
    parse_pr_token,
)
from sdd_auto_story_to_uat.mcp import (
    BITBUCKET_TOOL_ALIASES,
    JIRA_TOOL_ALIASES,
    match_transition,
    parse_transitions,
)
from sdd_auto_story_to_uat.models import (
    JiraIssue,
    issues_from_search,
    pull_requests_from_payload,
    stories_from_issue,
)
from sdd_auto_story_to_uat.plan import build_issue_plan, build_plan
from sdd_auto_story_to_uat.settings import SettingsError, find_settings_file, load_settings
from sdd_auto_story_to_uat.storage import find_storage_file, record_output


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "mcp-aliases":
        print(
            json.dumps(
                {"jira": JIRA_TOOL_ALIASES, "bitbucket": BITBUCKET_TOOL_ALIASES},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    try:
        settings_path = find_settings_file(args.settings)
        settings = load_settings(settings_path)
    except SettingsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    storage_path = find_storage_file(
        args.storage, settings_path=settings.path, create=bool(args.storage)
    )

    try:
        if args.command == "plan":
            plan = build_plan(settings)
            record_output(storage_path, "plan", plan)
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return 0
        if args.command == "jql":
            jql = settings.source.jql()
            record_output(storage_path, "jql", jql)
            print(jql)
            return 0
        if args.command == "stories-jql":
            jql = settings.stories_jql(args.release, args.release_number or settings.release.number or "")
            record_output(storage_path, "stories-jql", jql)
            print(jql)
            return 0
        if args.command == "children-jql":
            jql = settings.children_jql(args.issue)
            record_output(storage_path, "children-jql", jql)
            print(jql)
            return 0
        if args.command == "release-number":
            release = _release_from_args(args)
            number = extract_release_number(settings, release, explicit=args.release_number)
            record_output(storage_path, "release-number", number)
            print(number)
            return 0
        if args.command == "issue-plan":
            release, story, prs, child_keys = _eval_inputs(args)
            transitions = _load_json_arg(args.transitions) if args.transitions else None
            number = extract_release_number(settings, release, explicit=args.release_number)
            plan = build_issue_plan(
                settings,
                release,
                story,
                prs,
                release_number=number,
                child_keys=child_keys,
                transitions=transitions,
            )
            record_output(storage_path, "issue-plan", plan)
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return 0
        if args.command == "evaluate":
            release, story, prs, child_keys = _eval_inputs(args)
            number = extract_release_number(settings, release, explicit=args.release_number)
            result = evaluate_story(
                settings,
                story,
                prs,
                release_number=number,
                release_key=release.key or None,
                child_keys=child_keys,
            )
            payload = result.to_dict()
            record_output(storage_path, "evaluate", payload)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if args.command == "match-transition":
            raw = _load_json_arg(args.transitions) if args.transitions else args.name
            matched = match_transition(parse_transitions(raw), settings.target.statuses)
            payload = {"matched": matched}
            record_output(storage_path, "match-transition", payload)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0 if matched else 1
        parser.print_help()
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdd-auto-story-to-uat",
        description=(
            "Локальные хелперы скилла: JQL релиза и Story, номер релиза, "
            "оценка PR и переход. Запись в Jira/Bitbucket — только через MCP."
        ),
    )
    parser.add_argument("--settings", help="Path to shared settings.yaml")
    parser.add_argument("--storage", help="Path to shared storage.yaml")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("plan", help="Печатает план MCP-конвейера из settings.yaml")
    sub.add_parser("jql", help="Печатает JQL поиска release-задачи (пункт 1)")

    stories = sub.add_parser("stories-jql", help="Печатает JQL Story под релизом")
    stories.add_argument("release", help="Ключ release-задачи")
    stories.add_argument("--release-number", default="", help="Номер релиза для jql_pattern")

    children = sub.add_parser("children-jql", help="Печатает JQL дочерних Task/Sub-task Story")
    children.add_argument("issue", help="Ключ Story")

    number = sub.add_parser("release-number", help="Извлекает номер релиза из задачи или настроек")
    number.add_argument("release", nargs="?", default="", help="Ключ release-задачи")
    number.add_argument("--summary", default="")
    number.add_argument("--release-number", default="")
    number.add_argument("--json", help="JSON payload release-задачи (MCP get)")

    issue = sub.add_parser("issue-plan", help="План по одной Story релиза")
    _add_eval_args(issue)

    evaluate = sub.add_parser(
        "evaluate",
        help="Решает, нужно ли переводить Story, по PR и номеру релиза",
    )
    _add_eval_args(evaluate)

    match = sub.add_parser(
        "match-transition",
        help="Выбирает переход Jira по имени/назначению из target.statuses",
    )
    match.add_argument("--name", action="append", default=[], help="Имя перехода")
    match.add_argument("--transitions", help="JSON файл или строка со списком transitions")

    sub.add_parser("mcp-aliases", help="Печатает алиасы Jira и Bitbucket MCP")
    return parser


def _add_eval_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("issue", help="Ключ Story")
    parser.add_argument("--release", default="", help="Ключ release-задачи")
    parser.add_argument("--release-number", default="")
    parser.add_argument("--release-summary", default="")
    parser.add_argument("--story-status", default="")
    parser.add_argument("--summary", default="")
    parser.add_argument(
        "--child",
        action="append",
        default=[],
        help="Ключ дочерней задачи, чтобы искать PR по нему",
    )
    parser.add_argument(
        "--pr",
        action="append",
        default=[],
        help="PR: STATE:DEST или SOURCE:STATE:DEST (можно несколько)",
    )
    parser.add_argument("--json", help="JSON файл/строка с release/story/prs")
    parser.add_argument("--transitions", help="JSON transitions (только issue-plan)")


def _eval_inputs(args: argparse.Namespace) -> tuple[JiraIssue, JiraIssue, list, list[str]]:
    payload = _load_json_arg(args.json) if args.json else None
    release = JiraIssue(
        key=args.release or "",
        summary=args.release_summary or args.release or "",
        issue_type="Task",
    )
    story = JiraIssue(
        key=args.issue,
        summary=args.summary or args.issue,
        issue_type="Story",
        status=args.story_status or "",
    )
    prs = []
    child_keys = list(args.child)
    if isinstance(payload, dict):
        if payload.get("release") or payload.get("release_issue"):
            release = JiraIssue.from_mcp(payload.get("release") or payload["release_issue"])
        if payload.get("story") or payload.get("issue"):
            story = JiraIssue.from_mcp(payload.get("story") or payload["issue"])
        prs.extend(pull_requests_from_payload(payload.get("prs") or payload.get("pull_requests") or []))
        child_keys.extend(str(item) for item in (payload.get("child_keys") or []))
        child_keys.extend(item.key for item in issues_from_search(payload.get("children") or []))
        child_keys.extend(
            item.key
            for item in stories_from_issue(payload.get("story") or payload.get("issue") or {})
        )
    elif isinstance(payload, list):
        prs.extend(pull_requests_from_payload(payload))
    if args.story_status:
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
    if args.issue and story.key != args.issue:
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
    for token in args.pr:
        prs.append(parse_pr_token(token))
    return release, story, prs, list(dict.fromkeys(child_keys))


def _release_from_args(args: argparse.Namespace) -> JiraIssue:
    if args.json:
        payload = _load_json_arg(args.json)
        if isinstance(payload, dict):
            raw = payload.get("release") or payload.get("issue") or payload
            if isinstance(raw, dict):
                issue = JiraIssue.from_mcp(raw)
                if args.release and not issue.key:
                    return JiraIssue(
                        key=args.release,
                        summary=issue.summary or args.summary,
                        description=issue.description,
                        issue_type=issue.issue_type,
                        status=issue.status,
                        labels=issue.labels,
                        raw=issue.raw,
                    )
                return issue
    return JiraIssue(
        key=args.release or "",
        summary=args.summary or args.release or "",
        issue_type="Task",
    )


def _load_json_arg(value: str) -> Any:
    path = Path(value)
    raw = path.read_text(encoding="utf-8") if path.is_file() else value
    return json.loads(raw)


if __name__ == "__main__":
    raise SystemExit(main())
