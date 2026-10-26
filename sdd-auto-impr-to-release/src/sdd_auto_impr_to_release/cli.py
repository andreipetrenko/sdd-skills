from __future__ import annotations

import json
import sys
from pathlib import Path

from sdd_auto_impr_to_release.loop import build_plan, run_loop, run_once
from sdd_auto_impr_to_release.settings import SettingsError, find_settings_file, load_settings
from sdd_auto_impr_to_release.storage import find_storage_file, load_storage


SKILL_DIR = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
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
        storage_path = find_storage_file(
            args.storage,
            settings_path=settings.path,
            create=True,
        )
        if storage_path is None:
            raise SettingsError("storage.yaml not found. Pass --storage or set storage.path.")
        if args.command == "storage":
            print(
                json.dumps(
                    {
                        "path": str(storage_path),
                        "data": load_storage(storage_path, create=True),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.command == "once":
            result = run_once(
                settings,
                storage_path=storage_path,
                start=SKILL_DIR,
                skill_command=args.skill_command,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return _iteration_exit(result)
        if args.command == "loop":
            run_loop(
                settings,
                storage_path=storage_path,
                start=SKILL_DIR,
                skill_command=args.skill_command,
            )
            return 0
        parser.print_help()
        return 2
    except KeyboardInterrupt:
        return 130
    except SettingsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="sdd-auto-impr-to-release",
        description=(
            "Оркестратор атомарных скиллов каталога: общий settings.yaml и storage.yaml. "
            "В цикле запускает существующие scripts/run.py. "
            "Запись в Jira/Bitbucket — только внутри атомарных скиллов через MCP."
        ),
    )
    parser.add_argument("--settings", help="Path to shared settings.yaml")
    parser.add_argument("--storage", help="Path to shared storage.yaml")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("plan", help="Печатает порядок атомарных скиллов и пути settings/storage")
    sub.add_parser("storage", help="Печатает текущий shared storage.yaml")

    once = sub.add_parser("once", help="Одна итерация: атомарные скиллы по порядку каталога")
    once.add_argument(
        "--skill-command",
        default="plan",
        help="Команда существующего атомарного CLI (по умолчанию plan)",
    )

    loop = sub.add_parser(
        "loop",
        help="Повторяет once без условия остановки и без расписания (Ctrl+C)",
    )
    loop.add_argument(
        "--skill-command",
        default="plan",
        help="Команда существующего атомарного CLI (по умолчанию plan)",
    )
    return parser


def _iteration_exit(result: dict) -> int:
    for item in result.get("iteration") or []:
        if item.get("exit_code"):
            return int(item["exit_code"])
    return 0
