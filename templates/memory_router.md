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
