# Промпт: создать скилл `sdd-auto-story-to-uat`

Вставь этот файл целиком в новую сессию агента. Ниже — запрос, который был принят к реализации.

---

Сделай GigaCode-скилл с именем **`sdd-auto-story-to-uat`**.

Конвейер: найти release-задачу → Story этого релиза → PR каждой Story → если все учтённые PR влиты в `release/<номер>` → перевести эту Story в «Ready for UAT».

## Уточнения (обязательны)

- Скилл **для GigaCode**. Каталог с `SKILL.md` плюс references / assets / scripts.
- MCP **Jira** и MCP **Bitbucket уже настроены**. Не REST, не токены в YAML.
- Все параметры — **только из `settings.yaml`**.
- Локальный CLI — JQL, номер релиза, план, оценка PR. Запись — **только MCP**.
- Готовый скилл в каталоге **`sdd-auto-story-to-uat/`**.
- Именование как у `sdd-auto-impr-to-story` и `sdd-auto-story-to-ift`.
- Переводить **каждую** готовую Story, не ждать весь релиз.

## Pipeline

1. Найти release-задачу: пространство, тип, метка, статус (`source`).
2. Номер релиза: `release.number` / поле / summary.
3. Story релиза: `parent` и/или `linkedIssues` (`stories.via`).
4. PR Story (и детей) через Bitbucket MCP `list_prs`.
5. Все учтённые PR MERGED в ветку по `release.branch_pattern` (`release/{number}`) — перевести Story в `target.statuses` (`Ready for UAT`).
6. Переход: MCP `transitions` + первое совпадение + MCP `transition`.

## `settings.yaml`

Токенов нет. `source`, `stories`, `release`, `bitbucket`, `pr`, `target`.

## Что сдать

- `sdd-auto-story-to-uat/SKILL.md` + references + assets + scripts
- `settings.example.yaml`, README, тесты
- **не** свой HTTP к Jira/Bitbucket
