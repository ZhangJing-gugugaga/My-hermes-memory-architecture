---
name: hindsight-记忆系统已配置使用-deepseek-apilocalh
type: fact
triggers:
  descriptive:
    keywords: ["Hindsight", "D:\\hindsight", "DeepSeek API", "localhost:9177"]
    temporal: ['2026-06']
    spatial: []
  associative:
    queries:
      - query: "Hindsight 记忆系统已配置，使用 DeepSeek API，localhost:9177，安装在 D:\hind"
        confidence: 0.6
      - query: "memory provider=hindsight，flush_min_turns=15"
        confidence: 0.6
    pathways: []
entities:
  - name: Hindsight
    type: concept
    context: 
  - name: D:\hindsight
    type: concept
    context: 
  - name: DeepSeek API
    type: concept
    context: 
  - name: localhost:9177
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
summary: "Hindsight 记忆系统已配置，使用 DeepSeek API，localhost:9177，安装在 D:\hindsight。memory provide"
version: 4
cross_links: []
---

Hindsight 记忆系统已配置，使用 DeepSeek API，localhost:9177，安装在 D:\hindsight。memory provider=hindsight，flush_min_turns=15。
