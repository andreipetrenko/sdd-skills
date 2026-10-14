---
name: sdd-auto-impr-to-story
description: >-
  Конвейер Improvement → Story → OpenSpec BR/FR → ветки Bitbucket → PR.
  Ищи задачи Jira по settings.yaml, создавай Story и связанную задачу,
  ветки и pull request через уже подключённые MCP Jira и Bitbucket.
  Используй при sdd-auto-impr-to-story, Improvement→Story, SDD, OpenSpec из Jira.
---

# sdd-auto-impr-to-story

Автоматический SDD-конвейер для агента GigaCode.

Этот каталог копируется в проект как `.gigacode/skills/sdd-auto-impr-to-story/`.

MCP Jira и MCP Bitbucket **уже подключены**. Не спрашивай токены. Не вызывай REST Jira/Bitbucket. Не пиши `curl` к `/rest/api`. Если нужного MCP-инструмента нет — остановись и назови недостающее действие.

Параметры только из `settings.yaml`. Схема: `references/settings.md`. MCP: `references/mcp.md`. OpenSpec: `references/openspec.md`.

Локальный CLI — только JQL, план полей и OpenSpec. Запись в Jira и Bitbucket — только MCP.

```bash
python .gigacode/skills/sdd-auto-impr-to-story/scripts/run.py --settings settings.yaml plan
python .gigacode/skills/sdd-auto-impr-to-story/scripts/run.py --settings settings.yaml jql
python .gigacode/skills/sdd-auto-impr-to-story/scripts/run.py issue-plan SOURCE-KEY --summary "..." --description "..."
```

## Когда использовать

Пользователь просит `/sdd-auto-impr-to-story`, провести Improvement в Story, сгенерировать BR/FR, открыть PR из ветки Improvement в ветку Story.

## Preconditions

1. Есть `settings.yaml` (скопируй `assets/settings.example.yaml`, если файла нет). Если найден только example — не пиши в Jira/Bitbucket, попроси заполнить значения.
2. В сессии доступны MCP Jira и MCP Bitbucket. Сопоставь имена инструментов с алиасами из `plan` / `mcp-aliases`.
3. В Jira уже существуют указанные `issuetype`, статусы, метки и Component.
4. Перед живой записью покажи план: JQL, список SOURCE-KEY, какие Story/ветки/PR будут созданы. Если пользователь не подтвердил — остановись после плана.

## Pipeline (ровно эти 8 пунктов)

```
source issues (1)
    → create Story (2)
    → feature/{SOURCE-KEY} in bitbucket.repository (3)
    → OpenSpec BR + FR, commit, push to (3) (4)
    → related issue + link + component (5)
    → feature/{STORY-KEY} in the same repo (6)
    → PR: branch(3) → branch(6) (7)
    → after merge: source issue → В работе/In Progress (8)
```

### 0. MCP-инструменты

1. Посмотри список доступных MCP tools.
2. Для каждого действия возьми **первое совпадение** из алиасов (`references/mcp.md`).
3. Обязательные действия Jira: `search`, `get`, `create`, `link`, `transitions`, `transition`.
4. Обязательные действия Bitbucket: `create_branch`, `create_pr`. Желательны `get_branch` / `list_prs` / `get_pr` для идемпотентности.
5. Нет совпадения — не подставляй REST. Сообщи, какого action не хватает.

Workspace / slug репозитория возьми из `plan.bitbucket` (разбор `bitbucket.repository`).

### 1. Найти задачи

Параметры: `source.project` (пространство), `source.issue_type`, `source.label`, `source.status`.

```bash
python .gigacode/skills/sdd-auto-impr-to-story/scripts/run.py --settings settings.yaml jql
```

Вызови Jira MCP `search` с этим JQL. `maxResults` = `limits.max_issues`.

Пустой список — остановись, напиши что фильтр ничего не нашёл. Не расширяй JQL.

### 2. Для каждой найденной — создать Story

Параметры: `story.project`, `story.issue_type`, `story.label`, `story.status`.

Идемпотентность: сначала `search` по `labels = "sdd-from-{SOURCE-KEY}"`. Если Story есть — используй её, не создавай вторую.

Иначе `issue-plan SOURCE-KEY --summary ... --description ...` и Jira MCP `create` с `story_fields` (`project`, `issue_type`, `summary`, `description`, `labels`). Статус при создании часто игнорируется: при необходимости `transitions` + `transition`.

Свяжи Story с исходной задачей: MCP `link`, тип `story.link_type`.

### 3. Feature-ветка с номером задачи пункта 1

