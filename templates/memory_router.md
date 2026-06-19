# MEMORY.md — HIMRA v5.1 记忆路由

## 会话必读
1. 读取 D:\HIMRA\rules.md（行为章程，每次必读）
2. 检测 Hindsight：curl -s http://localhost:9177/health

## 记忆分流规则

### 日常检索 → Hindsight
所有常规对话的上下文回忆走 Hindsight auto_recall（静默）。

### 会话回忆 → HIMRA
仅当用户明确表达以下意图时，搜索 D:\HIMRA\sessions\ 目录：
- 触发词："回忆"、"之前聊过"、"上次说的"、"帮我找之前的对话"
- 触发词："查会话记录"、"我们讨论过"、"翻一下之前"
- 触发词："你记不记得上次"、"之前有个"
- 判断标准：用户想找的是"哪次对话"而非"某个事实"

### 会话保存（双写）
退出时摘要同时存入：
1. D:\HIMRA\sessions\YYYY-MM-DD\session-XXX.md（HIMRA 存档）
2. Hindsight（bank: hermes-cli）

### Hindsight 不可用时的回退
走完整 HIMRA 管线：long-term/ → short-term/ → facts/ → summaries/

