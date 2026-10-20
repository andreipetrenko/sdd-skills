# settings.yaml

Путь по умолчанию: `settings.yaml`. Переопределение: `--settings PATH`.

Токены в YAML не клади.

Вход скилла — **ключ release Story**, не блок `source`.

## Состав (`stories`)

Как у `sdd-auto-story-to-uat`.

| Поле | Смысл |
| --- | --- |
| `issue_type` | По умолчанию `Story` |
| `via` | `parent`, `linked` или `both` |
| `link_type` | Второй аргумент `linkedIssues` |
| `jql_pattern` | Полный JQL с `{release_key}` / `{release_number}` |

## Номер и ветка (`release`)

Как у `sdd-auto-story-to-uat`.

| Поле | Смысл | По умолчанию |
| --- | --- | --- |
| `number` | Явный номер | из fixVersion / summary |
| `number_field` | Поле Jira | — |
| `number_pattern` | Regex | `(\d+(?:\.\d+)*)` |
| `branch_pattern` | Имя ветки | `release/{number}` |

## Компоненты и репы

Как у `sdd-auto-impr-to-story`: Jira Component + `component.repository`.

| Поле | Смысл |
| --- | --- |
| `components[].name` | Имя Jira Component |
| `components[].repository` | Репа Bitbucket |
| `components[].default_branch` | Старт release-ветки, по умолчанию `master` |
| `components[].story_branch_pattern` | Head PR, по умолчанию `feature/{key}` |
| `component` | Один компонент, тот же набор полей |
| `related.component` | Fallback имени, если у Story нет Component |

Репа без имени и без `related.component` — ошибка settings: сопоставить Component нечем. Список `bitbucket.repositories` без имён **не** используется как «все репы для всех компонентов».