Репозиторий: `bitbucket.repository`. Имя: `bitbucket.source_branch_pattern` (по умолчанию `feature/{SOURCE-KEY}`).

Создай ветку через Bitbucket MCP `create_branch` **от `bitbucket.default_branch`**. Если ветка уже есть (`get_branch` / list) — не создавай заново.

Не создавай ветку локальным `git checkout -b` вместо MCP, если MCP доступен.

### 4. BR и FR через OpenSpec, пуш в ветку пункта 3

Работай **в клоне `bitbucket.repository`**, на ветке пункта 3.

1. `git fetch` и checkout ветки пункта 3.
2. Прочитай summary и description исходной задачи — это единственный источник скоупа.
3. Если есть бинарь `openspec`:
   - `openspec list --specs`
   - `openspec new <change-id>` если change ещё нет (`change-id` = kebab-case `SOURCE-KEY`)
   - `openspec instructions proposal --change <change-id>`
   - `openspec instructions specs --change <change-id>`
4. Если `openspec` нет — пиши те же файлы по шаблонам в `assets/openspec/`. Не заменяй OpenSpec произвольным markdown.
5. Создай:
   - `openspec/changes/<change-id>/proposal.md`
   - `openspec/changes/<change-id>/specs/business-requirements/spec.md`
   - `openspec/changes/<change-id>/specs/functional-requirements/spec.md`
6. Формат delta spec: `### Requirement:` + SHALL/MUST, затем `#### Scenario:` с **GIVEN**/**WHEN**/**THEN**. Сценарий — ровно `####`.
7. `business-requirements` = ценность, акторы, ограничения. `functional-requirements` = наблюдаемое поведение. Без классов, фреймворков и плана реализации.
8. Проверка: `openspec validate --change <change-id>` и/или

```bash
python .gigacode/skills/sdd-auto-impr-to-story/scripts/run.py --settings settings.yaml \
  validate-specs SOURCE-KEY --repo <clone>
```

9. Закоммить и `git push` **в ветку пункта 3**. Локальный git для файлов — нормально. Не пушь в `default_branch`. Не используй heuristic-черновик CLI, если уже написал качественные BR/FR.

Запасной каркас файлов:

```bash
python .gigacode/skills/sdd-auto-impr-to-story/scripts/run.py scaffold-specs SOURCE-KEY \
  --summary "..." --description "..." --story STORY-KEY --repo <clone>
```

После каркаса **перепиши** требования по описанию Jira, не оставляй заглушки.

### 5. Связанная задача для Story

Параметры: `related.issue_type`, `related.link_type`, компонент (`related.component` или Component исходной задачи, если `component_from_source: true`).

Идемпотентность: `search` по метке `sdd-impl-{STORY-KEY}` (или `{related.label}-{STORY-KEY}`).

Иначе `create` с `related_fields` из `issue-plan ... --story STORY-KEY`. В задаче должен быть Component. Свяжи со Story типом `related.link_type`.

### 6. Feature-ветка с номером задачи пункта 2

Тот же репозиторий. Имя: `bitbucket.story_branch_pattern` (по умолчанию `feature/{STORY-KEY}`).

Создай через Bitbucket MCP **от `default_branch`**, не от ветки пункта 3 — иначе PR будет пустым.

### 7. Pull request: ветка 3 → ветка 6

Head = ветка с номером задачи пункта 1. Base = ветка с номером Story пункта 2. Не в `main`, если это не `story_branch_pattern`.

Сначала `list_prs`: если PR с этим head/base уже есть — верни его URL.

Иначе Bitbucket MCP `create_pr`. Заголовок из `issue-plan.pr.title`.

### 8. После мержа — статус задачи пункта 1 = В работе/In Progress

Не меняй статус до merge. Проверь PR через `get_pr` / `list_prs` (`MERGED` / `merged`).

Если смержен: `transitions` исходной задачи, выбери первое совпадение с `after_merge.statuses` без учёта регистра (`В работе`, `In Progress`), затем `transition`.

Не меняй статус Story и related-задачи. Не мержь PR сам, пока пользователь этого не попросил.

Если PR ещё открыт — отдай URL и напиши, что пункт 8 выполнится после merge.

## Правила

- Обрабатывай каждую исходную задачу отдельно. Ошибка одной не отменяет отчёт по остальным.
- Не выдумывай project / type / label / status / component / repository.
- Не вызывай GitHub/GitLab API. Forge — Bitbucket.
- Не коммить `settings.yaml` с секретами. Токенов в YAML быть не должно.
- В отчёте по каждой задаче: source, story, related, source_branch, story_branch, PR URL, исходная в работе да/нет.
