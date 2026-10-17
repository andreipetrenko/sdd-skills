# sdd-skills

Каталог скиллов для [GigaCode](https://gitverse.ru/docs/ai/ai-assistant-gigacode/gigacode-for-vscode/skills).

| Скилл | Назначение |
| --- | --- |
| [`sdd-auto-impr-to-story`](sdd-auto-impr-to-story/) | Improvement → Story → OpenSpec BR/FR → спека кода → код в репе компонента |
| [`sdd-auto-story-to-ift`](sdd-auto-story-to-ift/) | Story → Ready for IFT, если все дочерние Task/Sub-task в статусе «Готов» |

Промпты для воспроизведения в другой сессии:

- [`sdd-auto-impr-to-story/PROMPT.md`](sdd-auto-impr-to-story/PROMPT.md)
- [`sdd-auto-story-to-ift/PROMPT.md`](sdd-auto-story-to-ift/PROMPT.md)

Чтобы подключить скилл, скопируйте его папку в `.gigacode/skills/` целевого проекта:

```bash
cp -R sdd-auto-impr-to-story path/to/project/.gigacode/skills/sdd-auto-impr-to-story
cp -R sdd-auto-story-to-ift path/to/project/.gigacode/skills/sdd-auto-story-to-ift
```

Jira и Bitbucket должны быть уже подключены к агенту как MCP.
