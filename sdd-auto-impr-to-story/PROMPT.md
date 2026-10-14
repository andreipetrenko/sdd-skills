# Промпт: создать скилл `sdd-auto-impr-to-story`

Вставь этот файл целиком в новую сессию агента. Ниже — запрос, который был принят к реализации, со всеми уточнениями.

---

Сделай GigaCode-скилл с именем **`sdd-auto-impr-to-story`**.

Spec-driven конвейер: Improvement → Story → OpenSpec BR/FR → спека кода компонента → генерация кода в репе компонента → PR → финальные статусы.

## Уточнения (обязательны)

- Скилл **для GigaCode**, не для Cursor. Каталог с `SKILL.md` (`name`, `description`) плюс references / assets / scripts.
- MCP **Jira** и MCP **Bitbucket уже настроены**. Не REST, не токены в YAML, не GitHub/GitLab API.
- Forge — **Bitbucket**. Два репозитория из настроек: **репа спек** и **репа компонента**.
- Все параметры — **только из `settings.yaml`**.
- Локальный CLI — JQL, план полей, каркас/валидация OpenSpec. Запись в Jira/Bitbucket — **только MCP**.
- Готовый скилл в каталоге **`sdd-auto-impr-to-story/`**. Копируют в `.gigacode/skills/sdd-auto-impr-to-story/`.
- Не мержить PR самому, пока пользователь не попросил. Статусы менять только после соответствующего merge.

## Этап A — BR/FR (пункты 1–8)

1. Найти задачи в Jira: пространство, тип, метка, статус (`source`).
2. Создать Story: пространство, тип, метка, статус; связь `story.link_type`.
3. Feature-ветка в **репе спек** с ключом Improvement (`bitbucket.source_branch_pattern`, от `bitbucket.default_branch`).
4. По описанию Improvement сгенерировать BR и FR инструментами OpenSpec, commit/push в ветку пункта 3.
5. Создать связанную **таску компонента**: тип, тип связи, компонент (`related`).
6. Feature-ветка с ключом Story в репе спек (`bitbucket.story_branch_pattern`, от default_branch, не от ветки 3).
7. PR: ветка 3 → ветка 6 в репе спек.
8. После merge: Improvement → `after_merge.statuses` (`В работе` / `In Progress`). Story и таску на этом шаге не трогать.

## Этап B — спека кода в репе спек (после пункта 8)

1. Сгенерировать OpenSpec-спеку **изменений кода в рамках компонента** (`code-changes` + `design.md`) по принятым BR/FR.
2. Запушить в feature-ветку **репы спек** с номером таски компонента (`bitbucket.task_branch_pattern`, по умолчанию `feature/{TASK-KEY}`).
3. Создать PR из ветки пункта 2 в ветку с номером Story в той же репе спек.
4. После merge таску взять в работу: статус = `related.in_progress` / `related.in_progress_status`.

## Этап C — код в репе компонента

5. Создать ветку `task` с номером таски в **репозитории компонента** (`component.repository`) от мастер-ветки `component.default_branch`.
6. По спеке этапа B запустить **генерацию кода инструментами OpenSpec** (`openspec instructions apply` и реализация по spec/design).
7. Запушить код в ветку пункта 5.
8. Создать PR из ветки пункта 5 в ветку с номером Story **в том же репозитории компонента**. Ветку Story в репе компонента создать от той же мастер-ветки.
9. После merge статус таски → `related.done` / `related.done_status`.
10. Статус Story → `story.done` / `story.done_status`.
11. Статус Improvement → `improvement_done` / `source.done`.

## `settings.yaml`

Токенов нет.

| Блок | Этап | Поля |
| --- | --- | --- |
| `source` | A1 | `project`, `issue_type`, `label`, `status` |
| `story` | A2, C10 | `project`, `issue_type`, `label`, `status`, `link_type`, `done_status` |
| `bitbucket` | A3–A7, B2–B3 | `repository` (репа спек), `default_branch`, `source_branch_pattern`, `story_branch_pattern`, `task_branch_pattern` |
| `related` | A5, B4, C9 | `issue_type`, `link_type`, `component`, `in_progress_status`, `done_status` |
| `after_merge` | A8 | Improvement в работу после BR/FR |
| `component` | C5–C8 | `repository`, `default_branch` (мастер), `task_branch_pattern`, `story_branch_pattern` |
| `improvement_done` | C11 | финальный статус Improvement |

Идемпотентность: метки `sdd-from-{SOURCE-KEY}`, `sdd-impl-{STORY-KEY}`. Существующие ветки/PR не дублировать.

BR = ценность. FR = наблюдаемое поведение. code-changes = как меняется компонент. Источник BR/FR — описание Improvement. Источник code-changes — принятые BR/FR и компонент.

## MCP и отчёт

Алиасы Jira/Bitbucket; нет tool — стоп, без curl.

Перед записью показать план. Этап B только после merge A7 и A8. Этап C только после merge B3 и B4.

В отчёте: ключи Jira, ветки/PR обеих реп, статусы improvement/story/task.

## Что сдать

- `sdd-auto-impr-to-story/SKILL.md` + references + assets + scripts
- `settings.example.yaml` со всеми новыми параметрами
- README, локальные хелперы и тесты
- **не** свой HTTP к Jira/Bitbucket
