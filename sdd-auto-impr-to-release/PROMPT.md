# Промпт: создать скилл `sdd-auto-impr-to-release`

Вставь этот файл целиком в новую сессию агента. Ниже — запрос, который был принят к реализации.

---

Сделай GigaCode-скилл-оркестратор с именем **`sdd-auto-impr-to-release`**.

Имя как у соседей: `sdd-auto-<from>-to-<to>` (Improvement → release).

## Уточнения (обязательны)

- Скилл **для GigaCode**. Каталог с `SKILL.md` плюс references / assets / scripts.
- Это **оркестратор**. Он работает **в цикле**.
- Скиллы **подключаются через settings** (`skills`: только имена). Число скиллов любое. Добавить/убрать — правка settings, не кода.
- Скиллы атомарные: список имён не задаёт порядок конвейера.
- Внутри цикла запускает скиллы из этого списка. Имя → `<имя>/scripts/run.py` в репозитории.
- Владеет **общим settings.yaml**, который читают остальные скиллы.
- Владеет **общим storage.yaml** для передачи данных между скиллами.
- Обнови атомарные скиллы: они читают общий settings и умеют читать/писать storage. Второй конфликтующей схемы settings не оставляй.
- Не выдумывай условие остановки цикла, расписание и атомарные шаги, которых нет в репозитории.
- MCP Jira/Bitbucket — только внутри атомарных скиллов. Не REST, не токены.
- Локальный CLI — plan / once / loop. Запись в Jira/Bitbucket — **только MCP** атомарных скиллов.
- Не мержить в `main`.

## `settings.skills`

Только имена, не path. Пример:

- `sdd-auto-impr-to-story`
- `sdd-auto-story-to-ift`
- `sdd-auto-story-to-uat`
- `sdd-auto-story-to-release`

## `settings.yaml`

Один файл. `skills` — список имён. Общие блоки наверху. Конфликтующие `source` / `target` — в секции с именем скилла.

## `storage.yaml`

YAML-словарь, ключ = имя скилла. Скилл пишет результат команды в свою секцию.

## Что сдать

- `sdd-auto-impr-to-release/SKILL.md` + references + assets + scripts
- общий `settings.example.yaml` / `storage.example.yaml`
- обновление атомарных скиллов
- README, тесты
- **не** свой HTTP к Jira/Bitbucket
- **не** merge в `main`
