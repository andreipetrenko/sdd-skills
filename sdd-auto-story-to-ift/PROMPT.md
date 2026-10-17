# Промпт: создать скилл `sdd-auto-story-to-ift`

Вставь этот файл целиком в новую сессию агента. Ниже — запрос, который был принят к реализации, со всеми уточнениями.

---

Сделай GigaCode-скилл с именем **`sdd-auto-story-to-ift`**.

Конвейер: найти Story в Jira → проверить дочерние Task/Sub-task → если все в статусе «Готов» → перевести Story в «Ready for IFT».

## Уточнения (обязательны)

- Скилл **для GigaCode**, не для Cursor. Каталог с `SKILL.md` (`name`, `description`) плюс references / assets / scripts.
- MCP **Jira уже настроен**. Не REST, не токены в YAML.
- Все параметры — **только из `settings.yaml`**.
- Локальный CLI — JQL, план, оценка статусов, выбор перехода. Запись в Jira — **только MCP**.
- Готовый скилл в каталоге **`sdd-auto-story-to-ift/`**. Копируют в `.gigacode/skills/sdd-auto-story-to-ift/`.
- Именование и раскладка как у `sdd-auto-impr-to-story`.

## Pipeline

1. Найти Story: пространство, тип, метка, статус (`source`) — тот же паттерн фильтра, что у существующего скилла.
2. Для каждой Story найти дочерние задачи типов `children.issue_type` (по умолчанию Task / Sub-task / Subtask) через JQL `parent = STORY-KEY`.
3. Если **все** такие дети в `children.ready_status` (по умолчанию `Готов`) — перевести Story в `target.statuses` (по умолчанию `Ready for IFT`).
4. Переход: MCP `transitions`, первое совпадение имени перехода или статуса назначения без учёта регистра, затем MCP `transition`.
5. Нет детей указанного типа, не все готовы или Story уже в целевом статусе — пропустить, не переводить.

## `settings.yaml`

Токенов нет.

| Блок | Поля |
| --- | --- |
| `source` | `project`, `issue_type`, `label`, `status` |
| `children` | `issue_type`, `ready_status` |
| `target` | `statuses` |

## MCP и отчёт

Алиасы Jira; нет tool — стоп, без curl.

Перед записью показать план.

В отчёте: ключи Story, дети и статусы, кого перевели, кого пропустили.

## Что сдать

- `sdd-auto-story-to-ift/SKILL.md` + references + assets + scripts
- `settings.example.yaml` со всеми параметрами
- README, локальные хелперы и тесты
- **не** свой HTTP к Jira
