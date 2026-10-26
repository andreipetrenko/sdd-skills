# sdd-auto-story-to-ift

Skill для [GigaCode](https://gitverse.ru/docs/ai/ai-assistant-gigacode/gigacode-for-vscode/skills): переводит Story в `Ready for IFT`, когда все дочерние Task/Sub-task в статусе `Готов`.

Исходный запрос для новой сессии: [`PROMPT.md`](PROMPT.md).

Jira уже должна быть подключена к агенту как MCP. Skill не ходит в REST и не хранит токены.

Настройки — общий `settings.yaml` оркестратора `sdd-auto-impr-to-release` (секция `sdd-auto-story-to-ift`). Обмен с другими скиллами — `storage.yaml` (`--storage`).

1. Ищет Story по пространству, типу, метке и статусу из `settings.yaml`
2. Для каждой найденной собирает дочерние задачи типов из `children.issue_type`
3. Если **все** такие дети в ready-статусе (`Готов` по умолчанию) — переводит Story в `target.statuses` (`Ready for IFT` по умолчанию)
4. Если детей нет, не все готовы или Story уже в целевом статусе — пропускает задачу и пишет причину

## Быстрый старт

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp settings.example.yaml settings.yaml
```

Заполните `settings.yaml`. Секреты не нужны: агент GigaCode вызывает уже настроенный MCP Jira.

Локальный CLI только читает настройки, печатает JQL/план и оценивает статусы:

```bash
python -m sdd_auto_story_to_ift --settings settings.yaml jql
python -m sdd_auto_story_to_ift --settings settings.yaml plan
python -m sdd_auto_story_to_ift --settings settings.yaml children-jql DEV-40
python -m sdd_auto_story_to_ift --settings settings.yaml evaluate DEV-40 \
  --story-status "In Progress" --child DEV-41:Готов --child DEV-42:Готов
```

То же через обёртку skill:

```bash
python scripts/run.py --settings settings.yaml plan
```

В проекте, куда скилл скопирован как `.gigacode/skills/sdd-auto-story-to-ift/`:

```bash
python .gigacode/skills/sdd-auto-story-to-ift/scripts/run.py --settings settings.yaml plan
```

## GigaCode skill

Чтобы подключить скилл, скопируйте эту папку в `.gigacode/skills/sdd-auto-story-to-ift/` целевого проекта. В агенте вызовите `/sdd-auto-story-to-ift` или опишите Story→Ready for IFT.

Агент:

- читает `settings.yaml`
- ищет Story и детей **только через Jira MCP**
- статусы Jira меняет только через `transitions` + `transition`
- не переводит Story, пока не все подходящие дети в ready-статусе

## settings.yaml

| Блок | Этап | Поля |
| --- | --- | --- |
| `source` | 1 | `project`, `issue_type`, `label`, `status` |
| `children` | 2–3 | `issue_type`, `ready_status` |
| `target` | 4 | `statuses` — целевой статус Story |

Полный пример — `settings.example.yaml`. Разбор полей — `references/settings.md`.

## Тесты

```bash
python -m pytest
```
