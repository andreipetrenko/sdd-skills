---
name: sdd-auto-impr-to-story
description: >-
  Конвейер Improvement → Story → OpenSpec BR/FR → спека кода компонента →
  генерация кода → PR в репе компонента. Jira и Bitbucket только через MCP.
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

## Pipeline

Этап A — BR/FR в репе спек (`bitbucket.repository`):

```
source issues (1)
    → create Story (2)
    → feature/{SOURCE-KEY} (3)
    → OpenSpec BR + FR (4)
    → related task + component (5)
    → feature/{STORY-KEY} (6)
    → PR 3 → 6 (7)
    → after merge: Improvement → after_merge.statuses (8)
```

Этап B — спека кода в той же репе спек (после пункта 8):

```
OpenSpec code-changes for component (B1)
    → feature/{TASK-KEY} in specs repo (B2)
    → PR B2 → feature/{STORY-KEY} (B3)
    → after merge: Task → related.in_progress (B4)
```

Этап C — код в репе компонента (`component.repository`):

```
task/{TASK-KEY} from component.default_branch (C1)
    → OpenSpec apply / generate code from B1 spec (C2)
    → push to C1 (C3)
    → feature/{STORY-KEY} in component repo + PR C1 → story (C4)
    → after merge: Task → related.done, Story → story.done, Improvement → improvement_done (C5–C7)
```

### 0. MCP-инструменты

1. Посмотри список доступных MCP tools.
2. Для каждого действия возьми **первое совпадение** из алиасов (`references/mcp.md`).
3. Обязательные действия Jira: `search`, `get`, `create`, `link`, `transitions`, `transition`.
4. Обязательные действия Bitbucket: `create_branch`, `create_pr`. Желательны `get_branch` / `list_prs` / `get_pr` для идемпотентности.
5. Нет совпадения — не подставляй REST. Сообщи, какого action не хватает.

Workspace / slug репозитория спек — `plan.bitbucket`. Репозиторий компонента — `plan.component`.

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

На этом шаге не меняй статус Story и related-задачи. Не мержь PR сам, пока пользователь этого не попросил.

Если PR ещё открыт — отдай URL и остановись. Этап B начинай только после merge пункта 7 и перехода пункта 8.

### B1. Спека изменений кода в рамках компонента

После пункта 8 сгенерируй OpenSpec-спеку **изменений кода** только для компонента задачи (`related.component` / Component исходной). Источник: принятые BR/FR (`openspec/changes/<source-change-id>/`) и описание исходной задачи.

Работай в клоне **репы спек** `bitbucket.repository`.

1. `openspec new <impl-id>` если change нет. `impl-id` = kebab-case ключа **таски компонента** (`implementation_change_id_pattern`, по умолчанию `{task_key}`).
2. `openspec instructions proposal|specs --change <impl-id>`
3. Файлы:
   - `openspec/changes/<impl-id>/proposal.md`
   - `openspec/changes/<impl-id>/specs/code-changes/spec.md`
   - `openspec/changes/<impl-id>/design.md` — подход внутри компонента
4. Формат delta spec тот же: `### Requirement:` + SHALL/MUST, `#### Scenario:` GIVEN/WHEN/THEN.
5. Каркас: `python .../scripts/run.py scaffold-impl-spec TASK-KEY --issue SOURCE --story STORY --component ... --repo <specs-clone>`
6. `openspec validate --change <impl-id>` или `validate-specs SOURCE --task TASK-KEY --repo <specs-clone>`

Не пиши код приложения в репе спек — только спеку.

### B2. Feature-ветка репы спек с номером таски

Имя: `bitbucket.task_branch_pattern` (по умолчанию `feature/{TASK-KEY}`). Создай через Bitbucket MCP от `bitbucket.default_branch` (или используй существующую). Checkout, commit спеки, `git push` в эту ветку.

### B3. PR: ветка таски → ветка Story в репе спек

Head = ветка B2. Base = `feature/{STORY-KEY}` (пункт 6 этапа A). Не в default_branch, если base должен быть story-веткой.

### B4. После merge — таска в работу

Не меняй статус таски до merge PR B3. Затем `transitions` таски, первое совпадение с `related.in_progress` / `related.in_progress_status` (`В работе`, `In Progress`).

### C1. Ветка task в репозитории компонента

Репозиторий: `component.repository`. Мастер: `component.default_branch` (например `master`). Имя: `component.task_branch_pattern` (по умолчанию `task/{TASK-KEY}`).

Создай через Bitbucket MCP **от мастер-ветки компонента**.

### C2. Генерация кода инструментами OpenSpec

В клоне **репы компонента**, на ветке C1, по спеке B1 (code-changes + design + принятые BR/FR):

- скопируй/подтяни `openspec/changes/<impl-id>/` в дерево компонента, если его там нет;
- `openspec instructions apply --change <impl-id>` если команда есть;
- реализуй код строго по спеке компонента, без лишнего рефакторинга.

### C3. Пуш кода в ветку C1

`git commit` и `git push` **в `task/{TASK-KEY}`** репы компонента. Не в мастер.

### C4. PR в ветку Story в том же репозитории компонента

Сначала создай ветку Story в репе компонента: `component.story_branch_pattern` (по умолчанию `feature/{STORY-KEY}`) **от `component.default_branch`**, не от task-ветки.

Затем PR: head = `task/{TASK-KEY}`, base = `feature/{STORY-KEY}` в `component.repository`.

### C5–C7. Финальные статусы после merge кода

Только после merge PR C4, в таком порядке:

1. Таска → `related.done` / `related.done_status`
2. Story → `story.done` / `story.done_status`
3. Improvement → `improvement_done` / `source.done`

Первое совпадение имени перехода без учёта регистра. Не мержь PR сам, пока пользователь не попросил.

## Правила

- Обрабатывай каждую исходную задачу отдельно. Ошибка одной не отменяет отчёт по остальным.
- Не выдумывай project / type / label / status / component / repository.
- Не вызывай GitHub/GitLab API. Forge — Bitbucket.
- Не коммить `settings.yaml` с секретами. Токенов в YAML быть не должно.
- Этап B не начинай, пока не смержен PR пункта 7 и не выполнен пункт 8. Этап C — пока не смержен PR B3 и не выполнен B4.
- В отчёте: source, story, related, ветки и PR репы спек, ветки и PR репы компонента, статусы improvement/story/task.
