# HIMRA v4 — Memory File Format Specification

> 版本：4.1（含审查优化）
> 分支：v4-memory-max
> 兼容：v3 SPEC.md 向前兼容

## 设计原则

1. 一个文件 = 一个可独立检索的知识单元
2. YAML frontmatter 是机器可读的索引，Markdown body 是人可读的内容
3. 触发器覆盖"表面相似"和"潜在关联"两种召回路径
4. 摘要层优先加载，原文层按需加载

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
| `entities` | object[] | 带消歧的实体列表（见下方） |
| `temporal` | object | 时间元数据（见下方） |
| `always_load` | boolean | 是否每轮都加载 |
| `priority` | enum | `high` / `medium` / `low` |
| `updated` | date | 最后修改日期 (YYYY-MM-DD) |
| `summary` | string | 一句话描述（<100 字符） |

### 实体格式（带消歧）

```yaml
entities:
  - name: ECS
    type: cloud_server          # 实体类型（消歧用）
    context: aliyun             # 上下文（消歧用）
  - name: swap
    type: system_config
  - name: 2GB
    type: memory_size
  - name: HIMRA
    type: architecture
    context: memory_system
```

**实体类型枚举（最小集）：**
`cloud_server` / `system_config` / `memory_size` / `architecture` / `protocol` / `framework` / `paper` / `person` / `tool` / `concept` / `event` / `other`

### 时间格式（一等公民）

```yaml
temporal:
  valid_from: 2026-06-18      # 此知识何时生效
  valid_until: null            # 何时失效（null = 仍有效）
  observed_at: 2026-06-18      # 何时观察到/记录
  event_time: 2026-06-18       # 事件发生时间
```

### 触发器格式

```yaml
triggers:
  descriptive:
    keywords: [ECS, Aliyun, 服务器, swap]    # 关键词匹配
    temporal: [2026-06, server-setup]         # 时间标记
    spatial: [aliyun-beijing, /root/.hermes/] # 空间/路径标记
  associative:
    queries:
      - query: "为什么 gateway 启动失败"
        confidence: 0.85
      - query: "如何给服务器扩容"
        confidence: 0.72
    pathways:
      - "服务器配置 → 服务部署 → 故障排查"
```

**触发器生成规则：**
- 描述性：从内容自动提取（实体 + 时间 + 路径）
- 关联性：LLM 预测未来查询
  - fact: 5-10 个 | session: 3-5 个 | source: 10-20 个 | summary: 5-8 个
- 置信度：LLM 自评 0-1，用于排序和过滤

### 关系格式（类型化）

```yaml
cross_links:
  - target: facts/server-ip.md
    relation: depends_on        # 此记忆依赖目标
  - context: facts/swap-config-v1.md
    relation: contradicts       # 此记忆与目标矛盾
  - target: sources/activemem-paper.md
    relation: generalizes       # 此记忆是目标的泛化
  - target: sessions/2026-06-18-himra.md
    relation: exemplifies       # 此记忆是目标的示例
  - target: facts/server-setup.md
    relation: temporally_after  # 此记忆发生在目标之后
```

**关系类型枚举（5种，覆盖 80% 关联需求）：**
- `depends_on` — A 依赖 B
- `contradicts` — A 与 B 矛盾（版本冲突）
- `generalizes` — A 是 B 的泛化（总结→原文）
- `exemplifies` — A 是 B 的示例（理论→实践）
- `temporally_after` — A 发生在 B 之后（时序链）

### 可选字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | integer | Schema 版本（默认 1） |
| `supersedes` | string | 被此文件取代的旧文件名 |
| `expires` | date | 过期日期（自动归档） |
| `access_count` | integer | 加载次数（热度统计） |
| `last_accessed` | date | 最后访问日期 |
| `source_url` | string | 原始来源 URL（source 类型必填） |
| `source_type` | enum | `paper` / `repo` / `article` / `conversation` / `crawl` |
| `coverage` | string[] | summary 类型：覆盖的子主题 |
| `embedding_id` | string | 向量索引中的 ID |

## 完整示例

### fact 类型

