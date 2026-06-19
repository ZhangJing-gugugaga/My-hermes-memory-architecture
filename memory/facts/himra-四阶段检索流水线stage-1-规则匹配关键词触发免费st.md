---
name: himra-四阶段检索流水线stage-1-规则匹配关键词触发免费st
type: fact
triggers:
  descriptive:
    keywords: ["HIMRA"]
    temporal: ['2026-06']
    spatial: []
  associative:
    queries:
      - query: "HIMRA 四阶段检索流水线：Stage 1 规则匹配（关键词触发，免费）、Stage 2 实体匹配（索引查找，免费，解"
        confidence: 0.6
      - query: "评分公式：Score = alpha*规则 + beta*实体 + gamma*语义 + delta*图，alpha >"
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
summary: "HIMRA 四阶段检索流水线：Stage 1 规则匹配（关键词触发，免费）、Stage 2 实体匹配（索引查找，免费，解决同义词）、Stage 3 语义搜索（嵌"
version: 4
cross_links: []
---

HIMRA 四阶段检索流水线：Stage 1 规则匹配（关键词触发，免费）、Stage 2 实体匹配（索引查找，免费，解决同义词）、Stage 3 语义搜索（嵌入相似度，~50ms，处理新表达）、Stage 4 图遍历（关系导航，~10ms，跨主题链接）。评分公式：Score = alpha*规则 + beta*实体 + gamma*语义 + delta*图，alpha > beta > gamma > delta。
