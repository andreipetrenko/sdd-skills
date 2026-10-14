# settings.yaml

Путь по умолчанию: `settings.yaml` в корне репозитория. Переопределение: `--settings PATH` или файл рядом со skill.

Токены и URL MCP в YAML не клади. Jira и Bitbucket ходят через уже подключённые MCP.

## Пункт 1 — поиск (`source`)

| Поле | Смысл |
| --- | --- |
| `project` / `space` | Пространство Jira (project key) |
| `issue_type` / `type` | Тип задачи, например `Improvement` |
| `label` | Метка |
| `status` | Статус |

JQL: `project = "…" AND issuetype = "…" AND labels = "…" AND status = "…"`.

## Пункт 2 — создаваемая задача (`story`)

Те же поля `project`, `issue_type`, `label`, `status`. Дополнительно:

- `link_type` — связь Story с исходной задачей (по умолчанию `Relates`)
- `summary_pattern` — `{source_key}`, `{source_summary}`

На Story вешается служебная метка `sdd-from-{SOURCE-KEY}` — повторный запуск не создаёт дубликат.

## Пункт 3 — репозиторий (`bitbucket`)

Ключ `git:` тоже принимается как синоним.

- `repository` — HTTPS или SSH URL Bitbucket Cloud / Server
- `workspace`, `repo_slug`, `project` — если URL нестандартный; иначе разберёт CLI `plan`
- `source_branch_pattern` — ветка с номером задачи пункта 1, по умолчанию `feature/{key}`
- `story_branch_pattern` — ветка с номером задачи пункта 2
- `default_branch` — откуда ветвятся обе feature-ветки

## Пункт 5 — связанная задача (`related`)

- `issue_type` — тип (Task, Sub-task, …)
- `link_type` — тип связи Jira (`Relates`, `Blocks`, …)
- `component` — компонент, для которого вносится изменение
- `component_from_source: true` — сначала взять Component с исходной задачи

Служебная метка: `sdd-impl-{STORY-KEY}` (или `{related.label}-{STORY-KEY}`).

## Пункт 8 — после merge (`after_merge.statuses`)

Список имён перехода/статуса исходной задачи. Первое совпадение без учёта регистра: `В работе`, `In Progress`.

Ключ `done:` в YAML ещё принимается как синоним `after_merge:`.

## Опционально

- `jira.base_url` — только чтобы собрать browse-ссылки в отчёте. Для API не используется.
- `openspec.capabilities` / `change_id_pattern`
- `limits.max_issues`
