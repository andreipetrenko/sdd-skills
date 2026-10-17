# Jira и Bitbucket MCP

Серверы уже настроены на агенте GigaCode. Этот skill только выбирает инструмент по алиасу и передаёт поля из `settings.yaml` / `plan` / `evaluate`.

## Запрещено

- REST `curl` / `requests` к Jira и Bitbucket
- спрашивать `JIRA_TOKEN`, `BITBUCKET_TOKEN`
- GitHub / GitLab / GitVerse API
- подставлять выдуманные project key, workspace, slug, номер релиза

## Как выбрать tool

1. Возьми список MCP tools текущей сессии.
2. Для action из таблиц ниже используй **первое** имя, которое реально есть.
3. Алиасы также печатает `python .../scripts/run.py mcp-aliases`.

## Jira

| Action | Алиасы (по приоритету) | Зачем |
| --- | --- | --- |
| `search` | `searchJiraIssuesUsingJql`, `jira_search`, `search_issues`, `jira_search_issues` | release-задачи, Story релиза, дети Story |
| `get` | `getJiraIssue`, `jira_get_issue`, `get_issue` | номер релиза, issuelinks / subtasks |
| `transitions` | `getTransitionsForJiraIssue`, `listJiraIssueTransitions`, `jira_get_transitions` | пункт 6 |
| `transition` | `transitionJiraIssue`, `jira_transition_issue`, `transition_issue` | пункт 6 |

`search`: `jql` + `maxResults`. Не меняй JQL из CLI.

`transition`: id перехода, у которого имя **или** статус назначения совпало с `target.statuses` без учёта регистра.

## Bitbucket

| Action | Алиасы | Зачем |
| --- | --- | --- |
| `list_prs` | `listBitbucketRepoPullRequests`, `list_pull_requests`, `listPullRequests` | пункт 4 |
| `get_pr` | `getBitbucketRepoPullRequest`, `get_pull_request`, `getPullRequest` | state / destination, если список урезан |

Идентификатор репозитория — из `plan.bitbucket`:

- Cloud: `workspace` + `repo_slug`
- Server/DC: `project` + `repo_slug`

PR принадлежит Story, если ключ Story (или ребёнка) есть в title / source / destination / description.

Учтённый PR готов, если `state` ∈ `MERGED` и destination — release-ветка с номером релиза.
