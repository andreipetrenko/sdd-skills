# Промпт: создать скилл `sdd-auto-story-to-release`

Вставь этот файл целиком в новую сессию агента. Ниже — запрос, который был принят к реализации.

---

Сделай GigaCode-скилл с именем **`sdd-auto-story-to-release`**.

Вход: номер release Story. Состав: дочерние/связанные Story и Jira Component (как уже умеют скиллы каталога). Создать release-ветку на каждый компонент. Создать PR каждой Story в соответствующую release-ветку.

## Уточнения (обязательны)

- Скилл **для GigaCode**. Каталог с `SKILL.md` плюс references / assets / scripts.
- MCP **Jira** и MCP **Bitbucket уже настроены**. Не REST, не токены.
- Вход — ключ Story, не поиск всех релизов.
- Состав Story — как `sdd-auto-story-to-uat` (`parent` / `linkedIssues`).
- Component — поле Jira, как `sdd-auto-impr-to-story`.
- Имя release-ветки — как `sdd-auto-story-to-uat`: `release/{number}`. Не придумывай новый паттерн.
- Локальный CLI — JQL, номер, compose/plan. Ветки и PR — **только MCP**.
- Не меняй статусы Jira. Не мержь PR.
- Не угадывай репу по имени компонента, если её нет в settings.
- Заменить выдуманный `sdd-auto-release-to-uat`, не оставлять старое поведение.

## `settings.yaml`

`stories`, `release.branch_pattern`, `components` / `component` + `related.component`.

## Что сдать

- `sdd-auto-story-to-release/SKILL.md` + references + assets + scripts
- `settings.example.yaml`, README, тесты
- удалить `sdd-auto-release-to-uat`
- **не** свой HTTP к Jira/Bitbucket
