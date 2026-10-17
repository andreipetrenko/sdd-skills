# Jira MCP

Сервер уже настроен на агенте GigaCode. Этот skill только выбирает инструмент по алиасу и передаёт поля из `settings.yaml` / `plan` / `evaluate`.

## Запрещено

- REST `curl` / `requests` к Jira
- спрашивать `JIRA_TOKEN`
- GitHub / GitLab / GitVerse / Bitbucket API
- подставлять выдуманные project key

## Как выбрать tool

1. Возьми список MCP tools текущей сессии.
2. Для action из таблицы ниже используй **первое** имя, которое реально есть.
3. Алиасы также печатает `python .../scripts/run.py mcp-aliases`.

## Jira

| Action | Алиасы (по приоритету) | Зачем |
| --- | --- | --- |
| `search` | `searchJiraIssuesUsingJql`, `jira_search`, `search_issues`, `jira_search_issues` | пункт 1 (Story) и пункт 2 (дети `parent = KEY`) |
| `get` | `getJiraIssue`, `jira_get_issue`, `get_issue` | статус Story; запасной список `fields.subtasks` |
| `transitions` | `getTransitionsForJiraIssue`, `listJiraIssueTransitions`, `jira_get_transitions` | пункт 4 |
| `transition` | `transitionJiraIssue`, `jira_transition_issue`, `transition_issue` | пункт 4 |

`search`: `jql` + `maxResults`. Не меняй JQL из CLI.

`transition`: id перехода, у которого имя **или** статус назначения совпало со списком `target.statuses` без учёта регистра.

Нет совпадения среди переходов — не выдумывай id и не зови REST.
