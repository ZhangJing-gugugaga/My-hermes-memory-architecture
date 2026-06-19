# HIMRA v4 — Memory Max

> **无限存储流派**：2200 字符路由器，管 70GB 知识海洋。
> 设计目标：最大记忆深度、最大召回率、不考虑交互体验。

## 核心思想

```
v1: MEMORY.md 是存储容器（扁平记忆）
v3: MEMORY.md 是检索路由器（五组件+四阶段）
v4: MEMORY.md 是多级知识塔的入口（三层架构+触发器排练+主动巩固）
```

**v4 的核心公式：**

```
写入(同步) = 存储事实 + 更新实体索引 (< 2s)
写入(异步) = 生成触发器 + 生成 embedding + 更新图索引
召回 = 查询改写 → 触发器匹配(热) → 实体匹配(温) → 向量+图遍历(冷) → 打分排序
巩固 = 每日轻量 + 每周深度 + 每月归档
```

## 三层知识塔

```
┌──────────────────────────────────────────────────────┐
│               LLM 上下文 (2200 chars)                │
│  ┌────────────────────────────────────────────────┐  │
│  │ Planner Summary (~300 chars)                    │  │
│  │ 当前状态蒸馏，全局快照                           │  │
│  ├────────────────────────────────────────────────┤  │
│  │ Retrieval Router (~1900 chars)                  │  │
│  │ 路由规则 + 五阶段配置 + 写入指令                 │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────────────────┘
                       │ 命中的记忆文件注入
┌──────────────────────▼───────────────────────────────┐
│                                                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────────┐ │
│  │ Level 1    │  │ Level 2    │  │ Level 3        │ │
│  │ 热层 Hot   │  │ 温层 Warm  │  │ 冷层 Cold      │ │
│  │            │  │            │  │                │ │
│  │ MEMORY.md  │  │ SQLite     │  │ 全文存储       │ │
│  │ 路由规则   │  │ .indices.db│  │ FAISS(mmap)    │ │
│  │ Planner    │  │ 触发器     │  │ 图遍历         │ │
│  │ Summary    │  │ 实体/图    │  │ 全文搜索       │ │
│  │            │  │ 摘要/超边  │  │                │ │
│  │ <10ms      │  │ <100ms     │  │ <500ms         │ │
│  │ ~50 规则   │  │ 按需查询   │  │ ~70GB          │ │
│  └────────────┘  └────────────┘  └────────────────┘ │
│                                                      │
└──────────────────────────────────────────────────────┘
```

## 记忆粒度（四层目录）

```
memory/
├── facts/          # 单事实级 — 一个事实一个文件（<1KB）
├── sessions/       # 对话级 — 保留完整对话弧线（1-10KB）
├── sources/        # 原始知识 — 论文、仓库、网页全文（10-100KB）
├── summaries/      # 主题摘要 — 每个主题的蒸馏版（1-5KB）
├── .indices.db     # SQLite 统一索引（触发器+实体+图+超边+摘要+访问日志）
├── .embeddings/    # 向量索引（FAISS IVF-PQ mmap）
│   └── index.faiss
└── archive/        # 归档（>90天未访问，压缩存储）
```

**加载策略：**
1. 命中 summary → 只加载 summary（1-5KB）
2. summary 不够 → 按需加载 source 原文
3. 命中 fact → 直接加载（<1KB）
4. 命中 session → 按相关性截取片段

## 六阶段检索流水线

```
Stage 0: 查询改写 [v4.1 NEW]
  将用户查询改写为 2-3 个候选表述
  规则改写（同义词、缩写、中英对照）→ 零成本
  └── "内存快满了" → ["内存不足", "服务器内存不够", "swap 不够"]

Stage 1: 触发器匹配 [v4 NEW]
  ├── 描述性触发器：关键词/时间/空间精确匹配
  ├── 关联性触发器：query embedding vs 预计算 trigger embedding
  ├── 查询改写后的候选表述分别匹配，取最高分
  └── 阈值：descriptive=exact, associative>0.70

Stage 2: 实体匹配 [v3 复用]
  └── entity_index 查找（带类型消歧）

Stage 3: 语义检索 [v3 复用, v4 扩展]
  ├── 触发条件：Stage 1+2 命中 < 2 个唯一文件
  ├── 模型：BGE-small (384维, 130MB RAM, mmap)
  ├── 范围：仅 facts/ + summaries/（高召回价值）
  └── 阈值：> 0.6

Stage 4: 图遍历 [v3 复用, v4 增强]
  ├── 触发条件：≥ 1 个文件命中
  ├── 深度：1-2（memory-max: 宁深勿漏）
  ├── 路径：cross_links（按关系类型过滤）+ pathways
  └── 超边：多实体联合查询命中时，召回整个超边的所有节点

Stage 5: 打分排序
  Score(f) = 0.35·trigger + 0.25·rule + 0.20·entity
           + 0.12·semantic + 0.08·graph
  关系类型加权：
    depends_on: ×1.2 | contradicts: ×0.5 | generalizes: ×1.1
    exemplifies: ×1.0 | temporally_after: ×0.9
```

