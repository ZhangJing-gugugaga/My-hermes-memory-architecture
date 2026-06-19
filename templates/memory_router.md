# MEMORY.md v4 模板 — Memory Max 流派
# 总预算：2200 字符
# Planner Summary: ~300 chars
# Retrieval Router: ~1900 chars

# Memory Router v4.0 — Memory Max

## Planner Summary (~300 chars)
[当前状态蒸馏]
[关键实体和关系]
[最近焦点]
[待办/进行中]

## Paths
facts/ = 单事实 | sessions/ = 对话弧线 | sources/ = 原始知识 | summaries/ = 主题摘要
.trigger_index = 触发器索引 | .entity_index = 实体索引 | .graph_index = 关系图

## Stage 0: Trigger Match [v4 NEW]
Method: 触发器索引查找（descriptive + associative）
Descriptive: 实体/时间/空间精确匹配
Associative: query embedding vs 预计算 trigger embedding
Threshold: descriptive=exact, associative>0.70
Limit: 最多返回 10 个文件

## Stage 1: Rules
Always load: user/profile.md
Keyword triggers: [按领域配置]

## Stage 2: Entities
Auto-retrieved from .entity_index.json

## Stage 3: Semantic
Trigger: Stage 0+1+2 matches < 2 unique files
Model: BGE-small (384维) | Threshold: > 0.6
Scope: facts/ + summaries/ 优先，sources/ 按需

## Stage 4: Graph
Trigger: >= 1 file matched
Depth: adaptive (1-3, based on trigger confidence)
Follow: cross_links + associative.pathways

## Scoring
α(trigger)=0.35 | β(rule)=0.25 | γ(entity)=0.20 | δ(semantic)=0.12 | ε(graph)=0.08

## Load Strategy
1. 命中 summary → 加载 summary（1-5KB）
2. summary 不够 → 按需加载 source 原文
3. 命中 fact → 直接加载（<1KB）
4. 命中 session → 截取相关片段

## Write Pipeline
Trigger: "remember" / correction / config change / task failure / knowledge ingestion
Pipeline:
  1. Extract fact + type classification (fact/session/source/summary)
  2. Trigger Rehearsal: descriptive + 5-10 associative queries
  3. Cross-link Detection: find related memories
  4. Write with full YAML frontmatter
  5. Update all indices (.trigger, .entity, .graph, .summary, .embeddings)
  6. Check Planner Summary freshness → update if needed

## Consolidation
Schedule: auto_retain (every 5 turns) + daily cron (server)
Tasks:
  - Detect cross-memory links
  - Merge redundant facts
  - Mark stale info (>90d)
  - Regenerate associative triggers for top-accessed memories
  - Re-distill Planner Summary
  - Update summaries/ when new sources added

## Lifecycle
>90d unmatched → archive/ | monthly consolidation | MEMORY.md <=2200 chars
