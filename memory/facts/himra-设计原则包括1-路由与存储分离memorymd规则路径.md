---
name: himra-设计原则包括1-路由与存储分离memorymd规则路径
type: fact
triggers:
  descriptive:
    keywords: ["MEMORY.md", "HIMRA"]
    temporal: ['2026-06']
    spatial: []
  associative:
    queries:
      - query: "HIMRA 设计原则包括：1. 路由与存储分离（MEMORY.md=规则+路径，外部文件=实际知识）、2. 懒加载（只加"
        confidence: 0.6
    pathways: []
entities:
  - name: MEMORY.md
    type: concept
    context: 
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
summary: "HIMRA 设计原则包括：1. 路由与存储分离（MEMORY.md=规则+路径，外部文件=实际知识）、2. 懒加载（只加载相关记忆）、3. 有界核心+无界外围（"
version: 4
cross_links: []
---

HIMRA 设计原则包括：1. 路由与存储分离（MEMORY.md=规则+路径，外部文件=实际知识）、2. 懒加载（只加载相关记忆）、3. 有界核心+无界外围（2200字符路由器管理无限知识库）、4. 可解释检索（每次注入都有理由）、5. 优雅降级（嵌入不可用→纯规则，实体索引损坏→纯关键词，永不完全失败）。
