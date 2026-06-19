---
name: [topic-name]
type: summary
triggers:
  descriptive:
    entities: []
    temporal: []
    spatial: []
  associative:
    queries:
      - query: "[关于此主题的常见问题 1]"
        confidence: 0.90
      - query: "[关于此主题的常见问题 2]"
        confidence: 0.85
      - query: "[关于此主题的常见问题 3]"
        confidence: 0.80
    pathways:
      - "[入口主题] → [本主题] → [延伸主题]"
always_load: false
priority: high
updated: YYYY-MM-DD
summary: [主题名称] — [覆盖范围概述]
version: 4
coverage:
  - [子主题1]
  - [子主题2]
  - [子主题3]
cross_links:
  - sources/[相关原始知识1].md
  - sources/[相关原始知识2].md
---

## [主题名称]

### 核心概念
[3-5 个核心概念，每个 1-2 段话]

### 关键发现
[从论文/实践中提取的关键发现]

### 当前状态
[此主题的最新进展]

### 与其他主题的关系
[交叉引用]
