from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sdd_auto_story_to_release.compose import compose, extract_release_number, parse_story_token
from sdd_auto_story_to_release.mcp import BITBUCKET_TOOL_ALIASES, JIRA_TOOL_ALIASES
from sdd_auto_story_to_release.models import JiraIssue, issues_from_search, stories_from_issue
from sdd_auto_story_to_release.plan import build_issue_plan, build_plan
from sdd_auto_story_to_release.settings import SettingsError, find_settings_file, load_settings
from sdd_auto_story_to_release.storage import find_storage_file, get_section, load_storage, record_output


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
    if hasattr(args, "release") and not args.release:
        args.release = _stored_release_key(storage_path)

    try:
        if args.command == "plan":
            plan = build_plan(settings)
            record_output(storage_path, "plan", plan)
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return 0
        if args.command in {"stories-jql", "compose", "issue-plan"} and not args.release:
            print(
                "error: release Story key required "
                "(CLI argument or storage.sdd-auto-story-to-release.release_key)",
                file=sys.stderr,
            )
            return 2
        if args.command == "stories-jql":
            jql = settings.stories_jql(args.release, args.release_number or settings.release.number or "")
            record_output(storage_path, "stories-jql", jql)
            print(jql)
            return 0
        if args.command == "release-number":
            release = _release_from_args(args)
            number = extract_release_number(settings, release, explicit=args.release_number)
            record_output(storage_path, "release-number", number)
            print(number)
            return 0
        if args.command == "compose":
            release, stories = _release_and_stories(args)
            result = compose(
                settings, release, stories, release_number=args.release_number or None
            )
            payload = result.to_dict()
            extra = {"release_key": release.key} if release.key else None
            record_output(storage_path, "compose", payload, extra=extra)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if args.command == "issue-plan":
            release, stories = _release_and_stories(args)
            plan = build_issue_plan(
                settings,
                release,
                stories,
                release_number=args.release_number or None,
            )
            extra = {"release_key": release.key} if release.key else None
            record_output(storage_path, "issue-plan", plan, extra=extra)
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return 0
        parser.print_help()
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdd-auto-story-to-release",
        description=(
            "Локальные хелперы скилла: состав release Story, номер релиза, "
            "план веток и PR. Запись в Jira/Bitbucket — только через MCP."
        ),
    )
    parser.add_argument("--settings", help="Path to shared settings.yaml")
    parser.add_argument("--storage", help="Path to shared storage.yaml")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("plan", help="Печатает план MCP-конвейера из settings.yaml")

    stories = sub.add_parser("stories-jql", help="Печатает JQL дочерних/связанных Story")
    stories.add_argument("release", nargs="?", default="", help="Ключ release Story")
    stories.add_argument("--release-number", default="")

    number = sub.add_parser("release-number", help="Извлекает номер релиза")
    number.add_argument("release", nargs="?", default="", help="Ключ release Story")
    number.add_argument("--summary", default="")
    number.add_argument("--release-number", default="")
    number.add_argument("--json", help="JSON payload release Story (MCP get)")

    compose_cmd = sub.add_parser("compose", help="Состав релиза, ветки и PR по компонентам")
    _add_eval_args(compose_cmd)

    issue = sub.add_parser("issue-plan", help="План MCP по одной release Story")
    _add_eval_args(issue)

    sub.add_parser("mcp-aliases", help="Печатает алиасы Jira и Bitbucket MCP")
    return parser


def _add_eval_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("release", nargs="?", default="", help="Ключ release Story")
    parser.add_argument("--summary", default="")
    parser.add_argument("--release-number", default="")
    parser.add_argument(
        "--story",
        action="append",
        default=[],
        help="Story состава KEY:COMPONENT или KEY:TYPE:COMPONENT",
    )
    parser.add_argument("--json", help="JSON файл/строка с release и stories")


def _release_and_stories(args: argparse.Namespace) -> tuple[JiraIssue, list[JiraIssue]]:
    payload = _load_json_arg(args.json) if args.json else None
    release = JiraIssue(
        key=args.release,
        summary=args.summary or args.release,
        issue_type="Story",
    )
    stories: list[JiraIssue] = []
    if isinstance(payload, dict):
        raw_release = payload.get("release") or payload.get("issue") or payload
        if isinstance(raw_release, dict) and (
            raw_release.get("key")
            or raw_release.get("issueKey")
            or isinstance(raw_release.get("fields"), dict)
        ):
            release = JiraIssue.from_mcp(raw_release)
            stories.extend(stories_from_issue(raw_release))
        stories.extend(issues_from_search(payload.get("stories") or payload.get("issues") or []))
    elif isinstance(payload, list):
        stories.extend(issues_from_search(payload))
    if args.release and release.key != args.release:
        release = JiraIssue(
            key=args.release,
            summary=release.summary or args.summary or args.release,
            description=release.description,
            issue_type=release.issue_type or "Story",
            status=release.status,
            labels=release.labels,
            components=release.components,
            parent_key=release.parent_key,
            url=release.url,
            raw=release.raw,
        )
    for token in args.story:
        stories.append(parse_story_token(token))
    return release, stories


def _release_from_args(args: argparse.Namespace) -> JiraIssue:
    if args.json:
        payload = _load_json_arg(args.json)
        if isinstance(payload, dict):
            raw = payload.get("release") or payload.get("issue") or payload
            if isinstance(raw, dict):
                return JiraIssue.from_mcp(raw)
    return JiraIssue(
        key=args.release or "",
        summary=args.summary or args.release or "",
        issue_type="Story",
    )


def _stored_release_key(storage_path: Path | None) -> str:
    if storage_path is None or not Path(storage_path).is_file():
        return ""
    try:
        section = get_section(load_storage(storage_path))
    except SettingsError:
        return ""
    return str(section.get("release_key") or "")


def _load_json_arg(value: str) -> Any:
    path = Path(value)
    raw = path.read_text(encoding="utf-8") if path.is_file() else value
    return json.loads(raw)


if __name__ == "__main__":
    raise SystemExit(main())
