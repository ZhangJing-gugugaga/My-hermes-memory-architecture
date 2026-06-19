---
name: himrahierarchical-indexed-memory-retrie
type: fact
triggers:
  descriptive:
    keywords: ["MEMORY.md", "用户", "HIMRA"]
    temporal: ['2026-06']
    spatial: []
  associative:
    queries:
      - query: "HIMRA（Hierarchical Indexed Memory Retrieval Architecture）是用户"
        confidence: 0.6
      - query: "| Involving: 用户"
        confidence: 0.6
    pathways: []
entities:
  - name: MEMORY.md
    type: concept
    context: 
  - name: 用户
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
summary: "HIMRA（Hierarchical Indexed Memory Retrieval Architecture）是用户设计的 Agent 记忆架构，核心思想是"
version: 4
cross_links: []
---

HIMRA（Hierarchical Indexed Memory Retrieval Architecture）是用户设计的 Agent 记忆架构，核心思想是把 MEMORY.md 从存储容器变成多阶段检索路由器，用 2200 字符的路由规则管理无限知识库。 | Involving: 用户
