# settings.yaml

Владелец файла — `sdd-auto-impr-to-release`. Атомарные скиллы читают **этот** файл.

Путь по умолчанию: `settings.yaml` в корне репозитория или в каталоге оркестратора. Переопределение: `--settings PATH`.

Токены и URL MCP в YAML не клади.

## Каталог (`skills`)

Список **имён** атомарных скиллов. Не path и не `{id, path}`. Список не задаёт порядок конвейера: каждый скилл атомарный.

Имя резолвится в существующий каталог репозитория: `<имя>/scripts/run.py` рядом с оркестратором (корень каталога или `.gigacode/skills/`).

Добавить или убрать скилл — изменить этот список, не код.

Синоним ключа: `skill`.

## Одна схема

Конфликтующие ключи (`source`, `target`) не живут на верхнем уровне: у каждого скилла своя секция с его именем. Общие блоки — наверху и читаются всеми, кому они нужны.

Верхний уровень (как в атомарных скиллах):

| Блок | Кто читает |
| --- | --- |
| `jira` | все |
| `bitbucket` | impr-to-story (репа спек); story-to-uat (плюс `repositories`) |
| `component` / `components` | impr-to-story, story-to-release; story-to-uat как доп. репы |
| `related` | impr-to-story, story-to-release |
| `stories` | story-to-uat, story-to-release |
| `release` | story-to-uat, story-to-release |
| `pr` | story-to-uat |
| `after_merge`, `improvement_done`, `openspec` | impr-to-story |
| `limits` | все |
| `skills` | оркестратор (каталог) |
| `storage.path` | оркестратор и подключённые скиллы |

Секции скиллов:

| Секция | Поля |
| --- | --- |
| `sdd-auto-impr-to-story` | `source`, `story` |
| `sdd-auto-story-to-ift` | `source`, `children`, `target` |
| `sdd-auto-story-to-uat` | `source`, `children`, `target` |
| `sdd-auto-story-to-release` | пустая, если хватает общих `stories` / `release` / `component` |

Атомарный `parse_settings` берёт верхний уровень, выбрасывает чужие секции и накладывает свою.

Смысл полей — в `references/settings.md` соответствующего атомарного скилла. Здесь они не переопределяются.
