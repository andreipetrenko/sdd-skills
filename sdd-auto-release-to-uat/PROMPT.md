# Промпт: создать скилл `sdd-auto-release-to-uat`

Вставь этот файл целиком в новую сессию агента. Ниже — запрос, который был принят к реализации.

---

Сделай GigaCode-скилл с именем **`sdd-auto-release-to-uat`**.

Конвейер: найти release Epic/задачу → Story этого релиза → если все в «Ready for UAT» → перевести Epic/задачу в «Ready for UAT».

## Уточнения (обязательны)

- Скилл **для GigaCode**. Каталог с `SKILL.md` плюс references / assets / scripts.
- MCP **Jira уже настроен**. Не REST, не токены в YAML.
- Все параметры — **только из `settings.yaml`**.
- Локальный CLI — JQL, план, оценка статусов. Запись — **только MCP**.
- Готовый скилл в каталоге **`sdd-auto-release-to-uat/`**.
- Именование как у `sdd-auto-impr-to-story`, `sdd-auto-story-to-ift`, `sdd-auto-story-to-uat`.
- Поиск релиза — тот же фильтр, что у `sdd-auto-story-to-uat` (`source`: project / type / label / status).
- Story релиза — тот же подход (`parent` и/или `linkedIssues`).
- Пустой набор Story ≠ все готовы: не переводить Epic.

## Pipeline

1. Найти Epic/задачу релиза: пространство, тип, метка, статус (`source`).
2. Найти Story: `stories.via` = parent / linked / both.
3. Если **все** Story в `stories.ready_status` (по умолчанию `Ready for UAT`) — перевести Epic в `target.statuses` (по умолчанию `Ready for UAT`).
4. Переход: MCP `transitions` + первое совпадение + MCP `transition`.

## `settings.yaml`

Токенов нет. `source`, `stories`, `target`.

## Что сдать

- `sdd-auto-release-to-uat/SKILL.md` + references + assets + scripts
- `settings.example.yaml`, README, тесты
- **не** свой HTTP к Jira
