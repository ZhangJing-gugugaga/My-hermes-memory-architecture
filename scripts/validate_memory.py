#!/usr/bin/env python3
"""
validate_memory.py — HIMRA v4.1 记忆文件校验器
================================================

扫描 memory/ 目录下所有 .md 文件，解析 YAML frontmatter，
对照 SPEC v4.1 规范进行校验，输出通过/失败清单及错误详情。

用法:
    python validate_memory.py [--fix] [--dry-run] [--dir memory/]

功能:
    1. 扫描指定目录下所有 .md 文件
    2. 解析 YAML frontmatter（支持 v3 向后兼容）
    3. 校验必填字段、类型约束、枚举值、格式规范
    4. 支持 --fix 自动修复简单问题（补全缺失字段的默认值）
    5. 支持 --dry-run 模式，仅报告不修改
    6. 输出带颜色的通过/失败清单

依赖:
    pip install pyyaml

兼容:
    HIMRA v4.1 (v4-memory-max) / v3 向前兼容
"""

import argparse
import glob
import os
import re
import sys
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    sys.exit("错误: 需要安装 pyyaml。请运行: pip install pyyaml")

# ── 常量 ──────────────────────────────────────────────────

VALID_TYPES = {"fact", "session", "source", "summary"}
VALID_PRIORITIES = {"high", "medium", "low"}
VALID_RELATIONS = {
    "depends_on",
    "contradicts",
    "generalizes",
    "exemplifies",
    "temporally_after",
}
VALID_ENTITY_TYPES = {
    "cloud_server",
    "system_config",
    "memory_size",
    "architecture",
    "protocol",
    "framework",
    "paper",
    "person",
    "tool",
    "concept",
    "event",
    "other",
}
VALID_SOURCE_TYPES = {"paper", "repo", "article", "conversation", "crawl"}
VALID_EDGE_TYPES = {"co_occurrence", "semantic_cluster"}

REQUIRED_FIELDS = [
    "name",
    "type",
    "triggers",
    "entities",
    "temporal",
    "always_load",
    "priority",
    "updated",
    "summary",
]

SUMMARY_MAX_LENGTH = 100

# ── 工具函数 ──────────────────────────────────────────────

class Colors:
    """ANSI 颜色码（Windows 兼容）"""
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    @staticmethod
    def enable():
        """在 Windows 上启用 ANSI 支持"""
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except Exception:
                pass


