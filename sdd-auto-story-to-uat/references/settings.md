# settings.yaml

Путь по умолчанию: `settings.yaml` в корне репозитория. Переопределение: `--settings PATH`.

Токены и URL MCP в YAML не клади. Jira и Bitbucket ходят через уже подключённые MCP.

## Поиск release-задачи (`source`) — пункт 1

Тот же паттерн фильтра, что у других скиллов каталога.

| Поле | Смысл |
| --- | --- |
| `project` / `space` | Пространство Jira |
| `issue_type` / `type` | Тип, например `Task` |
| `label` | Метка |
| `status` | Статус поиска |

Ключ `release_task:` принимается как синоним `source:`.

## Story релиза (`stories`) — пункт 3

| Поле | Смысл |
| --- | --- |
| `issue_type` / `type` | По умолчанию `Story` |
| `via` | `parent`, `linked` или `both` (по умолчанию) |
| `link_type` | Второй аргумент `linkedIssues` |
| `project` / `label` / `status` | Доп. фильтры Story |
| `jql_pattern` | Полный JQL с `{release_key}` и `{release_number}` |

JQL по умолчанию: `(parent = "REL-12" OR issue in linkedIssues("REL-12")) AND issuetype = "Story"`.

## Номер и ветка (`release`) — пункты 2 и 5

| Поле | Смысл |
| --- | --- |
| `number` / `release_number` | Явный номер |
| `number_field` | Поле Jira (`fixVersions`, custom field) |
| `number_pattern` | Regex, по умолчанию `(\d+(?:\.\d+)*)` |
| `branch_pattern` / `branch_patterns` | По умолчанию `release/{number}` |

Если `number` пуст: `number_field` → `fixVersions` → regex по summary / key / labels.

Ветка подходит, если совпадает с паттерном или после префикса (`release/`) идёт номер (`release/1.2`, `release/1.2.0` для `1.2`).

## Репозитории (`bitbucket`) — пункт 4

- `repository` — обязателен
- `repositories` — дополнительные репы
- `workspace` / `repo_slug` / `project` — переопределение разбора URL

Ключ `git:` принимается как синоним `bitbucket:`.

## PR (`pr`) — пункты 4–5

| Поле | Смысл | По умолчанию |
| --- | --- | --- |
| `include_child_keys` | Искать PR по ключам Task/Sub-task Story | `true` |
| `merged_states` | Считается влитым | `MERGED`, `merged` |
| `ignore_states` | Не учитывать | `DECLINED`, `SUPERSEDED` |
| `ignore_destination_prefixes` | Не учитывать внутренние PR SDD | `feature/`, `task/` |

## Целевой статус (`target`) — пункт 6

`statuses`: `Ready for UAT`.

Синонимы: `story.target`, `story.target_status`.

## Лимиты (`limits`)

`max_issues`, `max_stories`, `max_children`, `max_prs`.
