#!/usr/bin/env python3
"""
HIMRA v5.0 记忆文件校验器
校验 memory/ 目录下所有记忆文件的 frontmatter 是否符合规范
"""
from datetime import datetime
from pathlib import Path

VALID_TYPES = {"fact", "session", "source", "summary", "short_term", "long_term", "index"}

REQUIRED = {
    "fact": ["name","type","triggers","entities","temporal","always_load","priority","updated","summary"],
    "session": ["name","type","triggers","entities","temporal","always_load","priority","updated","summary"],
    "source": ["name","type","triggers","entities","temporal","always_load","priority","updated","summary"],
    "summary": ["name","type","triggers","entities","temporal","always_load","priority","updated","summary"],
    "short_term": ["name","type","created","last_retrieved","retrieval_count","source_session","tags","status","promoted_to"],
    "long_term": ["name","type","category","created","updated","source","manual_override"],
    "index": ["name","type","updated"],
}

def get_repo_root():
    import subprocess
    r = subprocess.run(['git','rev-parse','--show-toplevel'], capture_output=True, text=True, check=True)
    return Path(r.stdout.strip())

def parse_fm(content):
    if not content.startswith('---'): return None, content
    end = content.find('---', 3)
    if end == -1: return None, content
    meta = {}
    for line in content[3:end].strip().splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            k, v = k.strip(), v.strip()
            if v == 'null': v = None
            elif v == 'true': v = True
            elif v == 'false': v = False
            elif v.isdigit(): v = int(v)
            meta[k] = v
    return meta, content[end+3:].strip()

def validate(fp):
    try: content = fp.read_text(encoding='utf-8')
    except Exception as e: return [f"读取失败: {e}"]
    meta, _ = parse_fm(content)
    if meta is None: return ["缺少 YAML frontmatter"]
    t = meta.get('type')
    if t not in VALID_TYPES: return [f"未知类型: {t}"]
    errs = []
    for f in REQUIRED.get(t, []):
        if f not in meta: errs.append(f"缺少必填字段: {f}")
    if t == 'short_term':
        if meta.get('status') not in ['active','archived','promoted']: errs.append(f"status 无效: {meta.get('status')}")
        if not isinstance(meta.get('retrieval_count'), int): errs.append("retrieval_count 应为整数")
    elif t == 'long_term':
        if meta.get('category') not in ['identity','environment','behavior','project']: errs.append(f"category 无效: {meta.get('category')}")
        if meta.get('source') not in ['manual','promoted']: errs.append(f"source 无效: {meta.get('source')}")
        if not isinstance(meta.get('manual_override'), bool): errs.append("manual_override 应为布尔值")
    return errs

def main():
    root = get_repo_root()
    mem = root/'memory'
    print(f'[{datetime.now().isoformat()}] HIMRA v5.0 validate_memory.py')
    print(f'有效类型: {VALID_TYPES}')
    if not mem.exists(): print('错误: memory 目录不存在'); return
    total, ok, fail = 0, 0, 0
    for f in sorted(mem.rglob('*.md')):
        if f.name.startswith('.'): continue
        total += 1
        errs = validate(f)
        rel = f.relative_to(mem)
        if errs:
            fail += 1
            print(f'\n  FAIL {rel}:')
            for e in errs: print(f'    - {e}')
        else:
            ok += 1
            print(f'  OK   {rel}')
    print(f'\n完成: 总计={total} 通过={ok} 失败={fail}')

if __name__ == '__main__': main()
