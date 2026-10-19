# sdd-auto-release-to-uat

Skill для [GigaCode](https://gitverse.ru/docs/ai/ai-assistant-gigacode/gigacode-for-vscode/skills): переводит release Epic/задачу в `Ready for UAT`, когда **все** Story релиза уже в этом статусе.

Исходный запрос для новой сессии: [`PROMPT.md`](PROMPT.md).

Jira уже должна быть подключена к агенту как MCP. Skill не ходит в REST и не хранит токены.

1. Ищет release Epic/задачу по пространству, типу, метке и статусу из `settings.yaml`
2. Находит Story этого релиза (`parent` и/или `linkedIssues` — как в `sdd-auto-story-to-uat`)
3. Если **все** такие Story в `stories.ready_status` (`Ready for UAT` по умолчанию) — переводит Epic/задачу в `target.statuses` (`Ready for UAT` по умолчанию)
4. Если Story нет, не все готовы или Epic уже в целевом статусе — пропускает и пишет причину

## Быстрый старт

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp settings.example.yaml settings.yaml
```

Заполните `settings.yaml`. Секреты не нужны: агент GigaCode вызывает уже настроенный MCP Jira.

```bash
python -m sdd_auto_release_to_uat --settings settings.yaml jql
python -m sdd_auto_release_to_uat --settings settings.yaml plan
python -m sdd_auto_release_to_uat --settings settings.yaml stories-jql REL-12
python -m sdd_auto_release_to_uat --settings settings.yaml evaluate REL-12 \
  --release-status "In Progress" --story DEV-40:Ready for UAT --story DEV-41:Ready for UAT
```

То же через обёртку skill:

```bash
python scripts/run.py --settings settings.yaml plan
```

## GigaCode skill

Скопируйте папку в `.gigacode/skills/sdd-auto-release-to-uat/` целевого проекта. В агенте вызовите `/sdd-auto-release-to-uat`.

## settings.yaml

| Блок | Этап | Поля |
| --- | --- | --- |
| `source` | 1 | `project`, `issue_type`, `label`, `status` — фильтр Epic/задачи релиза |
| `stories` | 2–3 | `issue_type`, `via`, `ready_status` |
| `target` | 4 | `statuses` — целевой статус Epic/задачи |

Полный пример — `settings.example.yaml`. Разбор полей — `references/settings.md`.

## Тесты

```bash
python -m pytest
```
