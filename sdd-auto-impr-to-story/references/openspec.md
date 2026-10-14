# OpenSpec BR / FR / code-changes

Генерировать требования только инструментами OpenSpec и форматом delta spec.

## Команды

Если `openspec` установлен в целевом репозитории:

```bash
openspec list --specs
openspec new <change-id>
openspec instructions proposal --change <change-id>
openspec instructions specs --change <change-id>
openspec validate --change <change-id>
```

Для BR/FR `change-id` = kebab-case ключа исходной задачи (`impr-12`).

Для спеки кода `change-id` = kebab-case ключа таски (`dev-55`), паттерн `openspec.implementation_change_id_pattern`.

После спеки кода, в репе компонента:

```bash
openspec instructions apply --change <impl-id>
```

## Обязательные артефакты

```
openspec/changes/<change-id>/
  .openspec.yaml
  proposal.md
  specs/business-requirements/spec.md
  specs/functional-requirements/spec.md

openspec/changes/<task-change-id>/
  .openspec.yaml
  proposal.md
  design.md
  specs/code-changes/spec.md
```

Шаблоны: `assets/openspec/`.

Каждый `spec.md`:

- `## Purpose` (для новой capability)
- `## ADDED Requirements`
- `### Requirement: <name>` + нормативное SHALL/MUST
- минимум один `#### Scenario:` с **GIVEN** / **WHEN** / **THEN**

`#### Scenario:` — ровно четыре `#`. Не три и не список.

## Разделение BR и FR

- `business-requirements` — ценность, акторы, ограничения, критерии приёмки для бизнеса. Без классов, фреймворков и API-методов.
- `functional-requirements` — наблюдаемое поведение системы, входы, выходы, ошибки. Без внутреннего дизайна на этапе BR/FR.
- `code-changes` — как меняется **компонент**. `design.md` пишется на этапе B.

Источник правды для BR/FR — описание задачи пункта 1. Для code-changes — принятые BR/FR плюс скоуп компонента.

Источник правды для текста — описание задачи пункта 1, не выдуманный скоуп.

После записи файлов:

```bash
python .gigacode/skills/sdd-auto-impr-to-story/scripts/run.py validate-specs <SOURCE-KEY> --repo <target-repo>
```
