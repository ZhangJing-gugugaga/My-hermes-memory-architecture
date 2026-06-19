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

## 检索后回写规则

当 Hermes 检索时使用了一条短期记忆（无论是走 HIMRA 路由命中还是 Hindsight 语义召回），必须执行：

1. 打开对应的 short-term/YYYY-MM-DD/session-XXXX.md
2. 将 retrieval_count 字段值 +1
3. 将 last_retrieved 字段更新为当前时间戳（ISO 8601）
4. 同步更新 short-term/index.md 中对应行的召回次数和最后召回时间

此规则确保 consolidation.py 能正确判断哪些短期记忆应升级为长期记忆。

## 巩固规则

- 短期记忆被召回 ≥3 次 → 自动迁移到长期记忆
- 超过 14 天未召回 → 归档到 summaries/
- 用户说"记住这个" → 直接写入长期记忆

## 存储规则

- 所有记忆数据存储在 D:\HIMRA\memory\
- C 盘只存放程序代码和临时文件
- 备份文件存储在 D:\backups\
