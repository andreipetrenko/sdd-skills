# Промпт: создать скилл `sdd-auto-impr-to-story`

Вставь этот файл целиком в новую сессию агента. Ниже — запрос, который был принят к реализации, со всеми уточнениями.

---

Сделай GigaCode-скилл с именем **`sdd-auto-impr-to-story`**.

Это spec-driven конвейер: Improvement из Jira → Story → бизнес- и функциональные требования в OpenSpec → ветки Bitbucket → pull request.

## Уточнения (обязательны)

- Скилл **для GigaCode**, не для Cursor. Формат: каталог с `SKILL.md` (YAML frontmatter: `name`, `description`) плюс references / assets / scripts.
- MCP **Jira** и MCP **Bitbucket уже настроены** на агенте. Не пиши REST-клиенты, не проси токены, не клади секреты в YAML, не вызывай GitHub / GitLab / GitVerse API.
- Forge — **Bitbucket**. URL репозитория — из `settings.yaml`.
- Все параметры рабочего цикла — **только из `settings.yaml`**. Не выдумывай project / type / label / status / component / repository.
- Локальный CLI — только чтение настроек, JQL, план полей и каркас/валидация OpenSpec. Запись в Jira и Bitbucket — **только MCP**.
- Готовый скилл положи в каталог с **наименованием скилла**: `sdd-auto-impr-to-story/` (каталог скиллов: одна папка = один скилл). Чтобы подключить, папку копируют в `.gigacode/skills/sdd-auto-impr-to-story/` целевого проекта.

## Пайплайн (ровно 8 пунктов)

Для каждой найденной исходной задачи:

1. **Найти задачи в Jira** по `settings.yaml`: пространство (project/space), тип, метка, статус.
2. **Создать новую задачу (Story)** по `settings.yaml`: пространство, тип, метка, статус. Связать со исходной типом связи из настроек.
3. **Создать feature-ветку** в репозитории из настроек. Имя ветки содержит ключ задачи пункта 1 (по умолчанию `feature/{SOURCE-KEY}`). Ветка от `default_branch`.
4. По **описанию исходной задачи** сгенерировать **бизнес- и функциональные требования** инструментами OpenSpec (`openspec new` / `instructions` / `validate`). Формат delta spec: `### Requirement:` + SHALL/MUST и `#### Scenario:` с GIVEN / WHEN / THEN. Файлы:
   - `openspec/changes/<change-id>/proposal.md`
   - `openspec/changes/<change-id>/specs/business-requirements/spec.md`
   - `openspec/changes/<change-id>/specs/functional-requirements/spec.md`  
   `change-id` = kebab-case ключа исходной задачи. Commit и push **в ветку пункта 3**.
5. Для Story из пункта 2 **создать связанную задачу**: тип, тип связи и компонент изменения — из `settings.yaml`. Если у исходной задачи уже есть Component и включён `component_from_source`, взять его.
6. **Создать feature-ветку** с ключом Story пункта 2 в том же репозитории (по умолчанию `feature/{STORY-KEY}`). Ветка от `default_branch`, **не** от ветки пункта 3 — иначе PR будет пустым.
7. Открыть **pull request из ветки пункта 3 в ветку пункта 6** (head = Improvement, base = Story). Не в `main`, если это не `story_branch_pattern`.
8. **После merge** перевести исходную задачу пункта 1 в статус **`В работе` / `In Progress`** (первое совпадение имени перехода без учёта регистра). Не менять статус до merge. Не менять статус Story и related-задачи. Не мержить PR самому, пока пользователь не попросил.

## `settings.yaml`

Пример и схема обязательны. Токенов в файле нет.

| Блок | Пункт | Поля |
| --- | --- | --- |
| `source` | 1 | `project` (пространство) / `space`, `issue_type` / `type`, `label`, `status` |
| `story` | 2 | `project`, `issue_type`, `label`, `status`, `link_type` |
| `bitbucket` | 3, 6, 7 | `repository`, `default_branch`, `source_branch_pattern`, `story_branch_pattern` |
| `related` | 5 | `issue_type`, `link_type`, `component`, `component_from_source` |
| `after_merge` | 8 | `statuses`: `В работе`, `In Progress` |

Дополнительно:

- служебная метка Story: `sdd-from-{SOURCE-KEY}` — идемпотентность пункта 2;
- служебная метка related: `sdd-impl-{STORY-KEY}` — идемпотентность пункта 5;
- `openspec.capabilities`: `business-requirements`, `functional-requirements`;
- `limits.max_issues`.

BR = ценность, акторы, ограничения. FR = наблюдаемое поведение. Без классов, фреймворков и плана реализации. Источник скоупа — описание задачи пункта 1.

## MCP

Агент выбирает инструменты по алиасам (camelCase и snake_case): поиск/создание/линк/переходы Jira; создание ветки и PR Bitbucket. Нет совпадения — остановиться и назвать недостающее действие, не подставлять `curl`.

## Поведение агента

- Перед живой записью показать план (JQL и список ключей). Без подтверждения не писать в Jira/Bitbucket.
- Пустой поиск — остановиться, не расширять JQL.
- Ошибка одной задачи не отменяет отчёт по остальным.
- В отчёте: source, story, related, source_branch, story_branch, PR URL, исходная «в работе» да/нет.

## Что сдать

- `sdd-auto-impr-to-story/SKILL.md` + `references/` + `assets/` + `scripts/`
- `settings.example.yaml`
- README: что делает скилл и как запустить (`/sdd-auto-impr-to-story` в GigaCode)
- локальные хелперы (JQL / plan / OpenSpec) и тесты на них
- **не** реализовывать собственный HTTP к Jira/Bitbucket
