# sdd-auto-impr-to-release

Skill-оркестратор для [GigaCode](https://gitverse.ru/docs/ai/ai-assistant-gigacode/gigacode-for-vscode/skills): в цикле запускает атомарные скиллы каталога.

Исходный запрос для новой сессии: [`PROMPT.md`](PROMPT.md).

Владеет общим `settings.yaml` и `storage.yaml`. Подключённые скиллы их читают. Jira и Bitbucket по-прежнему только через MCP внутри этих скиллов.

`settings.skills` — имена атомарных скиллов, не pipeline. В примере:

- `sdd-auto-impr-to-story`
- `sdd-auto-story-to-ift`
- `sdd-auto-story-to-uat`
- `sdd-auto-story-to-release`

Имя резолвится в `<имя>/scripts/run.py` рядом с оркестратором. Добавление или удаление — правка `skills`, не кода. Условия остановки и расписание оркестратор не задаёт.

## Быстрый старт

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp settings.example.yaml settings.yaml
cp storage.example.yaml storage.yaml
```

Заполните `settings.yaml`. Секреты не нужны.

Локальный CLI читает общий файл, печатает план цикла и вызывает `scripts/run.py` атомарных скиллов:

```bash
python -m sdd_auto_impr_to_release --settings settings.yaml plan
python -m sdd_auto_impr_to_release --settings settings.yaml --storage storage.yaml once
python -m sdd_auto_impr_to_release --settings settings.yaml --storage storage.yaml loop
```

То же через обёртку skill:

```bash
python scripts/run.py --settings settings.yaml plan
```

## GigaCode skill

Скопируйте эту папку и атомарные скиллы в `.gigacode/skills/` целевого проекта. В агенте вызовите `/sdd-auto-impr-to-release`.

Агент:

- читает общий `settings.yaml` и `storage.yaml`
- в цикле запускает скиллы из `settings.skills` по их `SKILL.md`
- не выдумывает шаги, статусы, stop-условия и расписание

## settings.yaml

Один файл на все скиллы. `skills` — список имён. Общие блоки на верхнем уровне. Конфликтующие ключи (`source`, `target`) — в секции с именем скилла. Разбор: `references/settings.md`. Storage: `references/storage.md`.

## Тесты

```bash
python -m pytest
```
