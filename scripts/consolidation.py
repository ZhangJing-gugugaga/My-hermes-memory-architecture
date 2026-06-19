#!/usr/bin/env python3
"""
n# ⚠️ HIMRA v5.1: 此脚本仅在 Hindsight 不可用时作为回退方案使用。
# 如果 Hindsight 可用（localhost:9177 healthy），记忆生命周期由 Hindsight 机制管理。
HIMRA v5.0 Consolidation Script
cron: 每天凌晨 02:00 执行
巩固条件: retrieval_count >= 3 -> long-term, 14天未召回 -> summaries
"""
import shutil
from datetime import datetime, timedelta
from pathlib import Path

def get_repo_root():
    import subprocess
    r = subprocess.run(['git','rev-parse','--show-toplevel'], capture_output=True, text=True, check=True)
    return Path(r.stdout.strip())

def parse_fm(content):
    if not content.startswith('---'): return {}, content
    end = content.find('---', 3)
    if end == -1: return {}, content
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

def fmt_fm(meta):
    lines = ['---']
    for k, v in meta.items():
        if v is None: lines.append(f'{k}: null')
        elif isinstance(v, bool): lines.append(f'{k}: {"true" if v else "false"}')
        else: lines.append(f'{k}: {v}')
    lines.append('---')
    return '\n'.join(lines)

def parse_idx(path):
    if not path.exists(): return []
    entries, in_tbl = [], False
    for line in path.read_text(encoding='utf-8').splitlines():
        s = line.strip()
        if s.startswith('| ID'): in_tbl = True; continue
        if in_tbl and s.startswith('|---'): continue
        if in_tbl and s.startswith('|'):
            p = [x.strip() for x in s.split('|')]
            if len(p) >= 8:
                entries.append({'id':p[1],'path':p[2],'tags':p[3],'created':p[4],
                    'rc': int(p[5]) if p[5].isdigit() else 0,
                    'lr': p[6] if p[6]!='null' else None, 'status':p[7]})
    return entries

def write_idx(path, entries):
    lines = ['---','name: short-term-index','type: index',f'updated: {datetime.now().isoformat()}','---','',
        '| ID | 路径 | 标签 | 创建时间 | 召回次数 | 最后召回 | 状态 |',
        '|----|------|------|----------|----------|----------|------|']
    for e in entries:
        lr = e['lr'] or 'null'
        lines.append(f"| {e['id']} | {e['path']} | {e['tags']} | {e['created']} | {e['rc']} | {lr} | {e['status']} |")
    path.write_text('\n'.join(lines), encoding='utf-8')

def categorize(text):
    t = text.lower()
    if any(k in t for k in ['用户','姓名','身份','学生','agent名']): return 'identity'
    if any(k in t for k in ['服务器','ecs','配置','路径','代理','端口','cron']): return 'environment'
    if any(k in t for k in ['偏好','习惯','风格','语言','沟通']): return 'behavior'
    if any(k in t for k in ['项目','仓库','github','代码']): return 'project'
    return 'environment'

def tgt(cat, root):
    base = root/'memory'/'long-term'
    return base/{'identity':'user-profile.md','environment':'env-config.md','behavior':'preferences.md'}.get(cat,'env-config.md')

def main():
    root = get_repo_root()
    st, lt, su = root/'memory'/'short-term', root/'memory'/'long-term', root/'memory'/'summaries'
    idx = st/'index.md'
    print(f'[{datetime.now().isoformat()}] HIMRA v5.0 consolidation.py')
    lt.mkdir(parents=True, exist_ok=True); su.mkdir(parents=True, exist_ok=True)
    entries = parse_idx(idx)
    print(f'短期记忆: {len(entries)} 条')
    if not entries: print('无待处理'); return
    now, cutoff = datetime.now(), datetime.now()-timedelta(days=14)
    prom, arch, skip = [], [], []
    for e in entries:
        if e['status']!='active': skip.append(e); continue
        f = st/e['path']
        if not f.exists(): print(f'  跳过 {e["path"]}:不存在'); skip.append(e); continue
        meta, body = parse_fm(f.read_text(encoding='utf-8'))
        do_p = e['rc'] >= 3
        do_a = False
        if e['lr']:
            try: do_a = datetime.fromisoformat(e['lr']) < cutoff
            except: pass
        if do_p and not do_a:
            cat = categorize(body); t = tgt(cat, root)
            meta.update({'type':'long_term','source':'promoted','manual_override':False,'updated':now.isoformat(),'category':cat})
            if t.exists():
                em, eb = parse_fm(t.read_text(encoding='utf-8')); em['updated']=now.isoformat()
                t.write_text(fmt_fm(em)+'\n\n'+eb+f'\n\n## 迁移自 {meta.get("name","?")}\n\n'+body, encoding='utf-8')
            else:
                t.write_text(fmt_fm(meta)+'\n\n'+body, encoding='utf-8')
            e['status']='promoted'; prom.append((e,str(t)))
            print(f'  迁移 {e["path"]} -> {t.relative_to(root)}')
        elif do_a:
            ap = su/f'{meta.get("name","archived")}.md'
            meta.update({'type':'summary','updated':now.isoformat()})
            ap.write_text(fmt_fm(meta)+'\n\n'+body, encoding='utf-8')
            e['status']='archived'; arch.append((e,str(ap)))
            print(f'  归档 {e["path"]} -> {ap.relative_to(root)}')
        else: skip.append(e)
    write_idx(idx, entries)
    print(f'\n完成: 迁移={len(prom)} 归档={len(arch)} 跳过={len(skip)}')

if __name__ == '__main__': main()
