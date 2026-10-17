---
name: sdd-auto-story-to-uat
description: >-
  Находит release-задачу в Jira, для каждой Story релиза проверяет PR в Bitbucket
  и если все учтённые PR влиты в release-ветку с номером релиза — переводит
  Story в «Ready for UAT». Jira и Bitbucket только через MCP. Используй при
  sdd-auto-story-to-uat, Story→UAT, Ready for UAT, release-ветка.
---

# sdd-auto-story-to-uat

Автоматический перевод Story в Ready for UAT для агента GigaCode.

Этот каталог копируется в проект как `.gigacode/skills/sdd-auto-story-to-uat/`.

MCP Jira и MCP Bitbucket **уже подключены**. Не спрашивай токены. Не вызывай REST Jira/Bitbucket. Не пиши `curl` к `/rest/api`. Если нужного MCP-инструмента нет — остановись и назови недостающее действие.

Параметры только из `settings.yaml`. Схема: `references/settings.md`. MCP: `references/mcp.md`.

Локальный CLI — только JQL, номер релиза, план и оценка PR. Запись в Jira и Bitbucket — только MCP.

```bash
python .gigacode/skills/sdd-auto-story-to-uat/scripts/run.py --settings settings.yaml plan
python .gigacode/skills/sdd-auto-story-to-uat/scripts/run.py --settings settings.yaml jql
python .gigacode/skills/sdd-auto-story-to-uat/scripts/run.py --settings settings.yaml stories-jql REL-12
python .gigacode/skills/sdd-auto-story-to-uat/scripts/run.py --settings settings.yaml evaluate DEV-40 \
  --release REL-12 --release-number 1.2 --story-status "Ready for IFT" \
  --pr feature/DEV-40:MERGED:release/1.2
```

## Когда использовать

Пользователь просит `/sdd-auto-story-to-uat`, перевести Story релиза в Ready for UAT, проверить что PR влиты в `release/<номер>`.

## Preconditions

1. Есть `settings.yaml` (скопируй `assets/settings.example.yaml`, если файла нет). Если найден только example — не пиши в Jira, попроси заполнить значения.
2. В сессии доступны MCP Jira и MCP Bitbucket. Сопоставь имена инструментов с алиасами из `plan` / `mcp-aliases`.
3. В Jira уже существуют указанные `issuetype` и статусы. В Bitbucket есть release-ветки по паттерну из настроек.
4. Перед живой записью покажи план: JQL релиза, номер релиза, список Story, какие будут переведены. Если пользователь не подтвердил — остановись после плана.

## Pipeline

```
search release tasks (1)
    → release number (2)
    → Stories under the release (3)
    → PRs of each Story (4)
    → all considered PRs merged into release/<number>? (5)
    → transitions + transition that Story → Ready for UAT (6)
```

Переводи **каждую** Story, которая уже удовлетворяет условию. Не жди, пока весь релиз будет готов.

### 0. MCP-инструменты

1. Посмотри список доступных MCP tools.
2. Для каждого действия возьми **первое совпадение** из алиасов (`references/mcp.md`).
3. Обязательные действия Jira: `search`, `get`, `transitions`, `transition`.
4. Обязательные действия Bitbucket: `list_prs`. Желателен `get_pr`, если в списке нет state / destination.
5. Нет совпадения — не подставляй REST. Сообщи, какого action не хватает.

Workspace / slug репозитория — `plan.bitbucket`.

### 1. Найти release-задачу

Параметры: `source.project` (пространство), `source.issue_type`, `source.label`, `source.status`.

```bash
python .gigacode/skills/sdd-auto-story-to-uat/scripts/run.py --settings settings.yaml jql
```

Вызови Jira MCP `search` с этим JQL. `maxResults` = `limits.max_issues`.

Пустой список — остановись, напиши что фильтр ничего не нашёл. Не расширяй JQL.

Если задач несколько — обработай каждую отдельно.

### 2. Номер релиза

Параметры: `release.number`, `release.number_field`, `release.number_pattern`.

Порядок:

