---
name: sdd-auto-story-to-release
description: >-
  Принимает номер release Story, собирает её состав (дочерние/связанные Story и
  Jira Component) и через MCP Bitbucket создаёт release-ветку на каждый
  компонент и PR каждой Story в эту ветку. Jira и Bitbucket только через MCP.
  Используй при sdd-auto-story-to-release, release Story, release-ветка,
  PR в release.
---

# sdd-auto-story-to-release

Сборка релиза из release Story для агента GigaCode.

Этот каталог копируется в проект как `.gigacode/skills/sdd-auto-story-to-release/`.

MCP Jira и MCP Bitbucket **уже подключены**. Не спрашивай токены. Не вызывай REST Jira/Bitbucket. Не пиши `curl` к `/rest/api`. Если нужного MCP-инструмента нет — остановись и назови недостающее действие.

Параметры только из `settings.yaml` и **ключа release Story**, который дал пользователь. Схема: `references/settings.md`. MCP: `references/mcp.md`.

Локальный CLI — JQL состава, номер релиза, план веток/PR. Запись в Bitbucket — только MCP. Этот скилл **не** меняет статусы Jira.

```bash
python .gigacode/skills/sdd-auto-story-to-release/scripts/run.py --settings settings.yaml plan
python .gigacode/skills/sdd-auto-story-to-release/scripts/run.py --settings settings.yaml stories-jql REL-12
python .gigacode/skills/sdd-auto-story-to-release/scripts/run.py --settings settings.yaml compose REL-12 \
  --release-number 1.2 --story DEV-40:backend --story DEV-41:ui
```

## Когда использовать

Пользователь даёт номер release Story (`REL-12` / `DEV-100`) и просит `/sdd-auto-story-to-release`, собрать состав, создать `release/<номер>` по компонентам и открыть PR Story в эти ветки.

## Preconditions

1. Есть `settings.yaml` (скопируй `assets/settings.example.yaml`, если файла нет). Если найден только example — не пиши в Bitbucket, попроси заполнить значения.
2. Пользователь назвал **ключ release Story**. Не ищи релиз JQL-фильтром `source`, если ключ уже дан.
3. В сессии доступны MCP Jira и MCP Bitbucket. Сопоставь имена с `plan` / `mcp-aliases`.
4. В settings есть репозиторий **с именем компонента** (`components[].name` или `related.component` + `component.repository`). Не угадывай slug репы из имени Component.
5. Перед записью покажи план: номер релиза, Story и компоненты, какие ветки и PR будут созданы, кого пропустишь. Если пользователь не подтвердил — остановись после плана.

## Pipeline

```
release Story key (input)
    → composition: child/linked Stories + Component (1–2)
    → release/{number} per component repo (3)
    → PR each Story × component → that release branch (4)
```

### 0. MCP-инструменты

1. Посмотри список доступных MCP tools.
2. Первое совпадение из алиасов (`references/mcp.md`).
3. Jira: `get`, `search`. Bitbucket: `create_branch`, `create_pr`. Желательны `get_branch`, `list_prs`.
4. Нет совпадения — не подставляй REST.

### 1. Взять release Story

Вход: ключ, который дал пользователь.

Jira MCP `get` этой задачи. Номер релиза — как в `sdd-auto-story-to-uat`: `release.number` / `--release-number` / `number_field` / `fixVersions` / regex в summary. Не выдумывай номер.

```bash
python .gigacode/skills/sdd-auto-story-to-release/scripts/run.py --settings settings.yaml release-number REL-12 \
  --summary "Release 1.2"
```

### 2. Состав: дочерние и связанные Story + Component

Как в `sdd-auto-story-to-uat`:

```bash
python .gigacode/skills/sdd-auto-story-to-release/scripts/run.py --settings settings.yaml stories-jql REL-12
```

Jira MCP `search`, `maxResults` = `limits.max_stories`. `stories.via`: `parent` / `linked` / `both`.

Дополнительно `get` release Story: `subtasks` / `issuelinks`. Объедини по ключу. Оставь типы из `stories.issue_type`.

Компонент Story — поле Jira `components`, как в `sdd-auto-impr-to-story`. Если в `search` компонентов нет — `get` каждой Story. Если поле пустое — только fallback `related.component` / `component.name` (тот же fallback, что у impr-to-story). Других источников компонента нет.

Пустой состав — не создавай ветки и PR. Напиши, что Story нет.

```bash
python .gigacode/skills/sdd-auto-story-to-release/scripts/run.py --settings settings.yaml compose REL-12 \
  --json '{"release": {...}, "stories": {"issues": [...]}}'
```

### 3. Release-ветка на каждый компонент

Имя ветки — паттерн `sdd-auto-story-to-uat`: `release.branch_pattern` = `release/{number}`. Не придумывай суффикс компонента в имени ветки.

Для каждого **уникального** компонента из состава, у которого в settings есть `repository`:

1. Bitbucket MCP `get_branch` / list: если `release/{number}` уже есть — не создавай заново.
2. Иначе `create_branch` **от `component.default_branch`** (как skill 1 создаёт ветки от default, не от feature).

Репозиторий бери только из settings (`components[]` или блок `component` skill 1). Нет репы для имени Component — пропусти этот компонент, не угадывай URL.

### 4. PR каждой Story в release-ветку её компонента

Для каждой пары Story × её Component с известной репой:

- head = `component.story_branch_pattern` / `bitbucket.story_branch_pattern` skill 1, по умолчанию `feature/{STORY-KEY}`
- base = `release/{number}`
- title из `issue-plan` / `compose`: `{STORY-KEY} → release/{number}`

Сначала `list_prs`. Если PR с этим head/base уже есть — верни URL. Иначе Bitbucket MCP `create_pr`.

Не создавай feature-ветку Story, если её нет: в этом скилле нет такого шага. Напиши, что head не найден.

Не мержь PR. Не меняй статусы Jira.

## Правила

- Вход — ключ release Story, не поиск всех релизов.
- Не выдумывай project / component / repository / номер релиза / имя ветки.
- Forge — Bitbucket. Не GitHub/GitLab.
- Токенов в YAML быть не должно.
- Story без Component и без fallback — пропусти.
- Component без репы в settings — пропусти.
- В отчёте: ключ релиза, номер, состав, созданные ветки, PR, пропуски и причины.
