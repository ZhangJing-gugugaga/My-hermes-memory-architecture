---
name: himra-有两个分支main-分支是-v1-初始版本纯规则路由rag-
type: fact
triggers:
  descriptive:
    keywords: ["rag-integration", "SPEC.md", "HIMRA", "main"]
    temporal: ['2026-06']
    spatial: []
  associative:
    queries:
      - query: "HIMRA 有两个分支：main 分支是 v1 初始版本（纯规则路由），rag-integration 分支是最新版本（"
        confidence: 0.6
    pathways: []
entities:
  - name: rag-integration
    type: concept
    context: 
  - name: SPEC.md
    type: concept
    context: 
  - name: HIMRA
    type: concept
    context: 
  - name: main
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
summary: "HIMRA 有两个分支：main 分支是 v1 初始版本（纯规则路由），rag-integration 分支是最新版本（v3 完整五组件+四阶段流水线+SPEC"
version: 4
cross_links: []
---

HIMRA 有两个分支：main 分支是 v1 初始版本（纯规则路由），rag-integration 分支是最新版本（v3 完整五组件+四阶段流水线+SPEC.md 文件格式规范）。
