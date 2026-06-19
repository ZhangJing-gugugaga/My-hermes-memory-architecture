#!/usr/bin/env python3
"""
consolidation.py — HIMRA v4.1 记忆巩固器
==========================================

对记忆库执行定期维护，支持三种时间尺度的巩固模式。

用法:
    python consolidation.py --mode daily          # 每日巩固（<10min）
    python consolidation.py --mode weekly         # 每周巩固（<2h）
    python consolidation.py --mode monthly        # 每月巩固
    python consolidation.py --mode daily --dry-run

模式说明:
    daily (每日, <10分钟):
        1. 找到本周新增/修改的记忆文件
        2. 检测新记忆与已有记忆的 cross_links（共享 entity 的记忆对）
        3. 更新 summaries/ 中引用了新记忆的主题
        4. 重新蒸馏 Planner Summary（优先级最高的摘要）

    weekly (每周, <2小时):
        1. 冗余检测：比较同 entity 下的记忆（共享 entity 的记忆对）
        2. 重新生成 top-100 高频记忆的关联性触发器（可选，需 LLM API）
        3. 超边重建（semantic_cluster 类型）

    monthly (每月):
        1. 标记 >90 天未访问的记忆 → 移到 archive/
        2. 压缩 archive/ 目录（合并旧文件）

依赖:
    pip install pyyaml

兼容:
    HIMRA v4.1 (v4-memory-max)
"""

import argparse
import glob
import gzip
import json
import os
import re
import shutil
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import yaml
except ImportError:
    sys.exit("错误: 需要安装 pyyaml。请运行: pip install pyyaml")

# ── 常量 ──────────────────────────────────────────────────

SUMMARY_MAX_LENGTH = 100
ARCHIVE_DIR = "archive"
DAILY_LOOKBACK_DAYS = 7
MONTHLY_ARCHIVE_DAYS = 90
TOP_N_HIGH_FREQ = 100

# ── 工具函数 ──────────────────────────────────────────────

class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @staticmethod
    def enable():
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except Exception:
                pass


