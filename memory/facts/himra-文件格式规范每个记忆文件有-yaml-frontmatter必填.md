---
name: himra-文件格式规范每个记忆文件有-yaml-frontmatter必填
type: fact
triggers:
  descriptive:
    keywords: ["HIMRA"]
    temporal: ['2026-06']
    spatial: []
  associative:
    queries:
      - query: "HIMRA 文件格式规范：每个记忆文件有 YAML frontmatter，必填字段包括 name（唯一标识）、trig"
        confidence: 0.6
    pathways: []
entities:
  - name: HIMRA
    type: concept
    context: 
temporal:
  valid_from: 2026-06-18
  valid_until: null
  observed_at: 2026-06-18
  event_time: 2026-06-18
always_load: false
priority: medium
updated: 2026-06-18
summary: "HIMRA 文件格式规范：每个记忆文件有 YAML frontmatter，必填字段包括 name（唯一标识）、triggers（触发关键词数组，需包含中英文变"
version: 4
cross_links: []
---

HIMRA 文件格式规范：每个记忆文件有 YAML frontmatter，必填字段包括 name（唯一标识）、triggers（触发关键词数组，需包含中英文变体、常见缩写、品牌名）、always_load（是否每轮加载）、priority（high/medium/low）、updated（更新日期）、summary（一行描述）；可选字段包括 version、supersedes（替代旧文件）、expires（过期日期）、access_count。
