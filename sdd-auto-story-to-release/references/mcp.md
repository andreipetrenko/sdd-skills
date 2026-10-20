# Jira и Bitbucket MCP

Серверы уже настроены. Скилл только выбирает tool по алиасу.

## Запрещено

- REST `curl` / `requests`
- спрашивать токены
- GitHub / GitLab / GitVerse API
- выдумывать workspace, slug, номер релиза, репу компонента

## Jira

| Action | Алиасы | Зачем |
| --- | --- | --- |
| `get` | `getJiraIssue`, `jira_get_issue`, `get_issue` | release Story; Component на Story состава |
| `search` | `searchJiraIssuesUsingJql`, `jira_search`, `search_issues` | состав: `parent` / `linkedIssues` |

`search`: JQL из CLI, не меняй.

## Bitbucket

| Action | Алиасы | Зачем |
| --- | --- | --- |
| `create_branch` | `createBitbucketRepoBranch`, `create_branch`, `createBranch` | `release/{number}` от `default_branch` |
| `get_branch` | `getBitbucketRepoBranch`, `list_branches` | не плодить ветки; проверить head Story |
| `create_pr` | `createBitbucketRepoPullRequest`, `create_pull_request` | `feature/{STORY-KEY}` → `release/{number}` |
| `list_prs` | `listBitbucketRepoPullRequests`, `list_pull_requests` | не плодить PR |

Репозиторий — из `compose` / `issue-plan` (`workspace` + `repo_slug` или Server `project` + `repo_slug`).

`create_branch`: `name` = `release/{number}`, старт = `component.default_branch` (`target` / `startPoint` / `from_branch`).

`create_pr`: head = `feature/{STORY-KEY}`, base = `release/{number}`. Не в `default_branch`.
