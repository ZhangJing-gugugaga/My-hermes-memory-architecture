# HIMRA v5.1 — 双模式记忆架构

> **v5.0 → v5.1 的核心教训**：HIMRA 和 Hindsight 不是替代关系，是互补关系。v5.0 试图让 HIMRA 管理完整的记忆生命周期（短期→巩固→长期），但 `retrieval_count` 的可靠更新机制在实践中不可行。v5.1 接受 Hindsight 的存在，让 HIMRA 回归其真正擅长的领域：结构化存档、显式回忆、行为章程。

## 双模式设计

```
┌──────────────────────────────────────────────────┐
│              HIMRA v5.1 双模式                    │
├──────────────────────────────────────────────────┤
│                                                  │
│  模式 A: 有 Hindsight（推荐）                      │
│  ┌─────────────┐    ┌──────────────────┐        │
│  │  Hindsight  │    │  HIMRA           │        │
│  │  日常检索    │    │  显式会话回忆      │        │
│  │  auto_recall │    │  sessions/ 存档   │        │
│  │  auto_retain │    │  rules.md 章程    │        │
│  └─────────────┘    └──────────────────┘        │
│                                                  │
│  模式 B: 无 Hindsight（回退）                      │
│  ┌──────────────────────────────────────────┐   │
│  │  HIMRA 完整管线                            │   │
│  │  long-term/ → short-term/ → facts/        │   │
│  │  → summaries/ + consolidation.py          │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
└──────────────────────────────────────────────────┘
```

## 与 Hindsight 的分工（v5.1 定论）

| 职责 | Hindsight | HIMRA |
|------|-----------|-------|
| 日常语义检索 | ✅ 主力 | ❌ 不参与 |
| 零碎事实自动摄入 | ✅ auto_retain | ❌ 不参与 |
| 会话记录存档 | 双写（备份） | ✅ 主存档（sessions/） |
| 显式"回忆上次对话" | ❌ 不触发 | ✅ 按触发词搜 sessions/ |
| 行为规则/用户画像 | ❌ 不支持 | ✅ rules.md 每轮必读 |
| 环境配置/项目知识 | 语义可搜 | ✅ long-term/ 结构化 |
| 无 Hindsight 回退 | — | ✅ 完整管线 |

## 目录结构

```
D:\HIMRA\                          ← 数据根目录
├── rules.md                       ← 行为章程（每轮必读）
├── memory
│   ├── sessions\                  ← v5.1 新增：会话存档
│   │   └── YYYY-MM-DD
│   │       └── session-XXX.md
│   ├── long-term\                 ← 结构化长期记忆
│   │   ├── user-profile.md
│   │   ├── env-config.md
│   │   ├── preferences.md
│   │   └── projects
│   ├── short-term\                ← 无 Hindsight 时使用
│   ├── facts\                     ← 原子事实
│   └── summaries\                 ← 归档
├── scripts\                       ← 无 Hindsight 时使用
│   ├── consolidation.py
│   ├── init_indices.py
│   └── validate_memory.py
├── logs
└── backups\
```

## MEMORY.md 路由（精简到 16 行）

MEMORY.md 不再是"存储容器"，而是纯路由层：
1. 读取 rules.md（行为章程）
2. 检测 Hindsight 是否可用
3. 可用 → 日常走 Hindsight，显式回忆走 HIMRA sessions/
4. 不可用 → 完整 HIMRA 管线回退

## 记忆摄入三层架构

| 层 | 触发方式 | 目标 |
|----|---------|------|
| Layer 1: 实时原子事实 | Hindsight auto_retain 每 10 轮 | Hindsight |
| Layer 2: 手动标记 | 用户说"记住这个" | long-term/ |
| Layer 3: 会话结束摘要 | 用户说"拜拜" | sessions/ + Hindsight 双写 |

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v5.1.0 | 2026-06-19 | 双模式架构：Hindsight日常+HIMRA显式回忆；新增 rules.md 行为章程；sessions/ 会话存档；精简 MEMORY.md 到路由层 |
| v5.0.0 | 2026-06-19 | 双轴架构（检索+生命周期）、短期/长期记忆、consolidation.py |
| v4.1.0 | 2026-06-19 | 三层知识塔、六阶段检索、SQLite索引 |
| v3.0.0 | 2026-06-18 | 五组件+四阶段流水线 |
| v1.0.0 | 2026-06-18 | 纯规则路由 |
