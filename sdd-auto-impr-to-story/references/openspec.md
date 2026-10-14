# OpenSpec BR / FR

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

`change-id` = kebab-case ключа исходной задачи, например `impr-12`.

## Обязательные артефакты

```
openspec/changes/<change-id>/
  .openspec.yaml
  proposal.md
  specs/business-requirements/spec.md
  specs/functional-requirements/spec.md
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
- `functional-requirements` — наблюдаемое поведение системы, входы, выходы, ошибки. Без внутреннего дизайна (это `design.md`, его этот skill не пишет).

Источник правды для текста — описание задачи пункта 1, не выдуманный скоуп.

После записи файлов:

```bash
python .gigacode/skills/sdd-auto-impr-to-story/scripts/run.py validate-specs <SOURCE-KEY> --repo <target-repo>
```
