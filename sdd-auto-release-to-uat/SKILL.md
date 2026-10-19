---
name: sdd-auto-release-to-uat
description: >-
  Находит release Epic/задачу в Jira, проверяет все Story релиза и если все они
  в статусе «Ready for UAT» — переводит Epic/задачу в «Ready for UAT».
  Jira только через MCP. Используй при sdd-auto-release-to-uat, Epic→UAT,
  релиз Ready for UAT, все Story готовы.
---

# sdd-auto-release-to-uat

Автоматический перевод release Epic/задачи в Ready for UAT для агента GigaCode.

Этот каталог копируется в проект как `.gigacode/skills/sdd-auto-release-to-uat/`.

MCP Jira **уже подключён**. Не спрашивай токены. Не вызывай REST Jira. Не пиши `curl` к `/rest/api`. Если нужного MCP-инструмента нет — остановись и назови недостающее действие.

Параметры только из `settings.yaml`. Схема: `references/settings.md`. MCP: `references/mcp.md`.

Локальный CLI — только JQL, план и оценка статусов. Запись в Jira — только MCP.

```bash
python .gigacode/skills/sdd-auto-release-to-uat/scripts/run.py --settings settings.yaml plan
python .gigacode/skills/sdd-auto-release-to-uat/scripts/run.py --settings settings.yaml jql
python .gigacode/skills/sdd-auto-release-to-uat/scripts/run.py --settings settings.yaml stories-jql REL-12
python .gigacode/skills/sdd-auto-release-to-uat/scripts/run.py --settings settings.yaml evaluate REL-12 \
  --release-status "In Progress" --story DEV-40:Ready for UAT --story DEV-41:Ready for UAT
```

## Когда использовать

Пользователь просит `/sdd-auto-release-to-uat`, перевести Epic/задачу релиза в Ready for UAT, проверить что **все** Story релиза уже в «Ready for UAT».

## Preconditions

1. Есть `settings.yaml` (скопируй `assets/settings.example.yaml`, если файла нет). Если найден только example — не пиши в Jira, попроси заполнить значения.
2. В сессии доступен MCP Jira. Сопоставь имена инструментов с алиасами из `plan` / `mcp-aliases`.
3. В Jira уже существуют указанные `issuetype` и статусы.
4. Перед живой записью покажи план: JQL релиза, список Story и их статусы, будет ли переход. Если пользователь не подтвердил — остановись после плана.

## Pipeline

```
search release Epic/task (1)
    → Stories of the release (2)
    → all Stories in ready status? (3)
    → transitions + transition Epic/task → target (4)
```

Не переводи Epic, пока есть хотя бы одна Story не в ready-статусе. Пустой набор Story ≠ «все готовы»: пропусти релиз.

### 0. MCP-инструменты

1. Посмотри список доступных MCP tools.
2. Для каждого действия возьми **первое совпадение** из алиасов (`references/mcp.md`).
3. Обязательные действия Jira: `search`, `get`, `transitions`, `transition`.
4. Нет совпадения — не подставляй REST. Сообщи, какого action не хватает.

### 1. Найти release Epic/задачу

Параметры: `source.project` (пространство), `source.issue_type`, `source.label`, `source.status`. Тот же паттерн фильтра, что у `sdd-auto-story-to-uat`.

```bash
python .gigacode/skills/sdd-auto-release-to-uat/scripts/run.py --settings settings.yaml jql
```

Вызови Jira MCP `search` с этим JQL. `maxResults` = `limits.max_issues`.

Пустой список — остановись, напиши что фильтр ничего не нашёл. Не расширяй JQL.

Если задач несколько — обработай каждую отдельно.

### 2. Найти Story этого релиза

Параметры: `stories.issue_type` (по умолчанию `Story`), `stories.via` (`parent` / `linked` / `both`), `stories.link_type`.

Тот же подход, что у `sdd-auto-story-to-uat`. **Не** ставь `stories.status` = ready-статус: иначе поиск скроет неготовые Story.

```bash
python .gigacode/skills/sdd-auto-release-to-uat/scripts/run.py --settings settings.yaml stories-jql REL-12
```

Вызови Jira MCP `search`. `maxResults` = `limits.max_stories`.

Дополнительно `get` Epic/задачи: `fields.subtasks` и `issuelinks`. Объедини по ключу. Оставь только типы из `stories.issue_type`.

Пустой список Story — **не** переводи Epic. В отчёте напиши, что Story нет.

### 3. Проверить, что ВСЕ Story в ready-статусе

Параметры: `stories.ready_status` (по умолчанию `Ready for UAT`). Сравни без учёта регистра.

```bash
python .gigacode/skills/sdd-auto-release-to-uat/scripts/run.py --settings settings.yaml evaluate REL-12 \
  --release-status "In Progress" --story DEV-40:Ready for UAT --story DEV-41:Ready for IFT
```

Либо передай JSON ответа MCP:

```bash
python .gigacode/skills/sdd-auto-release-to-uat/scripts/run.py --settings settings.yaml evaluate REL-12 \
  --json '{"release": {...}, "stories": {"issues": [...]}}'
```

`should_transition` = true только если:

- у релиза есть хотя бы одна Story нужного типа;
- **все** такие Story в `stories.ready_status`;
- сам Epic/задача ещё не в целевом статусе.

Иначе пропусти релиз и продолжай со следующим. Ошибка одного не отменяет остальные.

### 4. Перевести Epic/задачу в целевой статус

Параметры: `target.statuses` (по умолчанию `Ready for UAT`).

Только если пункт 3 сказал переводить:

1. Jira MCP `transitions` для ключа Epic/задачи.
2. Первое совпадение имени перехода **или** статуса назначения с `target.statuses` без учёта регистра.
3. Jira MCP `transition` с id перехода.

Если перехода нет — не выдумывай id. Если Epic уже в целевом статусе — не вызывай `transition`.

## Правила

- Обрабатывай каждый релиз отдельно.
- Не выдумывай project / type / label / status.
- Не вызывай GitHub/GitLab/Bitbucket API — этот скилл только про Jira.
- Не коммить `settings.yaml` с секретами. Токенов в YAML быть не должно.
- Не расширяй JQL, если поиск пустой.
- Пустой набор Story ≠ «все готовы»: без Story переход не делай.
- В отчёте: Epic/задача, Story и статусы, перевели или пропустили и почему.
