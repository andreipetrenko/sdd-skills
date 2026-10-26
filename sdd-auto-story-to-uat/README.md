# sdd-auto-story-to-uat

Skill для [GigaCode](https://gitverse.ru/docs/ai/ai-assistant-gigacode/gigacode-for-vscode/skills): переводит Story релиза в `Ready for UAT`, когда все её учтённые PR влиты в release-ветку с номером релиза.

Исходный запрос для новой сессии: [`PROMPT.md`](PROMPT.md).

Jira и Bitbucket уже должны быть подключены к агенту как MCP. Skill не ходит в REST и не хранит токены.

Настройки — общий `settings.yaml` оркестратора `sdd-auto-impr-to-release` (секция `sdd-auto-story-to-uat`). Обмен с другими скиллами — `storage.yaml` (`--storage`).

1. Ищет release-задачу по пространству, типу, метке и статусу из `settings.yaml`
2. Извлекает номер релиза (`release.number`, fixVersion или summary)
3. Находит Story этого релиза (`parent` и/или `linkedIssues`)
4. Для каждой Story собирает PR Bitbucket, которые упоминают ключ Story (и её детей)
5. Если **все** учтённые PR в статусе MERGED и destination — `release/<номер>` — переводит эту Story в `Ready for UAT`
6. Переводит готовые Story сразу, не дожидаясь всего релиза

## Быстрый старт

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp settings.example.yaml settings.yaml
```

Заполните `settings.yaml`. Секреты не нужны: агент GigaCode вызывает уже настроенные MCP Jira и Bitbucket.

```bash
python -m sdd_auto_story_to_uat --settings settings.yaml jql
python -m sdd_auto_story_to_uat --settings settings.yaml plan
python -m sdd_auto_story_to_uat --settings settings.yaml stories-jql REL-12
python -m sdd_auto_story_to_uat --settings settings.yaml evaluate DEV-40 \
  --release REL-12 --release-number 1.2 --pr feature/DEV-40:MERGED:release/1.2
```

То же через обёртку skill:

```bash
python scripts/run.py --settings settings.yaml plan
```

## GigaCode skill

Скопируйте папку в `.gigacode/skills/sdd-auto-story-to-uat/` целевого проекта. В агенте вызовите `/sdd-auto-story-to-uat`.

## settings.yaml

| Блок | Этап | Поля |
| --- | --- | --- |
| `source` | 1 | `project`, `issue_type`, `label`, `status` — фильтр release-задачи |
| `stories` | 3 | `issue_type`, `via`, `link_type`, `status` |
| `release` | 2, 5 | `number`, `number_field`, `branch_pattern` |
| `bitbucket` | 4 | `repository` / `repositories` |
| `pr` | 4–5 | `include_child_keys`, `ignore_destination_prefixes` |
| `target` | 6 | `statuses` — по умолчанию `Ready for UAT` |

Полный пример — `settings.example.yaml`. Разбор полей — `references/settings.md`.

## Тесты

```bash
python -m pytest
```
