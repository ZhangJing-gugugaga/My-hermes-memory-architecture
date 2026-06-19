---
name: himra-有五个组件memory-store带-yaml-frontmat
type: fact
triggers:
  descriptive:
    keywords: ["Memory Store", "BGE-small", "MEMORY.md", "Entity Index", "FAISS", "HIMRA", "Vector Index", "Retrieval Router", "Graph Index"]
    temporal: ['2026-06']
    spatial: []
  associative:
    queries:
      - query: "HIMRA 有五个组件：Memory Store（带 YAML frontmatter 的 md 文件）、Entity "
        confidence: 0.6
    pathways: []
entities:
  - name: Memory Store
    type: concept
    context: 
  - name: BGE-small
    type: concept
    context: 
  - name: MEMORY.md
    type: concept
    context: 
  - name: Entity Index
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
summary: "HIMRA 有五个组件：Memory Store（带 YAML frontmatter 的 md 文件）、Entity Index（实体到文件的 JSON 映射"
version: 4
cross_links: []
---

HIMRA 有五个组件：Memory Store（带 YAML frontmatter 的 md 文件）、Entity Index（实体到文件的 JSON 映射，解决同义词问题）、Vector Index（FAISS + BGE-small 可选，150MB RAM）、Graph Index（实体关系 JSON，10MB RAM）、Retrieval Router（MEMORY.md 规则，始终加载）。
