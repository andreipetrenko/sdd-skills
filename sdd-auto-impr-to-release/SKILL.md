---
name: sdd-auto-impr-to-release
description: >-
  Оркестратор атомарных скиллов каталога: в цикле запускает
  sdd-auto-impr-to-story, sdd-auto-story-to-ift, sdd-auto-story-to-uat,
  sdd-auto-story-to-release. Владеет общим settings.yaml и storage.yaml.
  Jira и Bitbucket только через MCP атомарных скиллов. Используй при
  sdd-auto-impr-to-release, оркестратор SDD, цикл скиллов.
---

# sdd-auto-impr-to-release

Оркестратор SDD-конвейера для агента GigaCode.

Этот каталог копируется в проект как `.gigacode/skills/sdd-auto-impr-to-release/`. Рядом должны лежать атомарные скиллы каталога.

MCP Jira и MCP Bitbucket **уже подключены** к атомарным скиллам. Этот скилл сам не пишет в Jira/Bitbucket. Не спрашивай токены. Не вызывай REST. Не пиши `curl` к `/rest/api`.

Общие параметры — только из **его** `settings.yaml`. Обмен данными между скиллами — только через **его** `storage.yaml`. Схема: `references/settings.md`. Storage: `references/storage.md`.

Локальный CLI запускает существующие `scripts/run.py` атомарных скиллов. Живой конвейер — по `SKILL.md` каждого атомарного скилла.

```bash
python .gigacode/skills/sdd-auto-impr-to-release/scripts/run.py --settings settings.yaml plan
python .gigacode/skills/sdd-auto-impr-to-release/scripts/run.py --settings settings.yaml --storage storage.yaml once
python .gigacode/skills/sdd-auto-impr-to-release/scripts/run.py --settings settings.yaml --storage storage.yaml loop
```

## Когда использовать

Пользователь просит `/sdd-auto-impr-to-release`, прогнать весь SDD-конвейер, крутить атомарные скиллы по кругу.

## Preconditions

1. Есть общий `settings.yaml` (скопируй `assets/settings.example.yaml`, если файла нет). Если найден только example — не пиши в Jira/Bitbucket, попроси заполнить значения.
2. Есть общий `storage.yaml` (скопируй `storage.example.yaml` или дай `--storage`). Атомарные скиллы читают и пишут свои секции.
3. Атомарные скиллы лежат рядом: `sdd-auto-impr-to-story`, `sdd-auto-story-to-ift`, `sdd-auto-story-to-uat`, `sdd-auto-story-to-release`.
4. Перед живой записью каждый атомарный скилл показывает свой план. Если пользователь не подтвердил — остановись после плана.

## Цикл

Порядок — как в каталоге репозитория (порядок появления скиллов):

```
loop:
    sdd-auto-impr-to-story
    sdd-auto-story-to-ift
    sdd-auto-story-to-uat
    sdd-auto-story-to-release
    → снова с первого
```

1. Не добавляй шаги, которых нет в каталоге.
2. Не выдумывай условие остановки цикла и не ставь расписание / sleep.
3. Цикл продолжается, пока пользователь не остановит.
4. На каждой итерации запускай атомарный скилл целиком по его `SKILL.md`. Локальный `once` вызывает существующую команду `plan` каждого `scripts/run.py`.
5. Всем атомарным скиллам передавай **один** `--settings` (этот файл) и **один** `--storage`.
6. `sdd-auto-story-to-release` по-прежнему ждёт ключ release Story (пользователь, CLI или `storage.sdd-auto-story-to-release.release_key`). Не подставляй ключ release-задачи из `sdd-auto-story-to-uat`, если в storage его секции нет.

## Settings и storage

- Settings: `settings.yaml` оркестратора. Атомарные скиллы больше не держат отдельную схему: общий файл + секция с именем скилла для конфликтующих ключей (`source`, `target`).
- Storage: YAML-словарь, ключ = имя скилла. Скилл пишет результат своей команды в свою секцию и может читать чужие.

## Отчёт

После каждой итерации: какие скиллы запускались, код выхода, что записали в storage, какой ключ release Story есть или отсутствует. Не добавляй статусы и переходы, которых нет у атомарных скиллов.
