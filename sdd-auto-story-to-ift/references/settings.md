# settings.yaml

Общий файл оркестратора `sdd-auto-impr-to-release`. Этот скилл читает верхний уровень и секцию `sdd-auto-story-to-ift` (`source`, `children`, `target`). Переопределение: `--settings PATH`. `--storage` — общий `storage.yaml`.

Токены и URL MCP в YAML не клади. Jira ходит через уже подключённый MCP.

## Поиск Story (`source`) — пункт 1

Тот же паттерн фильтра, что у `sdd-auto-impr-to-story`.

| Поле | Смысл |
| --- | --- |
| `project` / `space` | Пространство Jira |
| `issue_type` / `type` | Тип, например `Story` |
| `label` | Метка |
| `status` | Статус поиска Story (текущий, не целевой) |

## Дочерние задачи (`children`) — пункты 2–3

| Поле | Смысл |
| --- | --- |
| `issue_type` / `issue_types` / `type` | Типы детей. Строка, список или CSV. По умолчанию `Task`, `Sub-task`, `Subtask` |
| `ready` / `ready_status` / `ready_statuses` / `status` | Статус «ребёнок готов». По умолчанию `Готов` |

JQL детей: `parent = "{STORY-KEY}" AND issuetype in (...)`.

## Целевой статус Story (`target`) — пункт 4

`statuses`: `Ready for IFT`.

Ключи-синонимы: `story.target`, `story.target_status`, `story.target_statuses`. Строка, список или `{statuses: [...]}` / `{status: "..."}`.

## Лимиты (`limits`)

- `max_issues` — сколько Story за один `search` (по умолчанию 20)
- `max_children` — сколько детей у одной Story (по умолчанию 100)
