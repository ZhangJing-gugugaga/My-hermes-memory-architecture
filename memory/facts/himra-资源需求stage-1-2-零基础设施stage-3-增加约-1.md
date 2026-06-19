---
name: himra-资源需求stage-1-2-零基础设施stage-3-增加约-1
type: fact
triggers:
  descriptive:
    keywords: ["HIMRA", "JSON 图", "BGE-small", "FAISS"]
    temporal: ['2026-06']
    spatial: []
  associative:
    queries:
      - query: "HIMRA 资源需求：Stage 1-2 零基础设施，Stage 3 增加约 150MB RAM（FAISS+BGE-s"
        confidence: 0.6
      - query: "| 对比向量数据库方案（1-2GB RAM）资源效率高 10 倍"
        confidence: 0.6
    pathways: []
entities:
  - name: HIMRA
    type: concept
    context: 
  - name: JSON 图
    type: concept
    context: 
  - name: BGE-small
    type: concept
    context: 
  - name: FAISS
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
summary: "HIMRA 资源需求：Stage 1-2 零基础设施，Stage 3 增加约 150MB RAM（FAISS+BGE-small），Stage 4 增加约 10"
version: 4
cross_links: []
---

HIMRA 资源需求：Stage 1-2 零基础设施，Stage 3 增加约 150MB RAM（FAISS+BGE-small），Stage 4 增加约 10MB RAM（JSON 图），总计约 150MB RAM，适合 2GB 服务器。 | 对比向量数据库方案（1-2GB RAM）资源效率高 10 倍。