1. `--release-number` / `release.number` из настроек;
2. поле `release.number_field` (например `fixVersions`) из MCP `get`;
3. `fixVersions` задачи;
4. первое совпадение `release.number_pattern` в summary / key / description / labels.

```bash
python .gigacode/skills/sdd-auto-story-to-uat/scripts/run.py --settings settings.yaml release-number REL-12 \
  --summary "Release 1.2.0"
```

Не выдумывай номер. Если извлечь нельзя — остановись для этой release-задачи.

### 3. Найти Story этого релиза

Параметры: `stories.issue_type` (по умолчанию `Story`), `stories.via` (`parent` / `linked` / `both`), `stories.link_type`, `stories.status`.

```bash
python .gigacode/skills/sdd-auto-story-to-uat/scripts/run.py --settings settings.yaml stories-jql REL-12 \
  --release-number 1.2
```

Вызови Jira MCP `search`. `maxResults` = `limits.max_stories`.

Дополнительно `get` release-задачи: `fields.subtasks` и `issuelinks`. Объедини по ключу. Оставь только типы из `stories.issue_type`.

Пустой список Story — напиши это и переходи к следующей release-задаче. Не расширяй JQL.

### 4. PR каждой Story

Для каждой Story:

1. Если `pr.include_child_keys` (по умолчанию да) — найди дочерние Task/Sub-task:

```bash
python .gigacode/skills/sdd-auto-story-to-uat/scripts/run.py --settings settings.yaml children-jql STORY-KEY
```

2. Для каждого репозитория из `plan.bitbucket` вызови Bitbucket MCP `list_prs`. Если state/destination нет — `get_pr`.
3. PR принадлежит Story, если ключ Story (или ребёнка) есть в title / source / destination / description.

Не вызывай GitHub/GitLab API.

### 5. Все учтённые PR влиты в release-ветку с номером?

Параметры: `release.branch_pattern` (по умолчанию `release/{number}`), `pr.merged_states`, `pr.ignore_states`, `pr.ignore_destination_prefixes`.

Не учитывай PR в статусах `DECLINED` / `SUPERSEDED` и PR в ветки `feature/` и `task/` (внутренние PR конвейера SDD). Это настраивается.

Оставшиеся PR должны:

- все быть `MERGED` (или `pr.merged_states`);
- все иметь destination, которая совпадает с `release/{number}` или начинается с префикса паттерна и содержит номер (`release/1.2`, `release/1.2.0` для номера `1.2`).

Нет учтённых PR ≠ «все влиты»: Story пропусти.

```bash
python .gigacode/skills/sdd-auto-story-to-uat/scripts/run.py --settings settings.yaml evaluate STORY-KEY \
  --release REL-12 --release-number 1.2 --story-status "Ready for IFT" \
  --child DEV-41 --pr feature/DEV-40:MERGED:release/1.2
```

`should_transition` = true только если условие выполнено и Story ещё не в целевом статусе.

Ошибка одной Story не отменяет остальные. Переводи готовую Story сразу, не жди весь релиз.

### 6. Перевести Story в целевой статус

Параметры: `target.statuses` / `story.target_status` (по умолчанию `Ready for UAT`).

Только если пункт 5 сказал переводить:

1. Jira MCP `transitions` для ключа Story.
2. Первое совпадение имени перехода **или** статуса назначения с `target.statuses` без учёта регистра.
3. Jira MCP `transition` с id перехода.

Если перехода нет — не выдумывай id. Если Story уже в целевом статусе — не вызывай `transition`.

## Правила

- Обрабатывай каждую Story отдельно. Не жди завершения всего релиза.
- Не выдумывай project / type / label / status / repository / номер релиза.
- Не вызывай GitHub/GitLab/GitVerse API. Forge — Bitbucket.
- Не коммить `settings.yaml` с секретами. Токенов в YAML быть не должно.
- Не расширяй JQL, если поиск пустой.
- В отчёте: release и номер, Story, учтённые PR и их destination, кого перевели, кого пропустили и почему.
