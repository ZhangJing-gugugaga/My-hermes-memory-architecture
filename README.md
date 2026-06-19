# HIMRA v5.0 — Human Memory

> **双轴架构**：检索轴（怎么找到记忆）+ 生命周期轴（记忆怎么生长和衰减）。
> v1-v4 解决检索，v5 新增生命周期管理。

## 核心思想

```
v1: MEMORY.md 是存储容器（扁平记忆）
v3: MEMORY.md 是检索路由器（五组件+四阶段）
v4: MEMORY.md 是多级知识塔的入口（三层架构+触发器排练+主动巩固）
v5: MEMORY.md 是路由规则 + 记忆生命周期管理（短期→巩固→长期→衰减）
```

**v5 的核心公式：**

```
写入 = 会话摘要 → short-term/ → 同时写入 Hindsight
巩固 = 每天扫描 short-term/ → 召回≥3次 → 迁移到 long-term/
衰减 = 14天未召回 → 归档到 summaries/
检索 = long-term/ → short-term/ → Hindsight recall
```

## 双轴架构

```
┌─────────────────────────────────────────────────────────────┐
│                    HIMRA v5.0 双轴架构                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────────┐│
│  │     检索轴 (v4.1)    │    │    生命周期轴 (v5 NEW)       ││
│  │                     │    │                             ││
│  │  查询               │    │  新信息                      ││
│  │    ↓                │    │    ↓                        ││
│  │  规则匹配           │    │  短期记忆                    ││
│  │    ↓                │    │    ↓ (召回≥3次)             ││
│  │  实体匹配           │    │  巩固迁移                    ││
│  │    ↓                │    │    ↓                        ││
│  │  语义检索(Hindsight)│    │  长期记忆                    ││
│  │    ↓                │    │    ↓ (14天未召回)            ││
│  │  图遍历             │    │  衰减归档                    ││
│  │    ↓                │    │                             ││
│  │  打分排序           │    │                             ││
│  └─────────────────────┘    └─────────────────────────────┘│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 与 Hindsight 的分工

| 职责 | HIMRA | Hindsight |
|------|-------|-----------|
| 存储 | 管"记忆放哪个文件夹、属于哪个类别" | 不管存储结构 |
| 检索 | 管"什么情况下去搜、搜什么" | 管"怎么搜"——语义匹配、相似度排序 |
| 生命周期 | 管"什么条件从短期升长期、什么条件衰减" | 管"统计这条记忆被召回了几次" |

**一句话：** HIMRA 是大脑结构（新皮层分区），Hindsight 是搜索引擎（海马体的模式完成功能）。

## 存储位置规范（D 盘优先）

**核心原则：所有持续增长、占用大量存储空间的数据必须存储在 D 盘。**

| 数据类型 | D 盘路径 | 说明 |
|----------|----------|------|
| HIMRA 记忆 | `D:\HIMRA\memory\` | 短期/长期/归档 |
| Hindsight 数据 | `D:\hindsight\` | 已在 D 盘 |
| Obsidian 知识库 | `D:\Obsidian Vault\` | 已在 D 盘 |
| 备份文件 | `D:\backups\` | 定时备份产出 |
| 日志文件 | `D:\HIMRA\logs\` | 长期累积 |

## 目录结构

```
D:\HIMRA\                              ← HIMRA 数据根目录
├── memory\                            ← 记忆系统
│   ├── short-term\                    ← 短期记忆
│   │   ├── index.md                   ← 短期记忆索引
│   │   └── YYYY-MM-DD\               ← 按日期组织
│   │       └── session-XXXX.md        ← 单次会话摘要
│   ├── long-term\                     ← 长期记忆
│   │   ├── user-profile.md            ← 用户画像
│   │   ├── env-config.md              ← 环境配置
│   │   ├── preferences.md             ← 偏好习惯
│   │   └── projects\                  ← 项目知识
│   ├── facts\                         ← v4.1 原子事实
│   ├── sessions\                      ← v4.1 原始会话记录
│   ├── summaries\                     ← 归档
│   ├── .indices.db                    ← SQLite 统一索引
│   └── .embeddings\                   ← 向量索引（FAISS）
├── sessions\                          ← Hermes 会话日志
├── logs\                              ← 长期日志
└── backups\                           ← 备份文件
```

## 记忆生命周期

### 写入流程

```
会话结束
    ↓
