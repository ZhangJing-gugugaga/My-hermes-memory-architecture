# HIMRA v4 — Memory File Format Specification

> 版本：4.0
> 分支：v4-memory-max
> 兼容：v3 SPEC.md 向前兼容（v3 文件无需迁移即可使用）

## 设计原则

1. **一个文件 = 一个可独立检索的知识单元**
2. **YAML frontmatter 是机器可读的索引，Markdown body 是人可读的内容**
3. **触发器覆盖"表面相似"和"潜在关联"两种召回路径**
4. **摘要层优先加载，原文层按需加载**

## 文件类型

| type | 目录 | 大小 | 说明 |
|------|------|------|------|
| `fact` | facts/ | <1KB | 单一事实，一个文件一条知识 |
| `session` | sessions/ | 1-10KB | 对话弧线，保留决策上下文 |
| `source` | sources/ | 10-100KB | 原始知识（论文、仓库、网页） |
| `summary` | summaries/ | 1-5KB | 主题摘要，覆盖某个领域所有知识 |

## YAML Frontmatter Schema

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 唯一标识符（文件名去 .md） |
| `type` | enum | `fact` / `session` / `source` / `summary` |
| `triggers` | object | 双类触发器（见下方） |
| `always_load` | boolean | 是否每轮都加载 |
| `priority` | enum | `high` / `medium` / `low` |
| `updated` | date | 最后修改日期 (YYYY-MM-DD) |
| `summary` | string | 一句话描述（<100 字符） |

### 触发器格式（v4 核心变化）

```yaml
triggers:
  descriptive:
    entities: [ECS, Aliyun, 123.57.30.132]    # 实体关键词
    temporal: [2026-06, server-setup]           # 时间标记
    spatial: [aliyun-beijing, /root/.hermes/]   # 空间/路径标记
  associative:
    queries:                                     # 关联性查询预测
      - query: "为什么 gateway 启动失败"
        confidence: 0.85
      - query: "如何给服务器扩容"
        confidence: 0.72
      - query: "服务器内存不够了怎么办"
        confidence: 0.68
    pathways:                                    # 语义推理路径
      - "服务器配置 → 服务部署 → 故障排查"
      - "ECS → 成本优化 → 迁移方案"
```

**触发器生成规则：**
- 描述性触发器：从内容中自动提取（实体 NER + 时间 + 路径）
- 关联性触发器：LLM 预测"用户未来可能问什么"
  - fact 类型：生成 5-10 个关联查询
  - session 类型：生成 3-5 个关联查询
  - source 类型：生成 10-20 个关联查询（内容多）
  - summary 类型：生成 5-8 个关联查询
- 置信度 (confidence)：LLM 自评，0-1，用于排序和过滤

### 可选字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | integer | Schema 版本（默认 1） |
| `supersedes` | string | 被此文件取代的旧文件名 |
| `expires` | date | 过期日期（自动归档） |
| `access_count` | integer | 加载次数（用于热度统计） |
| `last_accessed` | date | 最后访问日期 |
| `cross_links` | string[] | 关联记忆文件路径 |
| `source_url` | string | 原始来源 URL（source 类型必填） |
| `source_type` | enum | `paper` / `repo` / `article` / `conversation` / `crawl` |
| `coverage` | string[] | summary 类型：覆盖的子主题列表 |
| `embedding_id` | string | 向量索引中的 ID |

## 完整示例

### fact 类型

```yaml
---
name: swap-config
type: fact
triggers:
  descriptive:
    entities: [ECS, swap, 2GB, memory]
    temporal: [2026-06]
    spatial: [aliyun-beijing]
  associative:
    queries:
      - query: "服务器内存不够怎么办"
        confidence: 0.85
      - query: "swap 大小怎么调"
        confidence: 0.72
      - query: "为什么服务器这么慢"
        confidence: 0.65
    pathways:
      - "swap配置 → 内存不足 → 扩容方案"
always_load: false
priority: medium
updated: 2026-06-18
summary: ECS 服务器 swap 配置为 2GB
version: 4
cross_links:
  - facts/server-ip.md
  - context/server.md
---

ECS 服务器 swap 配置为 2GB。
位置：/swapfile
类型：swapfile（非分区）
配置时间：2026-06-18
```

