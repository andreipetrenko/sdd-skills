from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sdd_auto_impr_to_story.models import JiraIssue
from sdd_auto_impr_to_story.openspec import (
    change_dir,
    openspec_available,
    scaffold_change,
    scaffold_implementation_change,
    try_openspec_cli,
    validate_change,
)
from sdd_auto_impr_to_story.mcp import BITBUCKET_TOOL_ALIASES, JIRA_TOOL_ALIASES
from sdd_auto_impr_to_story.plan import build_issue_plan, build_plan
from sdd_auto_impr_to_story.settings import SettingsError, find_settings_file, load_settings


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "mcp-aliases":
        print(
            json.dumps(
                {
                    "jira": JIRA_TOOL_ALIASES,
                    "bitbucket": BITBUCKET_TOOL_ALIASES,
                },
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

    try:
        if args.command == "plan":
            print(json.dumps(build_plan(settings), ensure_ascii=False, indent=2))
            return 0
        if args.command == "jql":
            print(settings.source.jql())
            return 0
        if args.command == "issue-plan":
            source = JiraIssue(
                key=args.issue,
                summary=args.summary or args.issue,
                description=args.description or "",
                issue_type=settings.source.issue_type,
                status=settings.source.status or "",
                components=tuple(args.component) if args.component else (),
            )
            print(
                json.dumps(
                    build_issue_plan(
                        settings, source, story_key=args.story, task_key=args.task
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.command == "scaffold-specs":
            return _cmd_scaffold_specs(settings, args)
        if args.command == "scaffold-impl-spec":
            return _cmd_scaffold_impl_spec(settings, args)
        if args.command == "validate-specs":
            return _cmd_validate_specs(settings, args)
        parser.print_help()
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdd-auto-impr-to-story",
        description=(
            "Local helpers for the GigaCode skill: read settings.yaml, print JQL/plan, "
            "scaffold and validate OpenSpec BR/FR. Jira and Bitbucket writes go through MCP."
        ),
    )
    parser.add_argument("--settings", help="Path to settings.yaml")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("plan", help="Print the MCP workflow plan from settings.yaml")
    sub.add_parser("jql", help="Print JQL for source issues (пункт 1)")

    issue = sub.add_parser("issue-plan", help="Print payloads for one source issue")
    issue.add_argument("issue", help="Source Jira key")
    issue.add_argument("--summary", default="")
    issue.add_argument("--description", default="")
    issue.add_argument("--story", help="Already created story key")
    issue.add_argument("--task", help="Related/component task key")
    issue.add_argument("--component", action="append", default=[])

    scaffold = sub.add_parser("scaffold-specs", help="Write OpenSpec BR/FR stubs into a working tree")
    scaffold.add_argument("issue", help="Source Jira key")
    scaffold.add_argument("--summary", default="")
    scaffold.add_argument("--description", default="")
    scaffold.add_argument("--story", help="Story key")
    scaffold.add_argument("--repo", help="Path to the git working tree")

    impl = sub.add_parser(
        "scaffold-impl-spec",
        help="Write OpenSpec code-change spec stubs for the component task",
    )
    impl.add_argument("task", help="Component task Jira key")
    impl.add_argument("--issue", required=True, help="Source Jira key")
    impl.add_argument("--story", required=True, help="Story key")
    impl.add_argument("--summary", default="")
    impl.add_argument("--description", default="")
    impl.add_argument("--component", default="")
    impl.add_argument("--repo", help="Path to the specs-repo working tree")

    validate = sub.add_parser("validate-specs", help="Validate OpenSpec artifacts for a change")
    validate.add_argument("issue", help="Source Jira key or, with --task, ignored for change id")
    validate.add_argument("--task", help="Validate implementation change id from task key")
    validate.add_argument("--repo", help="Path to the git working tree")

    sub.add_parser("mcp-aliases", help="Print Jira/Bitbucket MCP tool name aliases")
    return parser


def _cmd_scaffold_specs(settings, args) -> int:
    source = JiraIssue(
        key=args.issue,
        summary=args.summary or args.issue,
        description=args.description or "",
        issue_type=settings.source.issue_type,
        status=settings.source.status or "",
    )
    repo = Path(args.repo).resolve() if args.repo else Path.cwd()
    target = scaffold_change(repo, settings, source, args.story)
    change_id = settings.change_id(source.key)
    if openspec_available():
        try:
            try_openspec_cli(repo, change_id, ["validate", "--change", change_id])
        except Exception as exc:  # noqa: BLE001
            print(f"openspec validate warning: {exc}", file=sys.stderr)
    print(str(target))
    return 0


def _cmd_scaffold_impl_spec(settings, args) -> int:
    source = JiraIssue(
        key=args.issue,
        summary=args.summary or args.issue,
        description=args.description or "",
        issue_type=settings.source.issue_type,
        status=settings.source.status or "",
    )
    repo = Path(args.repo).resolve() if args.repo else Path.cwd()
    target = scaffold_implementation_change(
        repo,
        settings,
        source,
        args.story,
        args.task,
        component=args.component or None,
    )
    change_id = settings.implementation_change_id(args.task, source.key)
    if openspec_available():
        try:
            try_openspec_cli(repo, change_id, ["validate", "--change", change_id])
        except Exception as exc:  # noqa: BLE001
            print(f"openspec validate warning: {exc}", file=sys.stderr)
    print(str(target))
    return 0


def _cmd_validate_specs(settings, args) -> int:
    repo = Path(args.repo).resolve() if args.repo else Path.cwd()
    if args.task:
        change_id = settings.implementation_change_id(args.task, args.issue)
    else:
        change_id = settings.change_id(args.issue)
    errors = validate_change(change_dir(repo, change_id))
    if errors:
        print("OpenSpec validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"OpenSpec change `{change_id}` looks valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
