# HIMRA - Memory File Format Specification

This document defines the YAML frontmatter schema for all memory files in the HIMRA system.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier for the memory file |
| `triggers` | string[] | Keywords that activate this memory |
| `always_load` | boolean | If true, loaded every turn regardless of query |
| `priority` | enum | `high` / `medium` / `low` |
| `updated` | date | Last modification date (YYYY-MM-DD) |
| `summary` | string | One-line description of contents |

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `version` | integer | Schema version (default: 1) |
| `supersedes` | string | Name of a previous file this replaces |
| `expires` | date | Auto-archive after this date |
| `access_count` | integer | Number of times loaded (for analytics) |

## Example

```yaml
---
name: server-configuration
triggers:
  - 服务器
  - ECS
  - SSH
  - 安全组
  - swap
  - systemd
  - gateway
  - server
  - 阿里云
  - Aliyun
always_load: false
priority: medium
updated: 2026-06-18
summary: 阿里云 ECS 服务器配置和部署历史
version: 3
---
```

## Trigger Best Practices

1. Include both Chinese and English variants
2. Include common misspellings and abbreviations
3. Include brand names (e.g., "阿里云", "Aliyun")
4. Include tool names (e.g., "systemd", "gateway")
5. Keep each file's trigger list under 20 entries for manageability
