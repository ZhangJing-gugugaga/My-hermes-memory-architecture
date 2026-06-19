---
name: env-config
type: long_term
category: environment
created: 2026-06-19T19:00:00+08:00
updated: 2026-06-19T19:00:00+08:00
source: manual
manual_override: false
---

## 服务器

- 阿里云 ECS: 123.57.30.132
- 配置: 2核2G + 2GB swap + 70G盘
- SSH: 密钥+密码
- 飞书 gateway: 已通
- HIMRA v4.1: /opt/himra/
- 定时任务产出: /opt/hermes-tasks/

## 本地环境

- 系统代理: Clash 127.0.0.1:7897
- Obsidian 主库: D:\Obsidian Vault\我的知识库
- Hindsight: localhost:9177
- Chrome DevTools MCP: 端口 9222

## Cron 定时任务清单

### 本地任务（C 盘）

1. hermes-daily-backup - 每天 02:00，备份到 D:\backups\
2. ai-knowledge-search - 每天 03:00，搜索 GitHub AI 知识
3. daily-wiki-compile - 每天 17:00，编译 Obsidian wiki

### 服务器任务（ECS）

4. ai-daily - 每天 08:00 (deliver=feishu)
5. github-trending - 每天 09:00 (deliver=feishu)
6. arxiv-tracker - 每天 09:30 (deliver=feishu)
7. web-monitor - 每天 10:00 (deliver=feishu)
8. himra-consolidation - 每天 02:00

## HIMRA 仓库信息

- GitHub: ZhangJing-gugugaga/My-hermes-memory-architecture
- 分支: main(v1), rag-integration(v3), v4-memory-max(v4.1), v5-human-memory(v5.0)
- v4.1 服务器路径: /opt/himra/
- venv: /opt/himra/venv/
- 依赖: pyyaml, faiss-cpu, numpy, onnxruntime

## Hindsight 配置

- 本地: localhost:9177
- 安装路径: D:\hindsight
- auto_retain: true
- bank: hermes-cli
- Key: .env_key

## Obsidian 知识库结构

- 主库: D:\Obsidian Vault\我的知识库
- 写作库: D:\Obsidian Vault\vibe-writing-workflow-main
- AI 知识库: AI知识库/（8分类）
- wiki: wiki/（entities/topics/sources/index.md/SCHEMA.md）

## 飞书 CLI 配置

- APP ID: cli_aab93df90678dbe8
- 安装路径: /tmp/cli/bin/lark-cli
- 配置文件: C:\Users\laotie_nb666\.lark-cli\hermes\config.json

## Windows 特有问题

- Hermes 多终端并发时会因 SQLite 锁冲突导致静默崩溃
- 崩溃的 session 数据仍在 state.db（end_reason IS NULL）
- 可通过 hermes --resume <id> 恢复

## 迁移记录

### 2026-06-19 从 Hermes MEMORY.md 迁移到 HIMRA v5.0 long-term

1. 系统代理: Clash 127.0.0.1:7897，访问海外站点需设置 HTTP_PROXY/HTTPS_PROXY
2. HIMRA 仓库: ZhangJing-gugugaga/My-hermes-memory-architecture
3. Hindsight: localhost:9177, auto_retain=true, bank=hermes-cli
4. Obsidian: 主库 D:\Obsidian Vault\我的知识库, 写作库同目录 vibe-writing-workflow-main
5. 飞书: APP ID=cli_aab93df90678dbe8, bot-only 模式
6. Chrome DevTools MCP: 端口 9222, chrome-debug.bat 开机自启
7. 用户: 张敬, 大二 CS, 研究 AI Agent/记忆架构/MCP
8. Agent: Hermes by Nous Research, 模型 mimo-v2.5-pro (Xiaomi MiMo)
