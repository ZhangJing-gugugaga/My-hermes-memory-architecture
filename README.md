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
写入 = 存储事实 + 生成描述性触发器 + 生成关联性触发器 + 更新摘要
召回 = 触发器匹配(热) → 实体匹配(温) → 向量+图遍历(冷) → 打分排序
巩固 = 后台重组 + 冗余合并 + 摘要蒸馏 + 过期归档
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
│  │ MEMORY.md  │  │ 索引文件   │  │ 全文存储       │ │
│  │ 路由规则   │  │ 触发器     │  │ 向量检索       │ │
│  │ Planner    │  │ 实体索引   │  │ 图遍历         │ │
│  │ Summary    │  │ 图索引     │  │ 全文搜索       │ │
│  │            │  │ 摘要索引   │  │                │ │
│  │ <10ms      │  │ <100ms     │  │ <500ms         │ │
│  │ ~50 规则   │  │ ~500 条目  │  │ ~70GB          │ │
│  └────────────┘  └────────────┘  └────────────────┘ │
│                                                      │
└──────────────────────────────────────────────────────┘
```

## 记忆粒度（四层目录）

```
memory/
├── facts/          # 单事实级 — 一个事实一个文件
│   ├── server-ip.md
│   ├── swap-config.md
│   └── ...（每个 <1KB）
│
├── sessions/       # 对话级 — 保留完整对话弧线
│   ├── 2026-06-18-himra-discussion.md
│   ├── 2026-06-19-paper-analysis.md
│   └── ...（每个 1-10KB）
│
├── sources/        # 原始知识 — 论文、仓库、网页全文
│   ├── tmem-paper.md
│   ├── activemem-paper.md
│   ├── github-rag-techniques.md
│   └── ...（每个 10-100KB）
│
├── summaries/      # 主题摘要 — 每个主题的蒸馏版
│   ├── memory-systems.md      # 覆盖所有记忆相关知识
│   ├── mcp-protocol.md        # 覆盖所有 MCP 相关知识
│   ├── agent-frameworks.md    # 覆盖所有 Agent 框架
│   └── ...（每个 1-5KB）
│
├── .trigger_index.json     # 触发器索引（描述性+关联性）
├── .entity_index.json      # 实体索引
├── .graph_index.json       # 关系图索引
├── .summary_index.json     # 摘要索引（主题→文件映射）
└── .embeddings/            # 向量索引（FAISS + BGE-small）
    └── index.faiss
```

**加载策略：**
1. 命中 summary → 只加载 summary（1-5KB，省上下文）
2. summary 不够 → 加载对应的 source 原文（10-100KB）
3. 命中 fact → 直接加载（<1KB，几乎免费）
4. 命中 session → 按相关性截取片段

## 五阶段检索流水线

```
Stage 0: 触发器匹配 (v4 新增)
  ├── 描述性触发器：实体/时间/空间精确匹配
  ├── 关联性触发器：query embedding vs 预计算 trigger embedding
  └── 阈值：descriptive=exact, associative>0.70

Stage 1: 规则匹配 (v3 复用)
  ├── 关键词触发：MEMORY.md 中的规则
  └── always_load：始终加载的文件

Stage 2: 实体匹配 (v3 复用)
  └── .entity_index.json 查找

Stage 3: 语义检索 (v3 复用, v4 扩展)
  ├── 触发条件：Stage 0+1+2 命中 < 2 个唯一文件
  ├── 模型：BGE-small (384维, 130MB RAM)
  └── 阈值：> 0.6

Stage 4: 图遍历 (v3 复用, v4 增强)
  ├── 触发条件：≥ 1 个文件命中
  ├── 深度：1-3（自适应，基于触发器置信度）
  ├── 路径：cross_links + associative.pathways
  └── 降级：深度 1 足够时不要走深度 3

打分公式：
  Score(f) = 0.35·trigger + 0.25·rule + 0.20·entity
           + 0.12·semantic + 0.08·graph
```

## 写入流水线

```
用户输入（对话/抓取/导入）
  │
  ▼
1. 事实提取
  LLM 提取: {fact, entities, type}
  type: fact | session | source | summary
  │
  ▼
2. 触发器排练 (T-Mem)
  Descriptive: 实体/时间/空间
  Associative: LLM 生成 5-10 个未来查询预测
  │
  ▼
3. 跨记忆关联检测
  检测与已有记忆的关联 → cross_links
  │
  ▼
4. 写入目标文件
  YAML frontmatter + 内容
  │
  ▼
5. 更新所有索引
  .trigger_index.json  (新触发器)
  .entity_index.json   (新实体)
  .graph_index.json    (新关系)
  .summary_index.json  (新摘要映射)
  .embeddings/index.faiss (新向量)
  │
  ▼
6. 检查 Planner Summary 是否需要更新
```

## 主动巩固 (Consolidation)

```
触发方式：
  - auto_retain: 每 5 轮（Hindsight 自动）
  - cron job: 每天凌晨（服务器）

巩固任务：
  ├── 检测跨记忆链接（更新 cross_links）
  ├── 合并冗余事实（同一事实多个版本 → 合并）
  ├── 标记过期信息（>90 天未访问 → archive/）
  ├── 重新生成高频访问记忆的关联性触发器
  ├── 重新蒸馏 Planner Summary
  └── 重新生成 summaries/（新知识进来后更新主题摘要）
```

## 资源预算（2核2GB + 70GB 磁盘）

| 资源 | 用量 | 说明 |
|------|------|------|
| RAM: BGE-small | 130MB | 向量模型常驻 |
| RAM: FAISS 索引 | ~50MB | 50万条记忆的 embedding |
| RAM: FlashRank | ~30MB | 重排序模型 |
| RAM: 其他 | ~300MB | Python + Hindsight + Hermes |
| **RAM 总计** | **~510MB** | 2GB 的 25%，安全 |
| Disk: 记忆文件 | ~1GB | 10万条记忆（平均 10KB/条） |
| Disk: 向量索引 | ~750MB | 50万条 × 1.5KB |
| Disk: 原始知识 | ~50GB | 论文、仓库、网页缓存 |
| **Disk 总计** | **~52GB** | 70GB 的 74%，有余量 |

## 目录结构

```
himra/
├── README.md           # 本文件 — 架构总览
├── SPEC.md             # 记忆文件格式规范
├── ARCHITECTURE.md     # 详细设计文档
├── memory/             # 记忆文件模板
│   ├── facts/.gitkeep
│   ├── sessions/.gitkeep
│   ├── sources/.gitkeep
│   └── summaries/.gitkeep
├── scripts/            # 工具脚本
│   ├── validate_memory.py    # schema 验证
│   ├── init_indices.py       # 初始化索引
│   └── consolidation.py      # 巩固脚本
└── templates/          # 模板文件
    ├── memory_template.md    # 记忆文件模板
    ├── summary_template.md   # 摘要模板
    └── memory_router.md      # MEMORY.md v4 模板
```
