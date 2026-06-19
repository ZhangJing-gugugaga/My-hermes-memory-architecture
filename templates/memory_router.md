# MEMORY.md v4.1 模板 — Memory Max 流派
# 总预算：2200 字符
# Planner Summary: ~300 chars
# Retrieval Router: ~1900 chars

# Memory Router v4.1 — Memory Max

## Planner Summary (~300 chars)
[当前状态蒸馏]
[关键实体和关系]
[最近焦点]
[待办/进行中]

## Paths
facts/ = 单事实 | sessions/ = 对话弧线 | sources/ = 原始知识 | summaries/ = 主题摘要
.indices.db = SQLite统一索引 | .embeddings/ = FAISS向量(mmap)

## Stage 0: Query Rewrite [v4.1 NEW]
规则改写：同义词、缩写、中英对照
零成本，将用户查询扩展为 2-3 个候选表述

## Stage 1: Trigger Match [v4 NEW]
Descriptive: 关键词/时间/空间精确匹配
Associative: query embedding vs trigger embedding (SQLite)
改写后的候选分别匹配，取最高分
Threshold: descriptive=exact, associative>0.70

## Stage 2: Entities
entity_index 查找（带 type+context 消歧）

## Stage 3: Semantic
Trigger: Stage 1+2 matches < 2 unique files
Model: BGE-small (384维, mmap) | Threshold: > 0.6
Scope: 仅 facts/ + summaries/

## Stage 4: Graph
Trigger: >= 1 file matched
Depth: 1-2 | Follow: cross_links (按关系类型过滤) + pathways
超边：多实体联合命中时召回整个超边节点

## Scoring
α(trigger)=0.35 | β(rule)=0.25 | γ(entity)=0.20 | δ(semantic)=0.12 | ε(graph)=0.08
关系加权：depends_on×1.2 | contradicts×0.5 | generalizes×1.1

## Load Strategy
summary → 够用就停 | fact → 直接加载 | session → 截取片段 | source → 按需

## Write Pipeline (同步+异步)
同步(<2s): 提取事实+分类+写文件+更新entity_index
异步(后台): 触发器生成+embedding+cross_link检测+Planner更新

## Consolidation
每日(<10min): 本周新记忆 cross_link + summary更新
每周(<2h): 冗余检测(同entity) + 触发器重生成 + 超边重建
每月: >90d → archive/ | >180d 可删

## Lifecycle
>90d unmatched → archive/ | MEMORY.md <=2200 chars
