# storage.yaml

Владелец файла — `sdd-auto-impr-to-release`. Атомарные скиллы читают и пишут свои секции.

Путь: `storage.path` в settings, иначе `storage.yaml` рядом, иначе `--storage PATH`.

Токены не клади.

## Форма

YAML-словарь. Ключ верхнего уровня — имя скилла.

```yaml
sdd-auto-impr-to-story:
  command: plan
  output: {}
sdd-auto-story-to-ift: {}
sdd-auto-story-to-uat: {}
sdd-auto-story-to-release:
  release_key: REL-12
```

После локальной команды скилл дописывает в свою секцию:

- `command` — имя команды CLI
- `output` — JSON stdout или текст
- `exit_code` — если запускал оркестратор

Дополнительные ключи, которые скилл уже знает как вход:

- `sdd-auto-story-to-release.release_key` — ключ release Story для CLI, если аргумент не передан

Оркестратор не выдумывает соответствие ключа release-задачи (`sdd-auto-story-to-uat`) ключу release Story.
