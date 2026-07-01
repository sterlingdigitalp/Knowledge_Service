# Intelligence Profiles

An Intelligence Profile defines what the system should collect before intelligence extraction begins.

## Schema
- `name`, `description`, `profile_id`
- optional `icon`, `color`
- `enabled`
- editable `interests`
- profile-local `watch_list`
- required, optional, and ignored podcast lists

## Watch List Entry
- `display_name`
- `aliases`
- `organization`
- `source_handles`
- `enabled`
- `priority`

## Podcast Lists
- Required podcasts are always collected when enabled.
- Optional podcasts are collected when an episode matches interests or watched people.
- Ignore podcasts suppress matching required/optional entries.
- Each podcast supports enable/disable, priority, polling interval, discovery mode, and maximum episodes per run.

## Import And Export
Use `knowledge_service.intelligence.config.load_profiles()` and `save_profiles()`.

Supported formats:
- JSON
- YAML when PyYAML is available
- JSON-compatible YAML when PyYAML is not installed

## Certification Profiles
The Phase 3 certifier demonstrates four simultaneous profiles:
- AI
- Investing
- Founders
- Longevity
