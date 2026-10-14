# sdd-auto-impr-to-story

Skill для [GigaCode](https://gitverse.ru/docs/ai/ai-assistant-gigacode/gigacode-for-vscode/skills): проводит Improvement из Jira по spec-driven циклу.

Исходный запрос для новой сессии: [`PROMPT.md`](PROMPT.md).

Jira и Bitbucket уже должны быть подключены к агенту как MCP. Skill не ходит в REST и не хранит токены.

1. Ищет задачи по пространству, типу, метке и статусу из `settings.yaml`
2. На каждую найденную создаёт Story (тоже по параметрам из настроек)
3. Создаёт feature-ветку с номером исходной задачи в репозитории Bitbucket
4. Генерирует бизнес- и функциональные требования в формате [OpenSpec](https://openspec.dev) и пушит их в эту ветку
5. Создаёт связанную задачу нужного типа, с нужным типом связи и компонентом изменения
6. Создаёт feature-ветку с номером Story в том же репозитории
7. Открывает pull request **из ветки пункта 3 в ветку пункта 6**
8. После мержа переводит Improvement в `В работе` / `In Progress`
9. Генерирует спеку изменений кода компонента и пушит в ветку таски в репе спек
10. PR этой ветки в ветку Story; после merge таска → статус «в работе» из настроек
11. В репе компонента создаёт `task/{TASK}` от мастера, генерирует код OpenSpec, пушит
12. PR в ветку Story в репе компонента; после merge выставляет финальные статусы таски, Story и Improvement

## Быстрый старт

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp settings.example.yaml settings.yaml
```

Заполните `settings.yaml`. Секреты не нужны: агент GigaCode вызывает уже настроенные MCP Jira и Bitbucket.

Локальный CLI только читает настройки, печатает JQL/план полей и работает с OpenSpec:

```bash
python -m sdd_auto_impr_to_story --settings settings.yaml jql
python -m sdd_auto_impr_to_story --settings settings.yaml plan
python -m sdd_auto_impr_to_story --settings settings.yaml issue-plan IMPR-12 \
  --summary "..." --description "..."
```

То же через обёртку skill:

```bash
python scripts/run.py --settings settings.yaml plan
```

В проекте, куда скилл скопирован как `.gigacode/skills/sdd-auto-impr-to-story/`:

```bash
python .gigacode/skills/sdd-auto-impr-to-story/scripts/run.py --settings settings.yaml plan
```

## GigaCode skill

Чтобы подключить скилл, скопируйте эту папку в `.gigacode/skills/sdd-auto-impr-to-story/` целевого проекта. В агенте вызовите `/sdd-auto-impr-to-story` или опишите Improvement→Story / SDD.

Агент:

- читает `settings.yaml`
- ищет и создаёт задачи **только через Jira MCP**
- создаёт ветки и PR **только через Bitbucket MCP**
- пишет BR/FR через инструменты OpenSpec (`openspec new`, `openspec instructions`, `openspec validate`)
- открывает PR спек `feature/{IMPROVEMENT}` → `feature/{STORY}`, затем спеку кода и PR в репе компонента
- статусы Jira меняет только после соответствующего merge

## settings.yaml

| Блок | Этап | Поля |
| --- | --- | --- |
| `source` | A | `project`, `issue_type`, `label`, `status` |
| `story` | A, C | `project`, `issue_type`, `done_status` |
| `bitbucket` | A, B | репа спек |
| `related` | A, B, C | `component`, `in_progress_status`, `done_status` |
| `after_merge` | A8 | Improvement в работу |
| `component` | C | репа кода, `default_branch` (мастер) |
| `improvement_done` | C | финальный статус Improvement |

Полный пример — `settings.example.yaml`. Разбор полей — `references/settings.md`.

## Тесты

```bash
python -m pytest
```