def parse_frontmatter(filepath: str) -> Tuple[Optional[Dict], Optional[str], Optional[str]]:
    """解析 .md 文件的 YAML frontmatter 和正文。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return None, None, f"无法读取文件: {e}"

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", content, re.DOTALL)
    if not match:
        return None, None, "缺少 YAML frontmatter"

    yaml_text = match.group(1)
    body = match.group(2).strip()

    try:
        frontmatter = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        return None, None, f"YAML 解析错误: {e}"

    if not isinstance(frontmatter, dict):
        return None, None, "frontmatter 不是有效的 mapping"

    return frontmatter, body, None


def write_memory(filepath: str, frontmatter: Dict, body: str):
    """将 frontmatter + body 写回 .md 文件"""
    yaml_text = yaml.dump(
        frontmatter,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
    content = f"---\n{yaml_text}---\n\n{body}\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def scan_memory_files(memory_dir: str) -> List[str]:
    """扫描目录下所有 .md 文件"""
    pattern = os.path.join(memory_dir, "**", "*.md")
    files = glob.glob(pattern, recursive=True)
    files = [f for f in files if not os.path.basename(f).startswith(".")]
    files = [f for f in files if "README" not in os.path.basename(f).upper()]
    return sorted(files)


def parse_date(value: Any) -> Optional[date]:
    """将 YAML 日期或字符串解析为 date 对象"""
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def get_file_mtime(filepath: str) -> float:
    """获取文件修改时间（Unix 时间戳）"""
    return os.path.getmtime(filepath)


def load_all_memories(memory_dir: str) -> List[Dict[str, Any]]:
    """加载所有记忆文件，返回解析后的列表"""
    files = scan_memory_files(memory_dir)
    memories = []
    for filepath in files:
        fm, body, err = parse_frontmatter(filepath)
        if err or fm is None:
            continue
        if "name" not in fm:
            fm["name"] = os.path.splitext(os.path.basename(filepath))[0]
        memories.append({
            "filepath": filepath,
            "relpath": os.path.relpath(filepath, memory_dir),
            "frontmatter": fm,
            "body": body or "",
        })
    return memories


# ── 每日巩固器 ────────────────────────────────────────────

class DailyConsolidator:
    """每日巩固：cross_links 检测 + summaries 更新"""

    def __init__(
        self,
        memory_dir: str,
        db_path: str,
        dry_run: bool = False,
    ):
        self.memory_dir = os.path.abspath(memory_dir)
        self.db_path = db_path
        self.dry_run = dry_run
        self.memories: List[Dict] = []
        self.new_or_modified: List[Dict] = []
        self.linked_pairs: List[Tuple[str, str, str]] = []  # (mem_a, mem_b, shared_entity)

    def run(self):
        print(f"{Colors.BOLD}═══ HIMRA 每日巩固 (daily) ═══{Colors.RESET}")
        print(f"记忆目录: {self.memory_dir}")
        print(f"日期: {date.today().isoformat()}")
        if self.dry_run:
            print(f"模式: {Colors.CYAN}预览模式{Colors.RESET}")
        print()

        # 1. 加载所有记忆
        self._load_memories()

        # 2. 找到本周新增/修改的记忆
        self._find_recent_changes()

        # 3. 检测 cross_links
        self._detect_cross_links()

        # 4. 更新 summaries
        self._update_summaries()

        # 5. 蒸馏 Planner Summary
        self._distill_planner_summary()

        # 6. 输出汇总
        self._report()

    def _load_memories(self):
        """加载所有记忆"""
        print(f"{Colors.BOLD}[1/5] 加载记忆文件...{Colors.RESET}")
        self.memories = load_all_memories(self.memory_dir)
        print(f"  加载了 {len(self.memories)} 条记忆")
        print()

    def _find_recent_changes(self):
        """找到本周新增/修改的记忆"""
        print(f"{Colors.BOLD}[2/5] 检测本周变更...{Colors.RESET}")
        cutoff = time.time() - DAILY_LOOKBACK_DAYS * 86400
        self.new_or_modified = [
            m for m in self.memories if get_file_mtime(m["filepath"]) >= cutoff
        ]
        print(f"  本周变更: {len(self.new_or_modified)} 条")
        for m in self.new_or_modified:
            mtime = datetime.fromtimestamp(get_file_mtime(m["filepath"]))
            print(f"    - {m['relpath']} ({mtime.strftime('%m-%d %H:%M')})")
        print()

    def _detect_cross_links(self):
        """检测新记忆与已有记忆的 cross_links（共享 entity）"""
        print(f"{Colors.BOLD}[3/5] 检测 cross_links（共享实体）...{Colors.RESET}")

        if not self.new_or_modified:
            print(f"  无新变更，跳过")
            print()
            return

        # 构建 entity → 记忆名列表
        entity_map: Dict[str, List[str]] = defaultdict(list)
        for mem in self.memories:
            mem_name = mem["frontmatter"].get("name", mem["relpath"])
            entities = mem["frontmatter"].get("entities", [])
            if isinstance(entities, list):
                for ent in entities:
                    if isinstance(ent, dict):
                        ename = ent.get("name", "")
                        if ename:
                            entity_map[ename].append(mem_name)

        # 对每个新记忆，找共享 entity 的已有记忆
        existing_names = {
            m["frontmatter"].get("name", m["relpath"])
            for m in self.memories
            if m not in self.new_or_modified
        }

        new_pairs: Set[Tuple[str, str, str]] = set()
        for mem in self.new_or_modified:
            mem_name = mem["frontmatter"].get("name", mem["relpath"])
            entities = mem["frontmatter"].get("entities", [])
            if not isinstance(entities, list):
                continue

            for ent in entities:
                if not isinstance(ent, dict):
                    continue
                ename = ent.get("name", "")
                linked = entity_map.get(ename, [])
                for linked_name in linked:
                    if linked_name != mem_name and linked_name in existing_names:
                        pair = tuple(sorted([mem_name, linked_name]))
                        new_pairs.add((pair[0], pair[1], ename))

        self.linked_pairs = sorted(new_pairs)

        if self.linked_pairs:
            print(f"  发现 {len(self.linked_pairs)} 对共享实体的记忆:")
            for mem_a, mem_b, entity in self.linked_pairs:
                print(f"    {mem_a} ←→ {mem_b} (共享: {entity})")
                # 自动添加 cross_links（如果尚未存在）
                if not self.dry_run:
                    self._add_cross_link(mem_a, mem_b, entity)
        else:
            print(f"  未发现新的共享实体对")
        print()

    def _add_cross_link(self, mem_a: str, mem_b: str, entity: str):
        """在两个记忆之间添加 exemplify 类型的 cross_link"""
        # 找到两个记忆对象
        mem_a_obj = next(
            (m for m in self.memories if m["frontmatter"].get("name") == mem_a), None
        )
        mem_b_obj = next(
            (m for m in self.memories if m["frontmatter"].get("name") == mem_b), None
        )

        if not mem_a_obj or not mem_b_obj:
            return

        for source_obj, target_name in [(mem_a_obj, mem_b), (mem_b_obj, mem_a)]:
            fm = source_obj["frontmatter"]
            existing_links = fm.get("cross_links", [])
            if not isinstance(existing_links, list):
                existing_links = []

            # 检查是否已有指向目标的链接
            existing_targets = {
                link.get("target") for link in existing_links if isinstance(link, dict)
            }
            if target_name not in existing_targets:
                relpath = source_obj["relpath"]
                target_rel = os.path.basename(target_name)
                if not target_rel.endswith(".md"):
                    target_rel += ".md"
                # 推断目标路径
                target_type = "facts"  # 默认
                for m in self.memories:
                    if m["frontmatter"].get("name") == target_name:
                        target_type = m["frontmatter"].get("type", "facts")
                        if target_type == "session":
                            target_type = "sessions"
                        elif target_type == "source":
                            target_type = "sources"
                        elif target_type == "summary":
                            target_type = "summaries"
                        else:
                            target_type = "facts"
                        break
                existing_links.append({
                    "target": f"{target_type}/{target_name}.md",
                    "relation": "exemplifies",
                })
                fm["cross_links"] = existing_links
                write_memory(source_obj["filepath"], fm, source_obj["body"])
                print(f"    {Colors.GREEN}✓ 添加 cross_link: {source_obj['relpath']} → {target_name}{Colors.RESET}")

    def _update_summaries(self):
        """更新 summaries/ 中引用了新记忆的主题"""
        print(f"{Colors.BOLD}[4/5] 更新 summaries...{Colors.RESET}")

        summaries = [m for m in self.memories if m["frontmatter"].get("type") == "summary"]
        if not summaries:
            print(f"  无 summary 类型记忆，跳过")
            print()
            return

        new_names = {
            m["frontmatter"].get("name", m["relpath"]) for m in self.new_or_modified
        }

        updated_count = 0
        for summary in summaries:
            fm = summary["frontmatter"]
            coverage = fm.get("coverage", [])
            if not isinstance(coverage, list):
                coverage = []

            # 检查新记忆是否属于此 summary 的 coverage 范围
            summary_entities = {
                e.get("name", "") for e in fm.get("entities", []) if isinstance(e, dict)
            }
            needs_update = False

            for new_mem in self.new_or_modified:
                new_entities = {
                    e.get("name", "")
                    for e in new_mem["frontmatter"].get("entities", [])
                    if isinstance(e, dict)
                }
                # 如果共享 entity 且不在 coverage 中
                if summary_entities & new_entities:
                    new_name = new_mem["frontmatter"].get("name", "")
                    if new_name and new_name not in coverage:
                        coverage.append(new_name)
                        needs_update = True

            if needs_update:
                fm["coverage"] = coverage
                fm["updated"] = date.today().isoformat()
                if not self.dry_run:
                    write_memory(summary["filepath"], fm, summary["body"])
                updated_count += 1
                print(f"  {Colors.GREEN}✓ 更新 summary: {summary['relpath']}{Colors.RESET}")
                print(f"    新增 coverage: {[c for c in coverage if c in new_names]}")

        if updated_count == 0:
            print(f"  无需更新")
        print()

    def _distill_planner_summary(self):
        """重新蒸馏 Planner Summary（优先级最高的 summary 类型记忆）"""
        print(f"{Colors.BOLD}[5/5] 蒸馏 Planner Summary...{Colors.RESET}")

        # 找到优先级最高的 summary
        summaries = [m for m in self.memories if m["frontmatter"].get("type") == "summary"]
        if not summaries:
            print(f"  无 summary 类型记忆，跳过")
            print()
            return

        # 按优先级排序: high > medium > low
        priority_order = {"high": 0, "medium": 1, "low": 2}
        summaries.sort(key=lambda m: priority_order.get(m["frontmatter"].get("priority", "low"), 3))

        planner = summaries[0]
        fm = planner["frontmatter"]
        coverage = fm.get("coverage", [])

        # 生成 Planner Summary 文本（拼接所有 coverage 子主题摘要）
        if not self.dry_run and coverage:
            parts = [f"## Planner Summary (自动生成 {date.today().isoformat()})"]
            for item in coverage[:20]:  # 限制前 20 个
                parts.append(f"- {item}")

            # 更新 summary 字段
            fm["summary"] = f"Planner 摘要: 覆盖 {len(coverage)} 个子主题"
            fm["updated"] = date.today().isoformat()
            write_memory(planner["filepath"], fm, planner["body"])

            print(f"  {Colors.GREEN}✓ 已更新 Planner Summary: {planner['relpath']}{Colors.RESET}")
            print(f"    覆盖主题数: {len(coverage)}")
        else:
            print(f"  Planner Summary: {planner['relpath']} (优先级: {fm.get('priority')})")
        print()

    def _report(self):
        """输出每日巩固报告"""
        print(f"{Colors.BOLD}{'─' * 45}{Colors.RESET}")
        print(f"{Colors.BOLD}每日巩固报告{Colors.RESET}")
        print(f"  本周变更记忆: {len(self.new_or_modified)}")
        print(f"  新 cross_links: {len(self.linked_pairs)}")
        if self.dry_run:
            print(f"  {Colors.CYAN}[预览模式] 未实际修改文件{Colors.RESET}")
        print()


# ── 每周巩固器 ────────────────────────────────────────────

class WeeklyConsolidator:
    """每周巩固：冗余检测 + 触发器再生 + 超边重建"""

    def __init__(
        self,
        memory_dir: str,
        db_path: str,
        llm_api_url: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        dry_run: bool = False,
    ):
        self.memory_dir = os.path.abspath(memory_dir)
        self.db_path = db_path
        self.llm_api_url = llm_api_url
        self.llm_api_key = llm_api_key
        self.dry_run = dry_run
        self.memories: List[Dict] = []
        self.redundant_pairs: List[Tuple[str, str, float]] = []  # (mem_a, mem_b, similarity)

    def run(self):
        print(f"{Colors.BOLD}═══ HIMRA 每周巩固 (weekly) ═══{Colors.RESET}")
        print(f"记忆目录: {self.memory_dir}")
        print(f"日期: {date.today().isoformat()}")
        if self.dry_run:
            print(f"模式: {Colors.CYAN}预览模式{Colors.RESET}")
        print()

        self._load_memories()

        # 1. 冗余检测
        self._detect_redundancy()

        # 2. 触发器再生（需 LLM API）
        self._regenerate_triggers()

        # 3. 超边重建
        self._rebuild_hyperedges()

        self._report()

    def _load_memories(self):
        print(f"{Colors.BOLD}[1/3] 加载记忆文件...{Colors.RESET}")
        self.memories = load_all_memories(self.memory_dir)
        print(f"  加载了 {len(self.memories)} 条记忆")
        print()

    def _detect_redundancy(self):
        """冗余检测：比较同 entity 下的记忆"""
        print(f"{Colors.BOLD}[2/3] 冗余检测...{Colors.RESET}")

        # 构建 entity → 记忆列表
        entity_memories: Dict[str, List[Dict]] = defaultdict(list)
        for mem in self.memories:
            entities = mem["frontmatter"].get("entities", [])
            if isinstance(entities, list):
                for ent in entities:
                    if isinstance(ent, dict):
                        ename = ent.get("name", "")
                        if ename:
                            entity_memories[ename].append(mem)

        # 对每个 entity，比较其下所有记忆对
        redundant = []
        for entity, mems in entity_memories.items():
            if len(mems) < 2:
                continue

            for i in range(len(mems)):
                for j in range(i + 1, len(mems)):
                    # 简化的冗余检测：基于 summary 和实体重叠
                    sim = self._compute_similarity(mems[i], mems[j])
                    if sim > 0.7:  # 阈值
                        name_a = mems[i]["frontmatter"].get("name", mems[i]["relpath"])
                        name_b = mems[j]["frontmatter"].get("name", mems[j]["relpath"])
                        redundant.append((name_a, name_b, sim))

        self.redundant_pairs = sorted(redundant, key=lambda x: x[2], reverse=True)

        if self.redundant_pairs:
            print(f"  发现 {len(self.redundant_pairs)} 对可能冗余的记忆 (相似度 > 0.7):")
            for mem_a, mem_b, sim in self.redundant_pairs:
                print(f"    {mem_a} ←→ {mem_b} (相似度: {sim:.3f})")
                # 标记 contradictory 关系
                if not self.dry_run:
                    self._mark_contradiction(mem_a, mem_b)
        else:
            print(f"  未发现明显冗余")
        print()

    def _compute_similarity(self, mem_a: Dict, mem_b: Dict) -> float:
        """计算两条记忆的简化相似度（基于实体重叠 + 关键词重叠）"""
        fm_a = mem_a["frontmatter"]
        fm_b = mem_b["frontmatter"]

        # 实体 Jaccard
        entities_a = {
            e.get("name", "") for e in fm_a.get("entities", []) if isinstance(e, dict)
        }
        entities_b = {
            e.get("name", "") for e in fm_b.get("entities", []) if isinstance(e, dict)
        }
        union_e = entities_a | entities_b
        entity_sim = len(entities_a & entities_b) / len(union_e) if union_e else 0

        # 关键词 Jaccard
        kw_a = set()
        kw_b = set()
        triggers_a = fm_a.get("triggers", {})
        triggers_b = fm_b.get("triggers", {})
        if isinstance(triggers_a, dict):
            desc = triggers_a.get("descriptive", {})
            if isinstance(desc, dict):
                kw_a = set(desc.get("keywords", []))
        if isinstance(triggers_b, dict):
            desc = triggers_b.get("descriptive", {})
            if isinstance(desc, dict):
                kw_b = set(desc.get("keywords", []))
        union_k = kw_a | kw_b
        kw_sim = len(kw_a & kw_b) / len(union_k) if union_k else 0

        # 加权平均
        return 0.6 * entity_sim + 0.4 * kw_sim

    def _mark_contradiction(self, mem_a: str, mem_b: str):
        """在两条冗余记忆间添加 contradictory cross_link"""
        mem_a_obj = next(
            (m for m in self.memories if m["frontmatter"].get("name") == mem_a), None
        )
        mem_b_obj = next(
            (m for m in self.memories if m["frontmatter"].get("name") == mem_b), None
        )

        if not mem_a_obj or not mem_b_obj:
            return

        for source_obj, target_name in [(mem_a_obj, mem_b), (mem_b_obj, mem_a)]:
            fm = source_obj["frontmatter"]
            links = fm.get("cross_links", [])
            if not isinstance(links, list):
                links = []

            existing = {l.get("target") for l in links if isinstance(l, dict)}
            if target_name not in existing:
                links.append({"target": f"facts/{target_name}.md", "relation": "contradicts"})
                fm["cross_links"] = links
                write_memory(source_obj["filepath"], fm, source_obj["body"])

    def _regenerate_triggers(self):
        """重新生成 top-100 高频记忆的关联性触发器（需 LLM API）"""
        print(f"{Colors.BOLD}[可选] 触发器再生...{Colors.RESET}")

        if not self.llm_api_url or not self.llm_api_key:
            print(f"  {Colors.YELLOW}⚠ 未配置 LLM API（--llm-api-url / --llm-api-key），跳过触发器再生{Colors.RESET}")
            print(f"  提示: 设置环境变量 HIMRA_LLM_URL 和 HIMRA_LLM_KEY 或通过参数传入")
            print()
            return

        # 按 access_count 排序取 top-100
        ranked = sorted(
            self.memories,
            key=lambda m: m["frontmatter"].get("access_count", 0),
            reverse=True,
        )[:TOP_N_HIGH_FREQ]

        if not ranked:
            print(f"  无高频记忆，跳过")
            print()
            return

        print(f"  待再生触发器: {len(ranked)} 条 (top-{TOP_N_HIGH_FREQ})")
        regenerated = 0

        for mem in ranked:
            fm = mem["frontmatter"]
            mem_type = fm.get("type", "fact")

            # 根据类型决定 query 数量
            query_counts = {
                "fact": (5, 10),
                "session": (3, 5),
                "source": (10, 20),
                "summary": (5, 8),
            }
            min_q, max_q = query_counts.get(mem_type, (3, 5))

            try:
                new_queries = self._call_llm_generate_queries(fm, mem["body"], min_q, max_q)
                if new_queries:
                    triggers = fm.get("triggers", {})
                    if isinstance(triggers, dict):
                        assoc = triggers.get("associative", {})
                        if isinstance(assoc, dict):
                            assoc["queries"] = new_queries
                            fm["triggers"] = triggers
                            if not self.dry_run:
                                write_memory(mem["filepath"], fm, mem["body"])
                            regenerated += 1
            except Exception as e:
                print(f"  {Colors.RED}✗ {mem['relpath']}: LLM 调用失败 — {e}{Colors.RESET}")

        print(f"  已再生: {regenerated}/{len(ranked)}")
        print()

    def _call_llm_generate_queries(
        self, fm: Dict, body: str, min_count: int, max_count: int
    ) -> List[Dict]:
        """调用 LLM API 生成关联性查询"""
        # 构建 prompt
        name = fm.get("name", "unknown")
        mem_type = fm.get("type", "fact")
        summary = fm.get("summary", body[:200])
        entities = fm.get("entities", [])
        entity_names = ", ".join(
            e.get("name", "") for e in entities if isinstance(e, dict)
        ) if isinstance(entities, list) else ""

        prompt = (
            f"你是一个记忆系统的触发器生成器。为以下记忆生成 {min_count}-{max_count} 个关联性查询。\n\n"
            f"记忆名称: {name}\n"
            f"类型: {mem_type}\n"
            f"实体: {entity_names}\n"
            f"摘要: {summary}\n"
            f"正文: {body[:500]}\n\n"
            f"对每个查询，评估其置信度 (0-1)。\n"
            f"返回格式为 JSON 数组: [{{\"query\": \"...\", \"confidence\": 0.XX}}]"
        )

        import urllib.request

        payload = json.dumps({
            "model": "claude-fable-5",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")

        req = urllib.request.Request(
            self.llm_api_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.llm_api_key,
                "anthropic-version": "2023-06-01",
            },
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        # 解析响应
        content = result.get("content", [{}])[0].get("text", "[]")
        # 尝试提取 JSON
        json_match = re.search(r"\[.*\]", content, re.DOTALL)
        if json_match:
            queries = json.loads(json_match.group())
            if isinstance(queries, list):
                # 确保置信度在 0-1 之间
                for q in queries:
                    if isinstance(q, dict):
                        q["confidence"] = max(0.0, min(1.0, float(q.get("confidence", 0.5))))
                return queries
        return []

    def _rebuild_hyperedges(self):
        """超边重建（semantic_cluster 类型）"""
        print(f"{Colors.BOLD}[3/3] 超边重建...{Colors.RESET}")

        if not os.path.exists(self.db_path):
            print(f"  {Colors.YELLOW}⚠ 数据库不存在: {self.db_path}，请先运行 init_indices.py{Colors.RESET}")
            print()
            return

        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")

        # 清除旧 semantic_cluster 超边
        conn.execute("DELETE FROM hyperedge_index WHERE edge_type = 'semantic_cluster'")

        # 基于实体共现重建 semantic_cluster 超边
        # 找出 3+ 记忆共现的实体组
        cursor = conn.cursor()
        rows = cursor.execute(
            "SELECT entity_name, COUNT(DISTINCT memory_name) as cnt, "
            "GROUP_CONCAT(DISTINCT memory_name) as mems "
            "FROM entity_index GROUP BY entity_name HAVING cnt >= 3"
        ).fetchall()

        if self.dry_run:
            print(f"  预览: 将创建 {len(rows)} 条 semantic_cluster 超边")
            for entity_name, cnt, mems in rows[:10]:
                mem_list = mems.split(",")
                print(f"    {entity_name}: {cnt} 条记忆 — {', '.join(mem_list[:5])}...")
            if len(rows) > 10:
                print(f"    ... 还有 {len(rows) - 10} 条")
        else:
            for entity_name, cnt, mems in rows:
                hyperedge_id = f"cluster_{entity_name}"
                mem_list = sorted(mems.split(","))
                nodes = json.dumps(mem_list, ensure_ascii=False)
                conn.execute(
                    "INSERT OR REPLACE INTO hyperedge_index VALUES (?, ?, 'semantic_cluster', ?)",
                    (hyperedge_id, nodes, cnt),
                )
            conn.commit()
            print(f"  {Colors.GREEN}✓ 已创建 {len(rows)} 条 semantic_cluster 超边{Colors.RESET}")

        conn.close()
        print()

    def _report(self):
        print(f"{Colors.BOLD}{'─' * 45}{Colors.RESET}")
        print(f"{Colors.BOLD}每周巩固报告{Colors.RESET}")
        print(f"  冗余记忆对: {len(self.redundant_pairs)}")
        if self.dry_run:
            print(f"  {Colors.CYAN}[预览模式] 未实际修改文件{Colors.RESET}")
        print()


# ── 每月巩固器 ────────────────────────────────────────────

class MonthlyConsolidator:
    """每月巩固：归档旧记忆 + 压缩 archive"""

    def __init__(
        self,
        memory_dir: str,
        db_path: str,
        archive_days: int = MONTHLY_ARCHIVE_DAYS,
        dry_run: bool = False,
    ):
        self.memory_dir = os.path.abspath(memory_dir)
        self.db_path = db_path
        self.archive_days = archive_days
        self.dry_run = dry_run
        self.archive_dir = os.path.join(memory_dir, ARCHIVE_DIR)
        self.memories: List[Dict] = []
        self.to_archive: List[Dict] = []

    def run(self):
        print(f"{Colors.BOLD}═══ HIMRA 每月巩固 (monthly) ═══{Colors.RESET}")
        print(f"记忆目录: {self.memory_dir}")
        print(f"日期: {date.today().isoformat()}")
        print(f"归档阈值: {self.archive_days} 天未访问")
        if self.dry_run:
            print(f"模式: {Colors.CYAN}预览模式{Colors.RESET}")
        print()

        # 1. 标记旧记忆
        self._find_stale_memories()

        # 2. 归档
        self._archive_memories()

        # 3. 压缩 archive
        self._compress_archive()

        # 4. 报告
        self._report()

    def _find_stale_memories(self):
        """找到 >90 天未访问的记忆"""
        print(f"{Colors.BOLD}[1/3] 查找过期记忆...{Colors.RESET}")
        self.memories = load_all_memories(self.memory_dir)

        # 排除已在 archive/ 中的文件
        self.memories = [
            m for m in self.memories
            if ARCHIVE_DIR not in m["relpath"].replace("\\", "/").split("/")
        ]

        cutoff = date.today() - timedelta(days=self.archive_days)

        for mem in self.memories:
            fm = mem["frontmatter"]

            # 检查 last_accessed
            last_accessed = parse_date(fm.get("last_accessed"))
            if not last_accessed:
                # 假设从未访问过，用 updated 代替
                last_accessed = parse_date(fm.get("updated"))

            if last_accessed and last_accessed < cutoff:
                self.to_archive.append(mem)

        if self.to_archive:
            print(f"  找到 {len(self.to_archive)} 条过期记忆:")
            for mem in self.to_archive:
                la = fm.get("last_accessed", fm.get("updated", "?"))
                print(f"    - {mem['relpath']} (最后访问: {la})")
        else:
            print(f"  无过期记忆")
        print()

    def _archive_memories(self):
        """将过期记忆移到 archive/ 目录"""
        print(f"{Colors.BOLD}[2/3] 归档过期记忆...{Colors.RESET}")

        if not self.to_archive:
            print(f"  无需要归档的记忆")
            print()
            return

        if self.dry_run:
            print(f"  预览: 将移动 {len(self.to_archive)} 条记忆到 {self.archive_dir}/")
            for mem in self.to_archive:
                print(f"    → {ARCHIVE_DIR}/{mem['relpath']}")
            print()
            return

        os.makedirs(self.archive_dir, exist_ok=True)

        for mem in self.to_archive:
            src = mem["filepath"]
            # 保持子目录结构
            rel = mem["relpath"].replace("\\", "/")
            dst = os.path.join(self.archive_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)

            # 更新 frontmatter 标记
            fm = mem["frontmatter"]
            fm["valid_until"] = date.today().isoformat()

            try:
                shutil.move(src, dst)
                print(f"  {Colors.GREEN}✓ 已归档: {rel} → {ARCHIVE_DIR}/{rel}{Colors.RESET}")
            except Exception as e:
                print(f"  {Colors.RED}✗ 归档失败: {rel} — {e}{Colors.RESET}")

        print()

    def _compress_archive(self):
        """压缩 archive/ 目录（将 >30 天的 .md 文件 gzip 压缩）"""
        print(f"{Colors.BOLD}[3/3] 压缩 archive 目录...{Colors.RESET}")

        if not os.path.isdir(self.archive_dir):
            print(f"  archive/ 目录不存在，跳过")
            print()
            return

        # 找到 archive 中 >30 天且未压缩的 .md 文件
        cutoff = time.time() - 30 * 86400
        archive_files = glob.glob(os.path.join(self.archive_dir, "**", "*.md"), recursive=True)

        to_compress = [f for f in archive_files if os.path.getmtime(f) < cutoff]
        # 排除已经压缩的
        to_compress = [f for f in to_compress if not f.endswith(".gz")]

        if not to_compress:
            print(f"  无需压缩的文件")
            print()
            return

        if self.dry_run:
            print(f"  预览: 将压缩 {len(to_compress)} 个文件")
            for f in to_compress[:10]:
                size = os.path.getsize(f)
                print(f"    {os.path.relpath(f, self.archive_dir)} ({size:,} bytes)")
            if len(to_compress) > 10:
                print(f"    ... 还有 {len(to_compress) - 10} 个")
            print()
            return

        saved_bytes = 0
        for filepath in to_compress:
            try:
                # gzip 压缩
                gz_path = filepath + ".gz"
                with open(filepath, "rb") as f_in:
                    with gzip.open(gz_path, "wb", compresslevel=6) as f_out:
                        f_out.write(f_in.read())

                orig_size = os.path.getsize(filepath)
                new_size = os.path.getsize(gz_path)
                saved_bytes += orig_size - new_size

                # 删除原始文件
                os.remove(filepath)

                rel = os.path.relpath(filepath, self.archive_dir)
                print(f"  {Colors.GREEN}✓ 压缩: {rel} ({orig_size:,} → {new_size:,} bytes){Colors.RESET}")
            except Exception as e:
                print(f"  {Colors.RED}✗ 压缩失败: {os.path.relpath(filepath, self.archive_dir)} — {e}{Colors.RESET}")

        print(f"  节省空间: {saved_bytes:,} bytes ({saved_bytes / 1024:.1f} KB)")
        print()

    def _report(self):
        print(f"{Colors.BOLD}{'─' * 45}{Colors.RESET}")
        print(f"{Colors.BOLD}每月巩固报告{Colors.RESET}")
        print(f"  过期记忆: {len(self.to_archive)}")
        if self.dry_run:
            print(f"  {Colors.CYAN}[预览模式] 未实际修改文件{Colors.RESET}")
        print()


# ── 主逻辑 ────────────────────────────────────────────────

def main():
    Colors.enable()

    parser = argparse.ArgumentParser(
        description="HIMRA v4.1 记忆巩固器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python consolidation.py --mode daily           # 每日巩固
  python consolidation.py --mode weekly          # 每周巩固
  python consolidation.py --mode monthly         # 每月巩固
  python consolidation.py --mode daily --dry-run # 预览模式
  python consolidation.py --mode weekly --llm-api-url https://api.anthropic.com/v1/messages \\
      --llm-api-key sk-ant-xxx                   # 带 LLM 的每周巩固
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["daily", "weekly", "monthly"],
        required=True,
        help="巩固模式: daily (每日) / weekly (每周) / monthly (每月)",
    )
    parser.add_argument(
        "--memory-dir",
        default="memory",
        help="记忆文件目录（默认: memory/）",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="SQLite 数据库路径（默认: <memory-dir>/.indices.db）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅预览，不实际修改文件",
    )
    parser.add_argument(
        "--llm-api-url",
        default=None,
        help="LLM API 端点（用于触发器再生，支持 Anthropic Messages API）",
    )
    parser.add_argument(
        "--llm-api-key",
        default=None,
        help="LLM API 密钥",
    )
    parser.add_argument(
        "--archive-days",
        type=int,
        default=MONTHLY_ARCHIVE_DAYS,
        help=f"归档阈值（天），默认 {MONTHLY_ARCHIVE_DAYS}",
    )
    args = parser.parse_args()

    # 环境变量回退
    llm_url = args.llm_api_url or os.environ.get("HIMRA_LLM_URL")
    llm_key = args.llm_api_key or os.environ.get("HIMRA_LLM_KEY")

    memory_dir = os.path.abspath(args.memory_dir)
    if not os.path.isdir(memory_dir):
        sys.exit(f"错误: 目录不存在 — {memory_dir}")

    db_path = args.db_path or os.path.join(memory_dir, ".indices.db")

    if args.mode == "daily":
        consolidator = DailyConsolidator(
            memory_dir=memory_dir,
            db_path=db_path,
            dry_run=args.dry_run,
        )
    elif args.mode == "weekly":
        consolidator = WeeklyConsolidator(
            memory_dir=memory_dir,
            db_path=db_path,
            llm_api_url=llm_url,
            llm_api_key=llm_key,
            dry_run=args.dry_run,
        )
    elif args.mode == "monthly":
        consolidator = MonthlyConsolidator(
            memory_dir=memory_dir,
            db_path=db_path,
            archive_days=args.archive_days,
            dry_run=args.dry_run,
        )
    else:
        sys.exit(f"未知模式: {args.mode}")

    consolidator.run()


if __name__ == "__main__":
    main()
