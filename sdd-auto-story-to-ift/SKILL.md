---
name: sdd-auto-story-to-ift
description: >-
  Находит Story в Jira по фильтрам из settings.yaml, проверяет дочерние
  Task/Sub-task и если все они в статусе «Готов» — переводит Story в
  «Ready for IFT». Jira только через MCP. Используй при sdd-auto-story-to-ift,
  Story→IFT, Ready for IFT, дочерние задачи готовы.
---

# sdd-auto-story-to-ift

Автоматический перевод Story в Ready for IFT для агента GigaCode.

Этот каталог копируется в проект как `.gigacode/skills/sdd-auto-story-to-ift/`.

MCP Jira **уже подключён**. Не спрашивай токены. Не вызывай REST Jira. Не пиши `curl` к `/rest/api`. Если нужного MCP-инструмента нет — остановись и назови недостающее действие.

Параметры только из общего `settings.yaml` оркестратора `sdd-auto-impr-to-release` (секция `sdd-auto-story-to-ift` + общие блоки). Схема: `references/settings.md`. MCP: `references/mcp.md`. Между скиллами данные — в общем `storage.yaml` (`--storage`).

Локальный CLI — только JQL, план и оценка статусов. Запись в Jira — только MCP.

```bash
python .gigacode/skills/sdd-auto-story-to-ift/scripts/run.py --settings settings.yaml plan
python .gigacode/skills/sdd-auto-story-to-ift/scripts/run.py --settings settings.yaml jql
python .gigacode/skills/sdd-auto-story-to-ift/scripts/run.py --settings settings.yaml children-jql STORY-KEY
python .gigacode/skills/sdd-auto-story-to-ift/scripts/run.py --settings settings.yaml evaluate STORY-KEY \
  --story-status "In Progress" --child TASK-1:Готов --child TASK-2:Готов
```

## Когда использовать

Пользователь просит `/sdd-auto-story-to-ift`, перевести Story в Ready for IFT, проверить что все дочерние Task/Sub-task в статусе «Готов».

## Preconditions

1. Есть `settings.yaml` (скопируй `assets/settings.example.yaml`, если файла нет). Если найден только example — не пиши в Jira, попроси заполнить значения.
2. В сессии доступен MCP Jira. Сопоставь имена инструментов с алиасами из `plan` / `mcp-aliases`.
3. В Jira уже существуют указанные `issuetype` и статусы.
4. Перед живой записью покажи план: JQL поиска Story, список ключей, по каким Story будет переход. Если пользователь не подтвердил — остановись после плана.

## Pipeline

```
search Stories (1)
    → children Task/Sub-task of each Story (2)
    → all children in ready status? (3)
    → transitions + transition Story → target (4)
```

### 0. MCP-инструменты

1. Посмотри список доступных MCP tools.
2. Для каждого действия возьми **первое совпадение** из алиасов (`references/mcp.md`).
3. Обязательные действия Jira: `search`, `get`, `transitions`, `transition`.
4. Нет совпадения — не подставляй REST. Сообщи, какого action не хватает.

### 1. Найти Story

Параметры: `source.project` (пространство), `source.issue_type`, `source.label`, `source.status`.

```bash
python .gigacode/skills/sdd-auto-story-to-ift/scripts/run.py --settings settings.yaml jql
```

Вызови Jira MCP `search` с этим JQL. `maxResults` = `limits.max_issues`.

Пустой список — остановись, напиши что фильтр ничего не нашёл. Не расширяй JQL.

### 2. Для каждой Story — найти дочерние Task/Sub-task

Параметры: `children.issue_type` (по умолчанию `Task`, `Sub-task`, `Subtask`).

```bash
python .gigacode/skills/sdd-auto-story-to-ift/scripts/run.py --settings settings.yaml children-jql STORY-KEY
```

Вызови Jira MCP `search` с этим JQL. `maxResults` = `limits.max_children`.

Дополнительно можно `get` саму Story и взять `fields.subtasks` / `children`. Объедини результаты по ключу. Оставь только типы из `children.issue_type` (без учёта регистра). Другие типы детей не учитывай.

Нет подходящих детей — **не** переводи Story. В отчёте напиши, что детей указанного типа нет.

### 3. Проверить, что ВСЕ подходящие дети в ready-статусе

Параметры: `children.ready_status` / `children.ready.statuses` (по умолчанию `Готов`).

Сравни статусы без учёта регистра.

```bash
python .gigacode/skills/sdd-auto-story-to-ift/scripts/run.py --settings settings.yaml evaluate STORY-KEY \
  --story-status "..." --child KEY:STATUS --child KEY:TYPE:STATUS
```

Либо передай JSON ответа MCP:

```bash
python .gigacode/skills/sdd-auto-story-to-ift/scripts/run.py --settings settings.yaml evaluate STORY-KEY \
  --json '{"story": {...}, "children": {"issues": [...]}}'
```

`should_transition` = true только если:

- у Story есть хотя бы один ребёнок нужного типа;
- **все** такие дети в ready-статусе;
- сама Story ещё не в целевом статусе.

Иначе пропусти Story и продолжай со следующей. Ошибка одной не отменяет отчёт по остальным.

### 4. Перевести Story в целевой статус

Параметры: `target.statuses` / `story.target_status` (по умолчанию `Ready for IFT`).

Только если пункт 3 сказал переводить:

1. Jira MCP `transitions` для ключа Story.
2. Выбери **первое** совпадение имени перехода **или** имени статуса назначения со списком `target.statuses` без учёта регистра.
3. Локально можно проверить так:

```bash
python .gigacode/skills/sdd-auto-story-to-ift/scripts/run.py --settings settings.yaml match-transition \
  --transitions '[{"id":"31","name":"Ready for IFT","to":{"name":"Ready for IFT"}}]'
```

4. Jira MCP `transition` с id выбранного перехода.

Если подходящего перехода нет — не выдумывай id, не зови REST. Напиши, каких статусов нет среди переходов.

Если Story уже в целевом статусе — не вызывай `transition`.

## Правила

- Обрабатывай каждую Story отдельно. Ошибка одной не отменяет отчёт по остальным.
- Не выдумывай project / type / label / status.
- Не вызывай GitHub/GitLab/Bitbucket API — этот скилл только про Jira.
- Не коммить `settings.yaml` с секретами. Токенов в YAML быть не должно.
- Не расширяй JQL, если поиск пустой.
- Пустой набор детей ≠ «все готовы»: без детей переход не делай.
- В отчёте: найденные Story, дети и их статусы, кого перевели, кого пропустили и почему.
