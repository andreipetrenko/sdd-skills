# settings.yaml

Путь по умолчанию: `settings.yaml` в корне репозитория. Переопределение: `--settings PATH`.

Токены и URL MCP в YAML не клади. Jira и Bitbucket ходят через уже подключённые MCP.

## Поиск (`source`) — этап A, пункт 1

| Поле | Смысл |
| --- | --- |
| `project` / `space` | Пространство Jira |
| `issue_type` / `type` | Тип, например `Improvement` |
| `label` | Метка |
| `status` | Статус поиска |
| `done` / `done_status` | Финальный статус Improvement после merge кода (этап C7); иначе блок `improvement_done` |

## Story (`story`) — этап A, пункт 2

- `project`, `issue_type`, `label`, `status`, `link_type`, `summary_pattern`
- `done` / `done_status` — финальный статус Story после merge кода (C6)
- служебная метка `sdd-from-{SOURCE-KEY}`

## Репа спек (`bitbucket`) — этапы A и B

- `repository` — URL репозитория со спеками
- `default_branch`
- `source_branch_pattern` — ветка Improvement
- `story_branch_pattern` — ветка Story
- `task_branch_pattern` — ветка таски для спеки кода (этап B), по умолчанию `feature/{key}`

Ключ `git:` принимается как синоним `bitbucket:`.

## Таска компонента (`related`) — этап A, пункт 5 и этапы B/C

- `issue_type`, `link_type`, `component`, `component_from_source`
- `in_progress` / `in_progress_status` — статус «таска в работе» после merge спеки кода (B4)
- `done` / `done_status` — финальный статус таски после merge кода (C5)
- служебная метка `sdd-impl-{STORY-KEY}`

## Репа компонента (`component`) — этап C

Обязательно.

- `repository` — URL репозитория, где пишется код
- `default_branch` — мастер (часто `master`)
- `task_branch_pattern` — по умолчанию `task/{key}`
- `story_branch_pattern` — ветка Story в этой же репе, от того же мастера

## Improvement после BR/FR (`after_merge`) — пункт 8

`statuses`: `В работе`, `In Progress`. Ключ `done:` на верхнем уровне ещё читается как синоним `after_merge:`.

## Improvement после кода (`improvement_done`) — C7

`statuses`: `Сделан`, `Done`.

## OpenSpec

- `capabilities` — BR/FR
- `change_id_pattern` — `{source_key}`
- `implementation_capability` — по умолчанию `code-changes`
- `implementation_change_id_pattern` — `{task_key}`
