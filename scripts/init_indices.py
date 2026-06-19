#!/usr/bin/env python3
"""
HIMRA v5.0 索引初始化脚本
初始化 memory/short-term/index.md 和 memory/long-term/ 目录结构
"""
from datetime import datetime
from pathlib import Path

def get_repo_root():
    import subprocess
    r = subprocess.run(['git','rev-parse','--show-toplevel'], capture_output=True, text=True, check=True)
    return Path(r.stdout.strip())

def main():
    root = get_repo_root()
    mem = root/'memory'
    st = mem/'short-term'
    lt = mem/'long-term'
    idx = st/'index.md'

    print(f'[{datetime.now().isoformat()}] HIMRA v5.0 init_indices.py')
    print(f'仓库: {root}')

    st.mkdir(parents=True, exist_ok=True)
    lt.mkdir(parents=True, exist_ok=True)

    # 初始化 short-term/index.md
    if not idx.exists():
        content = f"""---
name: short-term-index
type: index
updated: {datetime.now().isoformat()}
---

| ID | 路径 | 标签 | 创建时间 | 召回次数 | 最后召回 | 状态 |
|----|------|------|----------|----------|----------|------|
"""
        idx.write_text(content, encoding='utf-8')
        print(f'  创建 {idx}')
    else:
        print(f'  跳过 {idx}: 已存在')

    # 初始化 long-term 子目录
    for sub in ['projects']:
        d = lt/sub
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            (d/'.gitkeep').touch()
            print(f'  创建 {d}')

    # 初始化 long-term 基础文件
    now = datetime.now().isoformat()
    files = {
        'user-profile.md': f'''---
name: user-profile
type: long_term
category: identity
created: {now}
updated: {now}
source: manual
manual_override: true
---

## 基本信息
- 姓名：张敬
- 身份：大二计算机科学与技术专业学生
- 研究方向：AI Agent、记忆架构、MCP

## Agent 名称
- Agent 名：Hermes
- 创建者：Nous Research
''',
        'env-config.md': f'''---
name: env-config
type: long_term
category: environment
created: {now}
updated: {now}
source: manual
manual_override: false
---

## 服务器
- 阿里云 ECS: 123.57.30.132
- 配置: 2核2G + 2GB swap + 70G盘

## 本地环境
- 系统代理: Clash 127.0.0.1:7897
- Obsidian 主库: D:\Obsidian Vault\我的知识库
- Hindsight: localhost:9177
''',
        'preferences.md': f'''---
name: preferences
type: long_term
category: behavior
created: {now}
updated: {now}
source: manual
manual_override: false
---

## 沟通偏好
- 语言：中文
- 风格：简洁直接，结论先行

## 工作偏好
- 编码工具：Claude Code
- 知识库：Obsidian
- 自动化：Hermes + cron
'''
    }
    for fname, tmpl in files.items():
        fp = lt/fname
        if not fp.exists():
            fp.write_text(tmpl, encoding='utf-8')
            print(f'  创建 {fp}')
        else:
            print(f'  跳过 {fp}: 已存在')

    print('\n初始化完成')

if __name__ == '__main__': main()
