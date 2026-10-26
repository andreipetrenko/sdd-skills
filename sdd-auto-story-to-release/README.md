# sdd-auto-story-to-release

Skill для [GigaCode](https://gitverse.ru/docs/ai/ai-assistant-gigacode/gigacode-for-vscode/skills): по номеру release Story собирает состав, создаёт `release/<номер>` в репе каждого компонента и открывает PR каждой Story в эту ветку.

Исходный запрос для новой сессии: [`PROMPT.md`](PROMPT.md).

Jira и Bitbucket уже должны быть подключены к агенту как MCP. Skill не ходит в REST и не хранит токены.

Настройки — общий `settings.yaml` оркестратора `sdd-auto-impr-to-release`. Ключ release Story — CLI или `storage.sdd-auto-story-to-release.release_key`.

1. Принимает ключ release Story (вход пользователя, не JQL-поиск релиза)
2. Ищет дочерние/связанные Story так же, как `sdd-auto-story-to-uat`
3. Берёт Jira Component каждой Story так же, как `sdd-auto-impr-to-story`
4. Создаёт ветку `release/{number}` (паттерн skill 2) в репозитории компонента
5. Открывает PR `feature/{STORY-KEY}` → `release/{number}` на каждую пару Story × компонент

## Быстрый старт

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp settings.example.yaml settings.yaml
```

```bash
python -m sdd_auto_story_to_release --settings settings.yaml plan
python -m sdd_auto_story_to_release --settings settings.yaml stories-jql REL-12
python -m sdd_auto_story_to_release --settings settings.yaml compose REL-12 \
  --release-number 1.2 --story DEV-40:backend --story DEV-41:ui
```

## settings.yaml

| Блок | Смысл |
| --- | --- |
| `stories` | состав: `issue_type`, `via` (`parent` / `linked` / `both`) |
| `release` | `number`, `branch_pattern` = `release/{number}` |
| `components` / `component` | имя Jira Component + `repository` + `default_branch` |
| `related.component` | fallback имени компонента, как в impr-to-story |

Полный пример — `settings.example.yaml`. Разбор — `references/settings.md`.

## Тесты

```bash
python -m pytest
```
