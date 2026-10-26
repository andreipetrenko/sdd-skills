# sdd-auto-impr-to-release

Skill-оркестратор для [GigaCode](https://gitverse.ru/docs/ai/ai-assistant-gigacode/gigacode-for-vscode/skills): в цикле запускает атомарные скиллы каталога.

Исходный запрос для новой сессии: [`PROMPT.md`](PROMPT.md).

Владеет общим `settings.yaml` и `storage.yaml`. Атомарные скиллы их читают. Jira и Bitbucket по-прежнему только через MCP внутри атомарных скиллов.

Порядок в цикле — порядок появления скиллов в репозитории:

1. `sdd-auto-impr-to-story`
2. `sdd-auto-story-to-ift`
3. `sdd-auto-story-to-uat`
4. `sdd-auto-story-to-release`

Условия остановки и расписание оркестратор не задаёт.

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
- в цикле запускает атомарные скиллы по их `SKILL.md`
- не выдумывает шаги, статусы, stop-условия и расписание

## settings.yaml

Один файл на все скиллы. Общие блоки на верхнем уровне. Конфликтующие ключи (`source`, `target`) — в секции с именем скилла. Разбор: `references/settings.md`. Storage: `references/storage.md`.

## Тесты

```bash
python -m pytest
```