Hermes 自动生成会话摘要
    ↓
写入 D:\HIMRA\memory\short-term\YYYY-MM-DD\session-XXXX.md
    ↓
同时写入 Hindsight（bank: hermes-cli）
    ↓
更新 D:\HIMRA\memory\short-term\index.md
```

### 巩固流程（consolidation.py，每天凌晨运行）

```
扫描 D:\HIMRA\memory\short-term\index.md
    ↓
查询 Hindsight 中每条记忆的 retrieval_count 和 last_retrieved
    ↓
更新 index.md 中的统计字段
    ↓
判断：
  - retrieval_count ≥ 3 且跨越 ≥ 2 个不同会话 → 迁移到 long-term/
  - last_retrieved 超过 14 天 → 移入 summaries/
    ↓
更新记忆文件的 status 和 promoted_to 字段
```

### 手动干预

- 用户说"记住这个" → 直接写入 long-term/，标记 manual_override: true
- 用户说"忘记这个" → 移入 summaries/，标记 user_deleted: true

## MEMORY.md 路由规则

MEMORY.md 精简为路由层（≤1200字符）：

```
# MEMORY.md — HIMRA v5.0 路由规则

## 启动序列（always_load=true, priority=high）

每次会话开始时，必须执行：
1. 从 long-term/user-profile.md 读取用户名称和 Agent 名称
2. 从 short-term/ 找到最近一次会话摘要
3. 输出："你好，[用户名]，我是 [Agent名]，我们继续 [上次会话一句话摘要] 吗？"

## 路由规则

- 用户画像/偏好 → long-term/user-profile.md, preferences.md
- 环境配置 → long-term/env-config.md
- 项目知识 → long-term/projects/<name>.md
- 会话摘要 → short-term/YYYY-MM-DD/session-XXXX.md
- 原子事实 → facts/*.md
- 归档记忆 → summaries/*.md

## 检索策略

1. 先查 long-term/（快速匹配）
2. 再查 short-term/（最近信息）
3. 最后调 Hindsight recall（语义搜索）

## 巩固规则

- 短期记忆被召回 ≥3 次 → 自动迁移到长期记忆
- 超过 14 天未召回 → 归档到 summaries/
- 用户说"记住这个" → 直接写入长期记忆

## 存储规则

- 所有记忆数据存储在 D:\HIMRA\memory\
- C 盘只存放程序代码和临时文件
- 备份文件存储在 D:\backups\
```

## 巩固条件

| 条件 | 动作 | 说明 |
|------|------|------|
| 召回 ≥ 3 次，跨越 ≥ 2 个会话 | 迁移到 long-term/ | 被验证有用 |
| 14 天未被召回 | 归档到 summaries/ | 自然衰减 |
| 用户说"记住这个" | 直接写入 long-term/ | 手动干预 |
| 用户说"忘记这个" | 移入 summaries/ | 手动删除 |

## 评估指标

| 指标 | 目标 | 测量方法 |
|------|------|----------|
| 巩固准确率 | ≥ 80% | 升级到长期记忆的信息中，被后续使用的比例 |
| 遗忘合理率 | ≥ 90% | 归档的信息中，确实不再需要的比例 |
| 检索延迟 | < 100ms | 从查询到返回结果的时间 |
| 路由命中率 | ≥ 85% | 路由规则正确分类的比例 |

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v5.0.0 | 2026-06-19 | 新增短期/长期记忆架构，巩固机制，可见性接口，D盘存储规范 |
| v4.1.0 | 2026-06-19 | 三层知识塔，六阶段检索，SQLite索引 |
| v4.0.0 | 2026-06-19 | T-Mem + ActiveMem 融合 |
| v3.0.0 | 2026-06-18 | 五组件+四阶段流水线 |
| v1.0.0 | 2026-06-18 | 纯规则路由 |
