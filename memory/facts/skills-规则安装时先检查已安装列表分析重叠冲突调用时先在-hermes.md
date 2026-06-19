---
name: skills-规则安装时先检查已安装列表分析重叠冲突调用时先在-hermes
type: fact
triggers:
  descriptive:
    keywords: ["D:\\Obsidian Vault\\Skills and plugins.md", "Hermes skills 库"]
    temporal: ['2026-06']
    spatial: []
  associative:
    queries:
      - query: "Skills 规则：安装时先检查已安装列表分析重叠冲突；调用时先在 Hermes skills 库查找，找不到在 D:\"
        confidence: 0.6
    pathways: []
entities:
  - name: D:\Obsidian Vault\Skills and plugins.md
    type: concept
    context: 
  - name: Hermes skills 库
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
summary: "Skills 规则：安装时先检查已安装列表分析重叠冲突；调用时先在 Hermes skills 库查找，找不到在 D:\Obsidian Vault\Skill"
version: 4
cross_links: []
---

Skills 规则：安装时先检查已安装列表分析重叠冲突；调用时先在 Hermes skills 库查找，找不到在 D:\Obsidian Vault\Skills and plugins.md 模糊搜索；两套系统互通。
