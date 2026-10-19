# settings.yaml

Путь по умолчанию: `settings.yaml` в корне репозитория. Переопределение: `--settings PATH`.

Токены и URL MCP в YAML не клади. Jira ходит через уже подключённый MCP.

## Поиск Epic/задачи релиза (`source`) — пункт 1

Тот же паттерн фильтра, что у `sdd-auto-story-to-uat`.

| Поле | Смысл |
| --- | --- |
| `project` / `space` | Пространство Jira |
| `issue_type` / `type` | Тип, например `Epic` или `Task` |
| `label` | Метка |
| `status` | Статус поиска (текущий, не целевой) |

Ключи `release_task:` и `epic:` принимаются как синонимы `source:`.

## Story релиза (`stories`) — пункты 2–3

Тот же способ найти Story, что у `sdd-auto-story-to-uat`.

| Поле | Смысл |
| --- | --- |
| `issue_type` / `type` | По умолчанию `Story` |
| `via` | `parent`, `linked` или `both` (по умолчанию) |
| `link_type` | Второй аргумент `linkedIssues` |
| `project` / `label` / `status` | Доп. фильтры поиска. Не используй `status` как ready-проверку |
| `jql_pattern` | Полный JQL с `{release_key}` |
| `ready` / `ready_status` / `ready_statuses` | Статус «Story готова». По умолчанию `Ready for UAT` |

JQL по умолчанию: `(parent = "REL-12" OR issue in linkedIssues("REL-12")) AND issuetype = "Story"`.

## Целевой статус Epic/задачи (`target`) — пункт 4

`statuses`: `Ready for UAT`.

Синонимы: `release.target`, `release.target_status`, `epic.target_status`.

## Лимиты (`limits`)

- `max_issues` — сколько Epic/задач за один `search` (по умолчанию 20)
- `max_stories` — сколько Story у одного релиза (по умолчанию 100)