def parse_frontmatter(filepath: str) -> Tuple[Optional[Dict], Optional[str], Optional[str]]:
    """
    解析 .md 文件的 YAML frontmatter 和正文。

    返回: (frontmatter_dict, body_text, error_message)
    成功时 error_message 为 None。
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return None, None, f"无法读取文件: {e}"

    # 匹配 YAML frontmatter（--- 开头和结尾）
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", content, re.DOTALL)
    if not match:
        return None, None, "缺少 YAML frontmatter（未找到 '---' 分隔符）"

    yaml_text = match.group(1)
    body = match.group(2).strip()

    try:
        frontmatter = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        return None, None, f"YAML 解析错误: {e}"

    if frontmatter is None:
        return {}, body, None  # 空 frontmatter

    if not isinstance(frontmatter, dict):
        return None, None, "YAML frontmatter 必须是 mapping（键值对）"

    return frontmatter, body, None


def is_date(value: Any) -> bool:
    """检查值是否为日期对象或 YYYY-MM-DD 字符串。"""
    if isinstance(value, date):
        return True
    if isinstance(value, str):
        return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", value))
    return False


def is_date_or_null(value: Any) -> bool:
    """检查值是否为日期、null 或空。"""
    if value is None:
        return True
    return is_date(value)


# ── 校验器 ────────────────────────────────────────────────

class ValidationError:
    """单条校验错误"""

    def __init__(self, field: str, message: str, fixable: bool = False):
        self.field = field
        self.message = message
        self.fixable = fixable

    def __str__(self):
        fix_tag = " [可自动修复]" if self.fixable else ""
        return f"  ✗ {self.field}: {self.message}{fix_tag}"


class MemoryValidator:
    """HIMRA v4.1 记忆校验器"""

    def __init__(self, filepath: str, fix: bool = False, dry_run: bool = False):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.fix = fix
        self.dry_run = dry_run
        self.frontmatter: Optional[Dict] = None
        self.body: Optional[str] = None
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []
        self.fixes_applied: List[str] = []
        self._v3_upgraded = False

    def validate(self) -> bool:
        """执行全部校验。返回 True 表示通过。"""
        self.errors = []
        self.warnings = []
        self.fixes_applied = []

        # 解析
        fm, body, err = parse_frontmatter(self.filepath)
        if err:
            self.errors.append(ValidationError("frontmatter", err))
            return False
        self.frontmatter = fm or {}
        self.body = body or ""

        # 如果 frontmatter 为空，全部必填字段缺失
        if not self.frontmatter:
            self.errors.append(
                ValidationError("frontmatter", "YAML frontmatter 为空，缺少全部必填字段", True)
            )
            if self.fix:
                self._apply_defaults_for_empty()
            return len(self.errors) == 0

        # v3 向后兼容：triggers 是字符串数组
        self._check_v3_compat()

        # 逐项校验
        self._check_required_fields()
        self._check_type()
        self._check_triggers()
        self._check_entities()
        self._check_temporal()
        self._check_always_load()
        self._check_priority()
        self._check_updated()
        self._check_summary()
        self._check_cross_links()
        self._check_optional_fields()

        return len(self.errors) == 0

    def _check_v3_compat(self):
        """检测并升级 v3 格式到 v4"""
        triggers = self.frontmatter.get("triggers")
        if isinstance(triggers, list):
            self.warnings.append(
                "检测到 v3 格式 triggers（字符串数组），已自动映射为 v4 格式"
            )
            if self.fix:
                keywords = [t for t in triggers if isinstance(t, str)]
                self.frontmatter["triggers"] = {
                    "descriptive": {
                        "keywords": keywords,
                        "temporal": [],
                        "spatial": [],
                    },
                    "associative": {
                        "queries": [],
                        "pathways": [],
                    },
                }
                self.fixes_applied.append("triggers: v3 数组 → v4 对象结构")
                self._v3_upgraded = True

    def _apply_defaults_for_empty(self):
        """为空的 frontmatter 补全全部默认值"""
        name = os.path.splitext(self.filename)[0]
        today = date.today().isoformat()
        defaults = {
            "name": name,
            "type": "fact",
            "triggers": {
                "descriptive": {"keywords": [], "temporal": [], "spatial": []},
                "associative": {"queries": [], "pathways": []},
            },
            "entities": [],
            "temporal": {
                "valid_from": today,
                "valid_until": None,
                "observed_at": today,
                "event_time": today,
            },
            "always_load": False,
            "priority": "medium",
            "updated": today,
            "summary": self.body[: SUMMARY_MAX_LENGTH - 1] if self.body else "(无内容)",
            "version": 4,
        }
        self.frontmatter = defaults
        self.fixes_applied.append("frontmatter: 补全全部默认值")

    def _check_required_fields(self):
        """校验必填字段是否存在"""
        for field in REQUIRED_FIELDS:
            if field not in self.frontmatter or self.frontmatter[field] is None:
                fixable = field != "name"  # name 无法自动生成有意义的值
                self.errors.append(
                    ValidationError(
                        field,
                        f"缺少必填字段 '{field}'",
                        fixable=fixable,
                    )
                )
                if self.fix and fixable:
                    self._apply_default(field)

    def _apply_default(self, field: str):
        """为缺失字段补全默认值"""
        today = date.today().isoformat()
        defaults: Dict[str, Any] = {
            "type": "fact",
            "triggers": {
                "descriptive": {"keywords": [], "temporal": [], "spatial": []},
                "associative": {"queries": [], "pathways": []},
            },
            "entities": [],
            "temporal": {
                "valid_from": today,
                "valid_until": None,
                "observed_at": today,
                "event_time": today,
            },
            "always_load": False,
            "priority": "medium",
            "updated": today,
            "summary": self.body[: SUMMARY_MAX_LENGTH - 1] if self.body else "(无内容)",
        }
        if field in defaults:
            self.frontmatter[field] = defaults[field]
            self.fixes_applied.append(f"补全默认值: {field} = {defaults[field]!r}")
            # 从 errors 中移除该字段的错误
            self.errors = [e for e in self.errors if e.field != field]

    def _check_type(self):
        """校验 type 字段"""
        val = self.frontmatter.get("type")
        if val is not None and val not in VALID_TYPES:
            self.errors.append(
                ValidationError(
                    "type",
                    f"无效值 '{val}'，必须为: {', '.join(sorted(VALID_TYPES))}",
                )
            )

    def _check_triggers(self):
        """校验 triggers 字段结构"""
        triggers = self.frontmatter.get("triggers")
        if not isinstance(triggers, dict):
            return

        # 描述性触发器
        desc = triggers.get("descriptive")
        if not isinstance(desc, dict):
            self.errors.append(
                ValidationError("triggers.descriptive", "descriptive 必须是对象", True)
            )
            if self.fix:
                triggers["descriptive"] = {"keywords": [], "temporal": [], "spatial": []}
                self.fixes_applied.append("triggers.descriptive: 补全默认对象")
            return

        for sub in ("keywords", "temporal", "spatial"):
            if sub not in desc:
                self.errors.append(
                    ValidationError(
                        f"triggers.descriptive.{sub}",
                        f"缺少 descriptive.{sub}",
                        True,
                    )
                )
                if self.fix:
                    desc[sub] = []
                    self.fixes_applied.append(f"triggers.descriptive.{sub}: 补全空列表")
            elif not isinstance(desc[sub], list):
                self.errors.append(
                    ValidationError(
                        f"triggers.descriptive.{sub}",
                        f"descriptive.{sub} 必须是列表",
                    )
                )

        # 关联性触发器
        assoc = triggers.get("associative")
        if not isinstance(assoc, dict):
            self.errors.append(
                ValidationError("triggers.associative", "associative 必须是对象", True)
            )
            if self.fix:
                triggers["associative"] = {"queries": [], "pathways": []}
                self.fixes_applied.append("triggers.associative: 补全默认对象")
            return

        if "queries" not in assoc:
            self.errors.append(
                ValidationError(
                    "triggers.associative.queries",
                    "缺少 associative.queries",
                    True,
                )
            )
            if self.fix:
                assoc["queries"] = []
                self.fixes_applied.append("triggers.associative.queries: 补全空列表")
        else:
            queries = assoc["queries"]
            if isinstance(queries, list):
                for i, q in enumerate(queries):
                    if isinstance(q, dict):
                        if "query" not in q:
                            self.errors.append(
                                ValidationError(
                                    f"triggers.associative.queries[{i}]",
                                    "缺少 query 字段",
                                )
                            )
                        if "confidence" in q:
                            conf = q["confidence"]
                            if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
                                self.warnings.append(
                                    f"triggers.associative.queries[{i}].confidence 应为 0-1 之间的数值，当前为 {conf}"
                                )

        if "pathways" not in assoc:
            self.errors.append(
                ValidationError(
                    "triggers.associative.pathways",
                    "缺少 associative.pathways",
                    True,
                )
            )
            if self.fix:
                assoc["pathways"] = []
                self.fixes_applied.append("triggers.associative.pathways: 补全空列表")

    def _check_entities(self):
        """校验 entities 列表"""
        entities = self.frontmatter.get("entities")
        if not isinstance(entities, list):
            self.errors.append(
                ValidationError("entities", "entities 必须是列表", True)
            )
            if self.fix:
                self.frontmatter["entities"] = []
                self.fixes_applied.append("entities: 补全空列表")
            return

        for i, entity in enumerate(entities):
            if not isinstance(entity, dict):
                self.errors.append(
                    ValidationError(f"entities[{i}]", "每个 entity 必须是对象")
                )
                continue
            if "name" not in entity:
                self.errors.append(
                    ValidationError(f"entities[{i}].name", "缺少 name 字段")
                )
            if "type" not in entity:
                self.errors.append(
                    ValidationError(f"entities[{i}].type", "缺少 type 字段", True)
                )
                if self.fix:
                    entity["type"] = "other"
                    self.fixes_applied.append(f"entities[{i}].type: 默认值 'other'")
            elif entity["type"] not in VALID_ENTITY_TYPES:
                self.warnings.append(
                    f"entities[{i}].type = '{entity['type']}' 不在推荐枚举中，"
                    f"推荐: {', '.join(sorted(VALID_ENTITY_TYPES))}"
                )

    def _check_temporal(self):
        """校验 temporal 字段"""
        temporal = self.frontmatter.get("temporal")
        if not isinstance(temporal, dict):
            return

        required_temporal = ["valid_from", "valid_until", "observed_at", "event_time"]
        for field in required_temporal:
            if field not in temporal:
                self.errors.append(
                    ValidationError(
                        f"temporal.{field}", f"缺少 temporal.{field}", True
                    )
                )
                if self.fix:
                    if field == "valid_until":
                        temporal[field] = None
                    else:
                        temporal[field] = date.today().isoformat()
                    self.fixes_applied.append(f"temporal.{field}: 补全默认值")

        # 校验日期格式
        for field in ["valid_from", "observed_at", "event_time"]:
            val = temporal.get(field)
            if val is not None and not is_date(val):
                self.errors.append(
                    ValidationError(
                        f"temporal.{field}",
                        f"日期格式无效 '{val}'，应为 YYYY-MM-DD",
                    )
                )

        # valid_until 允许 null
        val = temporal.get("valid_until")
        if val is not None and not is_date(val):
            self.errors.append(
                ValidationError(
                    "temporal.valid_until",
                    f"日期格式无效 '{val}'，应为 YYYY-MM-DD 或 null",
                )
            )

    def _check_always_load(self):
        """校验 always_load 为布尔值"""
        val = self.frontmatter.get("always_load")
        if val is not None and not isinstance(val, bool):
            self.errors.append(
                ValidationError(
                    "always_load",
                    f"应为布尔值 (true/false)，当前为 {type(val).__name__}",
                )
            )

    def _check_priority(self):
        """校验 priority 枚举"""
        val = self.frontmatter.get("priority")
        if val is not None and val not in VALID_PRIORITIES:
            self.errors.append(
                ValidationError(
                    "priority",
                    f"无效值 '{val}'，必须为: {', '.join(sorted(VALID_PRIORITIES))}",
                    True,
                )
            )
            if self.fix:
                self.frontmatter["priority"] = "medium"
                self.fixes_applied.append("priority: 修正为 'medium'")

    def _check_updated(self):
        """校验 updated 日期格式"""
        val = self.frontmatter.get("updated")
        if val is not None and not is_date(val):
            self.errors.append(
                ValidationError(
                    "updated",
                    f"日期格式无效 '{val}'，应为 YYYY-MM-DD",
                    True,
                )
            )
            if self.fix:
                self.frontmatter["updated"] = date.today().isoformat()
                self.fixes_applied.append("updated: 修正为今天日期")

    def _check_summary(self):
        """校验 summary 长度"""
        val = self.frontmatter.get("summary")
        if isinstance(val, str) and len(val) >= SUMMARY_MAX_LENGTH:
            self.errors.append(
                ValidationError(
                    "summary",
                    f"摘要长度 {len(val)} 超出限制（最大 {SUMMARY_MAX_LENGTH} 字符）",
                )
            )

    def _check_cross_links(self):
        """校验 cross_links 关系枚举"""
        cross_links = self.frontmatter.get("cross_links")
        if cross_links is None:
            return
        if not isinstance(cross_links, list):
            self.errors.append(
                ValidationError("cross_links", "cross_links 必须是列表")
            )
            return

        for i, link in enumerate(cross_links):
            if not isinstance(link, dict):
                self.errors.append(
                    ValidationError(f"cross_links[{i}]", "每个 link 必须是对象")
                )
                continue
            if "target" not in link:
                self.errors.append(
                    ValidationError(f"cross_links[{i}].target", "缺少 target 字段")
                )
            if "relation" not in link:
                self.errors.append(
                    ValidationError(
                        f"cross_links[{i}].relation", "缺少 relation 字段"
                    )
                )
            else:
                rel = link["relation"]
                if rel not in VALID_RELATIONS:
                    self.errors.append(
                        ValidationError(
                            f"cross_links[{i}].relation",
                            f"无效关系类型 '{rel}'，必须为: {', '.join(sorted(VALID_RELATIONS))}",
                        )
                    )

    def _check_optional_fields(self):
        """校验可选字段的类型约束"""
        fm = self.frontmatter

        # version
        if "version" in fm and not isinstance(fm["version"], int):
            self.warnings.append(f"version 应为整数，当前为 {type(fm['version']).__name__}")

        # source_url: source 类型必填
        if fm.get("type") == "source":
            if not fm.get("source_url"):
                self.errors.append(
                    ValidationError(
                        "source_url",
                        "source 类型必须提供 source_url",
                        True,
                    )
                )
                if self.fix:
                    fm["source_url"] = ""
                    self.fixes_applied.append("source_url: 补全空字符串（请手动填写）")

        # source_type
        if "source_type" in fm and fm["source_type"] not in VALID_SOURCE_TYPES:
            self.warnings.append(
                f"source_type = '{fm['source_type']}' 不在推荐枚举中，"
                f"推荐: {', '.join(sorted(VALID_SOURCE_TYPES))}"
            )

        # coverage (summary 类型特有)
        if "coverage" in fm:
            if not isinstance(fm["coverage"], list):
                self.errors.append(
                    ValidationError("coverage", "coverage 必须是字符串列表")
                )
            else:
                for i, item in enumerate(fm["coverage"]):
                    if not isinstance(item, str):
                        self.warnings.append(f"coverage[{i}] 应为字符串")

        # access_count
        if "access_count" in fm and not isinstance(fm["access_count"], int):
            self.warnings.append("access_count 应为整数")

        # last_accessed
        if "last_accessed" in fm and not is_date(fm["last_accessed"]):
            self.warnings.append("last_accessed 日期格式无效，应为 YYYY-MM-DD")

        # expires
        if "expires" in fm and not is_date(fm["expires"]):
            self.warnings.append("expires 日期格式无效，应为 YYYY-MM-DD")

    def write_back(self):
        """将修复后的 frontmatter 写回文件"""
        if not self.fix or self.dry_run:
            return

        # 重建 YAML frontmatter + body
        yaml_text = yaml.dump(
            self.frontmatter,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
        )
        content = f"---\n{yaml_text}---\n\n{self.body}\n"

        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            self.errors.append(
                ValidationError("write", f"写回文件失败: {e}")
            )


# ── 主逻辑 ────────────────────────────────────────────────

def scan_memory_files(memory_dir: str) -> List[str]:
    """扫描目录下所有 .md 文件"""
    pattern = os.path.join(memory_dir, "**", "*.md")
    files = glob.glob(pattern, recursive=True)
    # 排除隐藏文件和目录
    files = [f for f in files if not os.path.basename(f).startswith(".")]
    # 排除 index 文件（如 README.md）
    files = [f for f in files if "README" not in os.path.basename(f).upper()]
    return sorted(files)


def main():
    Colors.enable()

    parser = argparse.ArgumentParser(
        description="HIMRA v4.1 记忆文件校验器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python validate_memory.py                          # 校验默认 memory/ 目录
  python validate_memory.py --dir /path/to/memory    # 指定目录
  python validate_memory.py --fix                    # 校验并自动修复
  python validate_memory.py --fix --dry-run          # 预览修复（不实际修改）
        """,
    )
    parser.add_argument(
        "--dir",
        default="memory",
        help="记忆文件目录（默认: memory/）",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="自动修复简单问题（补全缺失字段的默认值）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅报告，不实际修改文件",
    )
    args = parser.parse_args()

    memory_dir = os.path.abspath(args.dir)
    if not os.path.isdir(memory_dir):
        sys.exit(f"错误: 目录不存在 — {memory_dir}")

    print(f"{Colors.BOLD}═══ HIMRA v4.1 记忆文件校验 ═══{Colors.RESET}")
    print(f"目录: {memory_dir}")
    mode_parts = []
    if args.fix:
        mode_parts.append("自动修复")
    if args.dry_run:
        mode_parts.append("预览模式")
    mode_str = " + ".join(mode_parts) if mode_parts else "仅校验"
    print(f"模式: {mode_str}")
    print()

    files = scan_memory_files(memory_dir)

    if not files:
        print(f"{Colors.YELLOW}⚠ 未找到任何 .md 文件{Colors.RESET}")
        return

    print(f"找到 {len(files)} 个文件，开始校验...\n")

    passed = []
    failed = []
    total_errors = 0
    total_warnings = 0
    total_fixes = 0

    for filepath in files:
        relpath = os.path.relpath(filepath, memory_dir)
        validator = MemoryValidator(filepath, fix=args.fix, dry_run=args.dry_run)
        ok = validator.validate()

        if ok:
            passed.append(relpath)
            status = f"{Colors.GREEN}✓ 通过{Colors.RESET}"
        else:
            failed.append(relpath)
            status = f"{Colors.RED}✗ 失败{Colors.RESET}"

        # 输出该文件的结果
        error_count = len(validator.errors)
        warn_count = len(validator.warnings)
        fix_count = len(validator.fixes_applied)

        if error_count == 0 and warn_count == 0 and fix_count == 0:
            # 完全干净
            print(f"  {status} {relpath}")
        else:
            print(f"  {status} {relpath} ({error_count} 错误, {warn_count} 警告" +
                  (f", {fix_count} 修复" if fix_count > 0 else "") + ")")
            for err in validator.errors:
                print(f"    {Colors.RED}{err}{Colors.RESET}")
            for warn in validator.warnings:
                print(f"    {Colors.YELLOW}  ⚠ {warn}{Colors.RESET}")
            for fix in validator.fixes_applied:
                if args.dry_run:
                    print(f"    {Colors.CYAN}  [预览] {fix}{Colors.RESET}")
                else:
                    print(f"    {Colors.CYAN}  ✓ {fix}{Colors.RESET}")

        # 写回修复
        if args.fix and validator.fixes_applied and not args.dry_run:
            validator.write_back()
            if validator.fixes_applied:
                print(f"    {Colors.GREEN}  💾 已写入文件{Colors.RESET}")

        total_errors += error_count
        total_warnings += warn_count
        total_fixes += fix_count
        print()

    # ── 汇总 ──
    print(f"{Colors.BOLD}{'─' * 50}{Colors.RESET}")
    print(f"{Colors.BOLD}校验汇总{Colors.RESET}")
    print(f"  总计文件: {len(files)}")
    print(f"  {Colors.GREEN}通过: {len(passed)}{Colors.RESET}")
    print(f"  {Colors.RED}失败: {len(failed)}{Colors.RESET}")
    print(f"  错误总数: {total_errors}")
    print(f"  警告总数: {total_warnings}")
    if total_fixes > 0:
        if args.dry_run:
            print(f"  {Colors.CYAN}待修复: {total_fixes}（预览模式，未实际修改）{Colors.RESET}")
        else:
            print(f"  {Colors.GREEN}已修复: {total_fixes}{Colors.RESET}")

    if failed:
        print(f"\n{Colors.RED}失败文件清单:{Colors.RESET}")
        for f in failed:
            print(f"  - {f}")

    # 非零退出码
    if not args.fix and total_errors > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
