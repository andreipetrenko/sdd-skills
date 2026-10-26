# sdd-skills

Каталог скиллов для [GigaCode](https://gitverse.ru/docs/ai/ai-assistant-gigacode/gigacode-for-vscode/skills).

| Скилл | Назначение |
| --- | --- |
| [`sdd-auto-impr-to-story`](sdd-auto-impr-to-story/) | Improvement → Story → OpenSpec BR/FR → спека кода → код в репе компонента |
| [`sdd-auto-story-to-ift`](sdd-auto-story-to-ift/) | Story → Ready for IFT, если все дочерние Task/Sub-task в статусе «Готов» |
| [`sdd-auto-story-to-uat`](sdd-auto-story-to-uat/) | Story релиза → Ready for UAT, если все PR влиты в `release/<номер>` |
| [`sdd-auto-story-to-release`](sdd-auto-story-to-release/) | Release Story → состав → `release/<номер>` по компонентам и PR каждой Story |
| [`sdd-auto-impr-to-release`](sdd-auto-impr-to-release/) | Оркестратор: атомарные скиллы по именам из `settings.skills`, общий `settings.yaml` и `storage.yaml` |

Промпты для воспроизведения в другой сессии:

- [`sdd-auto-impr-to-story/PROMPT.md`](sdd-auto-impr-to-story/PROMPT.md)
- [`sdd-auto-story-to-ift/PROMPT.md`](sdd-auto-story-to-ift/PROMPT.md)
- [`sdd-auto-story-to-uat/PROMPT.md`](sdd-auto-story-to-uat/PROMPT.md)
- [`sdd-auto-story-to-release/PROMPT.md`](sdd-auto-story-to-release/PROMPT.md)
- [`sdd-auto-impr-to-release/PROMPT.md`](sdd-auto-impr-to-release/PROMPT.md)

Чтобы подключить скилл, скопируйте его папку в `.gigacode/skills/` целевого проекта:

```bash
cp -R sdd-auto-impr-to-story path/to/project/.gigacode/skills/sdd-auto-impr-to-story
cp -R sdd-auto-story-to-ift path/to/project/.gigacode/skills/sdd-auto-story-to-ift
cp -R sdd-auto-story-to-uat path/to/project/.gigacode/skills/sdd-auto-story-to-uat
cp -R sdd-auto-story-to-release path/to/project/.gigacode/skills/sdd-auto-story-to-release
cp -R sdd-auto-impr-to-release path/to/project/.gigacode/skills/sdd-auto-impr-to-release
```

Оркестратор владеет общим `settings.yaml` / `storage.yaml`. Атомарные скиллы читают этот файл (секция с именем скилла + общие блоки).

Jira и Bitbucket должны быть уже подключены к агенту как MCP.