### summary 类型

```yaml
---
name: memory-systems
type: summary
triggers:
  descriptive:
    entities: [memory, HIMRA, Hindsight, T-Mem, ActiveMem, retrieval]
    temporal: [2026-06]
    spatial: []
  associative:
    queries:
      - query: "Agent 记忆系统怎么设计"
        confidence: 0.92
      - query: "记忆召回率怎么提高"
        confidence: 0.88
      - query: "HIMRA 和传统 RAG 有什么区别"
        confidence: 0.85
      - query: "主动预测记忆是什么"
        confidence: 0.80
    pathways:
      - "记忆架构 → HIMRA → T-Mem触发器 → ActiveMem解耦"
      - "Hindsight → 向量检索 → 图遍历 → 巩固"
always_load: false
priority: high
updated: 2026-06-19
summary: Agent 记忆系统全景：HIMRA/Hindsight/T-Mem/ActiveMem
version: 4
coverage:
  - himra-architecture
  - hindsight-deployment
  - tmem-triggers
  - activemem-distributed
  - memory-consolidation
cross_links:
  - sources/tmem-paper.md
  - sources/activemem-paper.md
  - facts/swap-config.md
---

## Agent 记忆系统全景

### HIMRA 架构
五组件（Memory Store, Entity Index, Vector Index, Graph Index, Retrieval Router）
四阶段流水线（规则→实体→语义→图）
v4 新增：Stage 0 触发器匹配，Planner Summary 蒸馏层

### Hindsight
DeepSeek API + BGE-small + FlashRank，localhost:9177
auto_retain=true，每 5 轮自动保存
62+ 条事实记忆

### T-Mem 启发
写入时生成关联性触发器（预测未来查询）
"episodic future thinking" — 记忆为未来服务

### ActiveMem 启发
Planner（蒸馏摘要执行推理）⊥ Memory Manager（后台巩固）
解耦设计，分布式记忆管理

### 关键论文
- T-Mem (2606.15405): 主动预测记忆
- ActiveMem (2606.10532): 分布式解耦记忆
- MemTrace (2606.17328): 记忆一致性追踪
- Infini Memory (2606.10677): 主题文档式记忆
```

### source 类型

```yaml
---
name: tmem-paper
type: source
triggers:
  descriptive:
    entities: [T-Mem, episodic, trigger, rehearsal, LoCoMo]
    temporal: [2026-06]
    spatial: []
  associative:
    queries:
      - query: "什么是关联性触发器"
        confidence: 0.90
      - query: "记忆写入时应该做什么"
        confidence: 0.85
      - query: "如何提高记忆召回率"
        confidence: 0.80
    pathways:
      - "T-Mem → 触发器排练 → HIMRA v4 Stage 0"
always_load: false
priority: high
updated: 2026-06-19
summary: T-Mem 论文 — 主动预测记忆，关联性触发器
version: 4
source_url: https://arxiv.org/abs/2606.15405
source_type: paper
cross_links:
  - summaries/memory-systems.md
  - sources/activemem-paper.md
---

# T-Mem: Memory That Anticipates, Not Archives

[论文全文内容...]
```

## 向后兼容

v3 格式的记忆文件（只有 `triggers: string[]`）在 v4 中自动映射为：

```yaml
# v3 格式
triggers: [server, ECS, SSH]

# v4 自动解释为
triggers:
  descriptive:
    entities: [server, ECS, SSH]
    temporal: []
    spatial: []
  associative:
    queries: []
    pathways: []
```

迁移脚本可选运行，但不强制。
