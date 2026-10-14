# Jira и Bitbucket MCP

Серверы уже настроены на агенте GigaCode. Этот skill только выбирает инструмент по алиасу и передаёт поля из `settings.yaml` / `issue-plan`.

## Запрещено

- REST `curl` / `requests` к Jira и Bitbucket
- спрашивать `JIRA_TOKEN`, `BITBUCKET_TOKEN`, app password
- GitHub / GitLab / GitVerse API
- подставлять выдуманные project key, workspace, slug

## Как выбрать tool

1. Возьми список MCP tools текущей сессии.
2. Для action из таблиц ниже используй **первое** имя, которое реально есть.
3. Алиасы также печатает `python .../scripts/run.py mcp-aliases`.

## Jira

| Action | Алиасы (по приоритету) | Зачем |
| --- | --- | --- |
| `search` | `searchJiraIssuesUsingJql`, `jira_search`, `search_issues`, `jira_search_issues` | пункт 1, идемпотентность 2 и 5 |
| `get` | `getJiraIssue`, `jira_get_issue`, `get_issue` | описание исходной задачи |
| `create` | `createJiraIssue`, `jira_create_issue`, `create_issue` | Story и related |
| `link` | `createJiraIssueLink`, `createIssueLink`, `jira_create_issue_link`, `jira_link_issues` | связь Story↔source и related↔Story |
| `link_types` | `getIssueLinkTypes`, `listJiraIssueLinkTypes` | если `link` требует id типа связи |
| `transitions` | `getTransitionsForJiraIssue`, `listJiraIssueTransitions`, `jira_get_transitions` | статус Story (если нужен) и пункт 8 |
| `transition` | `transitionJiraIssue`, `jira_transition_issue`, `transition_issue` | пункт 8 |

Аргументы `create` мапь на схему конкретного tool:

- проект: `projectKey` / `project` / `fields.project.key` = `story_fields.project`
- тип: `issueTypeName` / `issuetype` = `story_fields.issue_type`
- `summary`, `description`
- метки: `additional_fields.labels` или `labels`
- компоненты related: `additional_fields.components: [{ "name": "<component>" }]`

`search`: `jql` + `maxResults`. Не меняй JQL из CLI.

`link`: inward/outward ключи и `type` = `link_type` из settings. Если tool хочет id типа — сначала `link_types`.

`transition`: id перехода, у которого имя совпало со списком из настроек без учёта регистра (`after_merge`, `related.in_progress`, `related.done`, `story.done`, `improvement_done`).

## Bitbucket

| Action | Алиасы | Зачем |
| --- | --- | --- |
| `create_branch` | `createBitbucketRepoBranch`, `create_branch`, `createBranch`, `bitbucket_create_branch` | пункты 3 и 6 |
| `get_branch` | `getBitbucketRepoBranch`, `list_branches`, `listBitbucketRepoBranches` | не плодить ветки |
| `create_pr` | `createBitbucketRepoPullRequest`, `create_pull_request`, `createPullRequest` | пункт 7 |
| `list_prs` | `listBitbucketRepoPullRequests`, `list_pull_requests` | идемпотентность PR |
| `get_pr` | `getBitbucketRepoPullRequest`, `get_pull_request` | пункт 8 (merged?) |

Идентификатор репозитория — из `plan.bitbucket`:

- Cloud: `workspace` + `repo_slug`
- Server/DC: `project` + `repo_slug` (в URL `/projects/{key}/repos/{slug}`)

`create_branch`:

- `name` = `feature/{KEY}` или `task/{KEY}` из паттерна
- старт = `default_branch` репы спек или `component.default_branch` (часто `target` / `startPoint` / `from_branch` / `source`)

Этап C использует `plan.component` (`workspace` / `repo_slug` / `project` из `component.repository`).

`create_pr`:

- этап A: head = ветка Improvement, base = ветка Story в репе спек
- этап B: head = ветка таски в репе спек, base = ветка Story в репе спек
- этап C: head = `task/{TASK-KEY}`, base = ветка Story в репе компонента
- не в `default_branch` / master, если base должен быть story-веткой

Локальный `git fetch` / `checkout` / `commit` / `push` для OpenSpec-файлов разрешён. Создание веток и PR — через MCP.