```yaml
---
name: swap-config
type: fact
triggers:
  descriptive:
    keywords: [ECS, swap, 2GB, memory, 内存]
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
entities:
  - name: ECS
    type: cloud_server
    context: aliyun
  - name: swap
    type: system_config
  - name: 2GB
    type: memory_size
temporal:
  valid_from: 2026-06-18
  valid_until: null
  observed_at: 2026-06-18
  event_time: 2026-06-18
always_load: false
priority: medium
updated: 2026-06-18
summary: ECS 服务器 swap 配置为 2GB
version: 4
cross_links:
  - target: facts/server-ip.md
    relation: depends_on
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
    keywords: [memory, HIMRA, Hindsight, T-Mem, ActiveMem, retrieval, 记忆]
    temporal: [2026-06]
  associative:
    queries:
      - query: "Agent 记忆系统怎么设计"
        confidence: 0.92
      - query: "记忆召回率怎么提高"
        confidence: 0.88
      - query: "HIMRA 和传统 RAG 有什么区别"
        confidence: 0.85
    pathways:
      - "记忆架构 → HIMRA → T-Mem触发器 → ActiveMem解耦"
entities:
  - name: HIMRA
    type: architecture
    context: memory_system
  - name: Hindsight
    type: tool
    context: memory_backend
  - name: T-Mem
    type: paper
    context: memory_prediction
temporal:
  valid_from: 2026-06-19
  valid_until: null
  observed_at: 2026-06-19
  event_time: 2026-06-19
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
cross_links:
  - target: sources/tmem-paper.md
    relation: generalizes
  - target: sources/activemem-paper.md
    relation: generalizes
---

## Agent 记忆系统全景
[内容...]
```

## 索引层规范（SQLite）

所有索引统一存储在单个 SQLite 数据库 `memory/.indices.db`：

```sql
-- 触发器索引
CREATE TABLE trigger_index (
    memory_name TEXT NOT NULL,
    trigger_text TEXT NOT NULL,
    trigger_type TEXT NOT NULL,    -- 'descriptive' | 'associative'
    trigger_embedding BLOB,        -- 384维 float32 → 1536 bytes
    confidence REAL DEFAULT 1.0,
    PRIMARY KEY (memory_name, trigger_text, trigger_type)
);

-- 实体索引
CREATE TABLE entity_index (
    entity_name TEXT NOT NULL,
    entity_type TEXT,
    entity_context TEXT,
    memory_name TEXT NOT NULL,
    frequency INTEGER DEFAULT 1,
    PRIMARY KEY (entity_name, memory_name)
);

-- 关系图索引
CREATE TABLE graph_index (
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    PRIMARY KEY (source, target, relation_type)
);

-- 超边索引（多实体联合查询）
CREATE TABLE hyperedge_index (
    hyperedge_id TEXT PRIMARY KEY,
    nodes TEXT NOT NULL,           -- JSON array of memory names
    edge_type TEXT NOT NULL,       -- 'co_occurrence' | 'semantic_cluster'
    weight REAL DEFAULT 1.0
);

-- 摘要索引
CREATE TABLE summary_index (
    topic TEXT NOT NULL,
    memory_name TEXT NOT NULL,
    coverage_area TEXT,
    PRIMARY KEY (topic, memory_name)
);

-- 访问统计
CREATE TABLE access_log (
    memory_name TEXT NOT NULL,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    query_text TEXT,
    stage_matched INTEGER         -- 哪个阶段命中的
);
```

**索引优势：**
- WAL 模式原子事务，崩溃不损坏
- 按需查询，不需要全量加载到 RAM
- 支持复杂查询（JOIN、聚合、排序）
- Python 标准库自带，零依赖

## 向量索引规范

```
存储：FAISS IndexIVFPQ (mmap 模式)
维度：384 (BGE-small)
量化：PQ64 (每向量压缩到 64 bytes)
索引范围：仅 facts/ + summaries/（高召回价值）
预计规模：5-10 万条 → 磁盘 ~85MB, RAM ~150MB (mmap 热页)
重建频率：每晚 cron（非实时增量）
```

## 向后兼容

v3 格式（`triggers: string[]`）自动映射为：

```yaml
triggers:
  descriptive:
    keywords: [原 v3 的 triggers 数组]
    temporal: []
    spatial: []
  associative:
    queries: []
    pathways: []
```
