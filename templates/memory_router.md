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

---

# rules.md — HIMRA v5.1 行为章程

## 启动序列（强制首句）

用户发送第一条消息后，你的第一句回复必须是：
1. 读取本文件下方的 Agent 名称和用户姓名
2. 从 sessions/ 找到最近一次会话摘要文件
3. 输出："你好，[用户名]，我是 [Agent名]，我们继续 [会话摘要原文] 吗？"

此问候语是强制首句，不得跳过。会话摘要必须引用原文，不得改写。

## 基本身份

- 用户姓名：[填写]
- Agent 名称：[填写]
- 命名时间：[填写]
- 命名来源：[填写]

## 用户画像

[填写用户画像：技术水平、表达风格、脾气特征、核心诉求]

## 行为约束规则

[填写行为约束：禁止瞎猜、任务失败上限、Skills规则、沟通规范等]

## 关键边界

[填写关键边界：服务器不存本机配置等]

## 退出保存规则
当用户说"bye"、"拜拜"、"退出"、"走了"、"保存并退出"时：
1. 生成本次会话一句话摘要
2. 写入 sessions/YYYY-MM-DD/session-XXX.md
3. 写入 Hindsight
4. 回复"已保存，下次见。"