## 写入流水线（同步+异步拆分）

```
用户输入
  │
  ▼
═══ 同步部分（< 2s，用户可感知）═══
  │
  ├── 1. 事实提取 + 分类 (LLM, 1次调用)
  ├── 2. 实体提取（带消歧）
  ├── 3. 写入记忆文件（I/O）
  └── 4. 更新 entity_index (SQLite, <10ms)
  │
  ▼ 返回给用户（不阻塞）
  │
═══ 异步部分（后台队列）═══
  │
  ├── 5. 生成关联性触发器 (LLM batch，攒 10 条一起)
  ├── 6. 生成 trigger embedding (batch，攒 50 条)
  ├── 7. 更新 trigger_index + graph_index (SQLite)
  ├── 8. 检测 cross_links（仅与共享 entity 的已有记忆比较）
  └── 9. 检查 Planner Summary 是否需要更新
```

**FAISS 索引重建：每晚 cron（非实时增量）**
- 5-10 万条向量全量重建约 2-5 分钟
- 比实时增量更新（每条 50-200ms）更稳定

## 主动巩固（三层增量）

```
每日轻量巩固（cron，< 10 分钟）：
  ├── 仅处理本周新增/修改的记忆（< 100 条）
  ├── 检测新记忆与已有记忆的 cross_links
  ├── 更新 summaries/ 中引用了新记忆的主题
  └── Planner Summary 重新蒸馏

每周深度巩固（cron，< 2 小时）：
  ├── 冗余检测：仅比较同 entity 下的记忆（O(n·k²) 非 O(n²)）
  ├── 重新生成 top-100 高频记忆的关联性触发器
  ├── 超边重建
  └── 实体消歧检查

每月归档（cron）：
  ├── >90 天未访问 → archive/
  ├── 压缩 archive/ 目录
  └── >180 天可配置自动删除（仅保留 summary）
```

## 资源预算（2核2GB + 70GB 磁盘）

| 资源 | 用量 | 说明 |
|------|------|------|
| RAM: BGE-small | 130MB | 向量模型常驻 |
| RAM: FAISS (mmap) | ~150MB | 仅热页缓存，5-10万条 IVF-PQ |
| RAM: SQLite | ~10MB | WAL 模式，按需加载 |
| RAM: FlashRank | ~30MB | 重排序模型 |
| RAM: 其他 | ~300MB | Python + Hindsight + Hermes |
| **RAM 总计** | **~620MB** | 2GB 的 31%，安全 |
| Disk: 记忆文件 | 2GB | 固定配额，超限触发合并/归档 |
| Disk: SQLite 索引 | 2GB | WAL 模式，定期 VACUUM |
| Disk: FAISS 向量 | 1GB | mmap 映射，保留重建空间 |
| Disk: 原始知识缓存 | 50GB | **LRU 淘汰**，硬限制 50GB |
| Disk: 归档 | 10GB | 压缩存储，>180天可删 |
| Disk: 系统余量 | 5GB | OS + 日志 + 临时文件 |
| **Disk 总计** | **70GB** | 完整分配 |

## 实体消歧

同一实体在不同上下文含义不同。entities 字段必须带 type+context：

```yaml
entities:
  - name: ECS
    type: cloud_server        # ← 不是 game_engine
    context: aliyun           # ← 不是 aws
```

最小实体类型集：
`cloud_server` / `system_config` / `memory_size` / `architecture` / `protocol` / `framework` / `paper` / `person` / `tool` / `concept` / `event` / `other`

## 关系类型化

cross_links 不再是裸字符串数组，每条关系带类型：

```yaml
cross_links:
  - target: facts/server-ip.md
    relation: depends_on
```

5 种关系覆盖 80% 需求：`depends_on` / `contradicts` / `generalizes` / `exemplifies` / `temporally_after`

## 超边（多实体联合查询）

当一个事实同时关联多个实体时，用超边表示：

```sql
-- SQLite hyperedge_index
INSERT INTO hyperedge_index VALUES (
  'he_001',
  '["facts/swap-config.md", "facts/server-ip.md"]',
  'co_occurrence',
  0.85
);
```

用户同时提到 3 个实体时，超边匹配提供比 pairwise 边更强的信号。

## 目录结构

```
himra/
├── README.md           # 本文件 — 架构总览
├── SPEC.md             # 记忆文件格式规范 v4.1
├── REVIEW.md           # 架构审查报告
├── memory/             # 记忆文件
│   ├── facts/
│   ├── sessions/
│   ├── sources/
│   ├── summaries/
│   ├── archive/
│   ├── .indices.db     # SQLite 统一索引
│   └── .embeddings/
├── scripts/            # 工具脚本
│   ├── validate_memory.py
│   ├── init_indices.py
│   └── consolidation.py
└── templates/          # 模板文件
    ├── memory_template.md
    ├── summary_template.md
    └── memory_router.md
```
