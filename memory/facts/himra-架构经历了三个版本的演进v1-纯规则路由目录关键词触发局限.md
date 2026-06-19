---
name: himra-架构经历了三个版本的演进v1-纯规则路由目录关键词触发局限
type: fact
triggers:
  descriptive:
    keywords: ["HIMRA", "RAG-Anything", "HKUDS 2025"]
    temporal: ['2026-06']
    spatial: []
  associative:
    queries:
      - query: "HIMRA 架构经历了三个版本的演进：v1 纯规则路由（目录+关键词触发，局限：同义词盲区），v2 实体增强（LLM 提"
        confidence: 0.6
    pathways: []
entities:
  - name: HIMRA
    type: concept
    context: 
  - name: RAG-Anything
    type: concept
    context: 
  - name: HKUDS 2025
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
summary: "HIMRA 架构经历了三个版本的演进：v1 纯规则路由（目录+关键词触发，局限：同义词盲区），v2 实体增强（LLM 提取实体索引，局限：无关系感知），v3 图"
version: 4
cross_links: []
---

HIMRA 架构经历了三个版本的演进：v1 纯规则路由（目录+关键词触发，局限：同义词盲区），v2 实体增强（LLM 提取实体索引，局限：无关系感知），v3 图增强混合（实体图+嵌入回退，灵感来自 RAG-Anything HKUDS 2025）。
