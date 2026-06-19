#!/usr/bin/env python3
"""
init_indices.py — HIMRA v4.1 索引初始化器
===========================================

从 memory/ 下的记忆文件初始化 SQLite 索引数据库和 FAISS 向量索引。

用法:
    python init_indices.py [--memory-dir memory/] [--embedding-model BAAI/bge-small-en-v1.5]
    python init_indices.py --rebuild --dry-run

功能:
    1. 扫描所有记忆文件，解析 YAML frontmatter
    2. 创建/重建 SQLite 数据库（6 张表），WAL 模式
    3. 填充触发器索引、实体索引、关系图索引、超边索引、摘要索引
    4. 为关联性触发器生成 BGE-small 384 维 embedding
    5. 构建 FAISS IndexIVFPQ 向量索引（mmap 模式）
    6. 输出索引统计信息

SQLite 表结构 (参见 SPEC.md §索引层规范):
    - trigger_index:     触发器索引（关键词+关联性）
    - entity_index:      实体索引
    - graph_index:       关系图索引（cross_links）
    - hyperedge_index:   超边索引（多实体联合查询）
    - summary_index:     摘要索引（主题→记忆映射）
    - access_log:        访问日志

依赖:
    pip install pyyaml sentence-transformers faiss-cpu

兼容:
    HIMRA v4.1 (v4-memory-max)
"""

import argparse
import glob
import json
import os
import re
import sqlite3
import sys
import time
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    sys.exit("错误: 需要安装 pyyaml。请运行: pip install pyyaml")

try:
    import numpy as np
except ImportError:
    sys.exit("错误: 需要安装 numpy。请运行: pip install numpy")

try:
    import faiss
except ImportError:
    sys.exit("错误: 需要安装 faiss-cpu。请运行: pip install faiss-cpu")

# ── 常量 ──────────────────────────────────────────────────

DIMENSION = 384  # BGE-small 输出维度
PQ_M = 64  # PQ 子向量数
N_CENTROIDS_RATIO = 0.05  # IVF 聚类中心比例（相对于向量数）
INDEX_FILENAME = "index.faiss"
METADATA_FILENAME = "index_meta.json"

SQL_SCHEMA = """
-- 触发器索引
CREATE TABLE IF NOT EXISTS trigger_index (
    memory_name TEXT NOT NULL,
    trigger_text TEXT NOT NULL,
    trigger_type TEXT NOT NULL,    -- 'descriptive' | 'associative'
    trigger_embedding BLOB,        -- 384维 float32 → 1536 bytes
    confidence REAL DEFAULT 1.0,
    PRIMARY KEY (memory_name, trigger_text, trigger_type)
);

-- 实体索引
CREATE TABLE IF NOT EXISTS entity_index (
    entity_name TEXT NOT NULL,
    entity_type TEXT,
    entity_context TEXT,
    memory_name TEXT NOT NULL,
    frequency INTEGER DEFAULT 1,
    PRIMARY KEY (entity_name, memory_name)
);

-- 关系图索引
CREATE TABLE IF NOT EXISTS graph_index (
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    PRIMARY KEY (source, target, relation_type)
);

-- 超边索引（多实体联合查询）
CREATE TABLE IF NOT EXISTS hyperedge_index (
    hyperedge_id TEXT PRIMARY KEY,
    nodes TEXT NOT NULL,           -- JSON array of memory names
    edge_type TEXT NOT NULL,       -- 'co_occurrence' | 'semantic_cluster'
    weight REAL DEFAULT 1.0
);

-- 摘要索引
CREATE TABLE IF NOT EXISTS summary_index (
    topic TEXT NOT NULL,
    memory_name TEXT NOT NULL,
    coverage_area TEXT,
    PRIMARY KEY (topic, memory_name)
);

-- 访问统计
CREATE TABLE IF NOT EXISTS access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_name TEXT NOT NULL,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    query_text TEXT,
    stage_matched INTEGER         -- 哪个阶段命中的
);
"""

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


def scan_memory_files(memory_dir: str) -> List[str]:
    """扫描目录下所有 .md 文件（排除隐藏文件和 README）"""
    pattern = os.path.join(memory_dir, "**", "*.md")
    files = glob.glob(pattern, recursive=True)
    files = [f for f in files if not os.path.basename(f).startswith(".")]
    files = [f for f in files if "README" not in os.path.basename(f).upper()]
    return sorted(files)


def human_size(bytes_val: int) -> str:
    """可读文件大小"""
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} TB"


def load_embedding_model(model_name: str):
    """
    加载嵌入模型。优先使用 sentence-transformers，
    回退到手动 HuggingFace 加载。
    """
    print(f"加载嵌入模型: {model_name} ...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_name)
        print(f"  {Colors.GREEN}✓ 模型加载成功（sentence-transformers）{Colors.RESET}")
        return model
    except ImportError:
        print(f"  {Colors.YELLOW}⚠ sentence-transformers 未安装，尝试手动加载{Colors.RESET}")
    except Exception as e:
        print(f"  {Colors.YELLOW}⚠ sentence-transformers 加载失败: {e}{Colors.RESET}")
        print(f"  {Colors.YELLOW}尝试从 transformers 手动加载...{Colors.RESET}")

    # 回退方案：用 transformers + 平均池化
    try:
        from transformers import AutoTokenizer, AutoModel
        import torch

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)

        class ManualEmbedder:
            def __init__(self, tokenizer, model):
                self.tokenizer = tokenizer
                self.model = model
                self.model.eval()

            def encode(self, texts, batch_size=32, **kwargs):
                """编码文本列表，返回 numpy 数组"""
                self.model.eval()
                all_embeddings = []
                with torch.no_grad():
                    for i in range(0, len(texts), batch_size):
                        batch = texts[i: i + batch_size]
                        inputs = self.tokenizer(
                            batch,
                            padding=True,
                            truncation=True,
                            max_length=512,
                            return_tensors="pt",
                        )
                        outputs = self.model(**inputs)
                        # 平均池化 (last_hidden_state)
                        attention_mask = inputs["attention_mask"]
                        hidden = outputs.last_hidden_state
                        mask_expanded = attention_mask.unsqueeze(-1).expand(hidden.size()).float()
                        sum_embeddings = torch.sum(hidden * mask_expanded, dim=1)
                        sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
                        embeddings = sum_embeddings / sum_mask
                        all_embeddings.append(embeddings.cpu().numpy())
                return np.vstack(all_embeddings).astype(np.float32)

        embedder = ManualEmbedder(tokenizer, model)
        print(f"  {Colors.GREEN}✓ 模型加载成功（transformers 手动模式）{Colors.RESET}")
        return embedder
    except ImportError:
        sys.exit(
            "错误: 需要安装 sentence-transformers 或 transformers。\n"
            "请运行: pip install sentence-transformers\n"
            "或: pip install transformers torch"
        )


# ── 索引构建器 ────────────────────────────────────────────

class IndexBuilder:
    """HIMRA 索引构建器"""

    def __init__(
        self,
        memory_dir: str,
        db_path: str,
        embedding_model_name: str,
        faiss_dir: str,
        rebuild: bool = False,
        dry_run: bool = False,
    ):
        self.memory_dir = os.path.abspath(memory_dir)
        self.db_path = db_path
        self.embedding_model_name = embedding_model_name
        self.faiss_dir = faiss_dir
        self.rebuild = rebuild
        self.dry_run = dry_run

        self.files: List[str] = []
        self.memories: List[Dict[str, Any]] = []  # 成功解析的 frontmatter
        self.parse_errors: List[Tuple[str, str]] = []  # (文件名, 错误信息)
        self.stats: Dict[str, Any] = {}

        # 延迟加载
        self._embedder = None
        self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("数据库未初始化，请先调用 init_db()")
        return self._conn

    @property
    def embedder(self):
        if self._embedder is None:
            self._embedder = load_embedding_model(self.embedding_model_name)
        return self._embedder

    def run(self):
        """执行完整索引构建流程"""
        print(f"{Colors.BOLD}═══ HIMRA v4.1 索引初始化 ═══{Colors.RESET}")
        print(f"记忆目录: {self.memory_dir}")
        print(f"数据库:   {self.db_path}")
        print(f"向量目录: {self.faiss_dir}")
        print(f"嵌入模型: {self.embedding_model_name}")
        mode = "预览模式" if self.dry_run else ("重建模式" if self.rebuild else "增量模式")
        print(f"模式:     {mode}")
        print()

        # 步骤 1: 扫描文件
        self._step_scan()
        if not self.files:
            print(f"{Colors.YELLOW}⚠ 未找到任何 .md 文件，退出{Colors.RESET}")
            return

        # 步骤 2: 解析 frontmatter
        self._step_parse()

        if not self.memories:
            print(f"{Colors.RED}✗ 没有成功解析的记忆文件，退出{Colors.RESET}")
            return

        # 步骤 3: 初始化数据库
        if not self.dry_run:
            self._step_init_db()

        # 步骤 4: 填充索引表
        if not self.dry_run:
            self._step_populate_tables()

        # 步骤 5: 生成向量并构建 FAISS 索引
        if not self.dry_run:
            self._step_build_faiss()

        # 步骤 6: 输出统计
        self._step_report()

    def _step_scan(self):
        """步骤 1: 扫描文件"""
        print(f"{Colors.BOLD}[1/6] 扫描记忆文件...{Colors.RESET}")
        self.files = scan_memory_files(self.memory_dir)
        print(f"  找到 {len(self.files)} 个 .md 文件")
        for f in self.files:
            print(f"    - {os.path.relpath(f, self.memory_dir)}")
        print()

    def _step_parse(self):
        """步骤 2: 解析 YAML frontmatter"""
        print(f"{Colors.BOLD}[2/6] 解析 YAML frontmatter...{Colors.RESET}")
        for filepath in self.files:
            relpath = os.path.relpath(filepath, self.memory_dir)
            fm, body, err = parse_frontmatter(filepath)
            if err:
                self.parse_errors.append((relpath, err))
                print(f"  {Colors.RED}✗ {relpath}: {err}{Colors.RESET}")
                continue
            if fm is None:
                self.parse_errors.append((relpath, "frontmatter 为空"))
                print(f"  {Colors.RED}✗ {relpath}: frontmatter 为空{Colors.RESET}")
                continue

            # 确保 name 字段存在
            if "name" not in fm:
                fm["name"] = os.path.splitext(os.path.basename(filepath))[0]

            self.memories.append({
                "filepath": filepath,
                "relpath": relpath,
                "frontmatter": fm,
                "body": body or "",
            })
            mem_type = fm.get("type", "?")
            print(f"  {Colors.GREEN}✓{Colors.RESET} {relpath} (type={mem_type})")

        print(f"  成功: {len(self.memories)} / 总计: {len(self.files)}")
        if self.parse_errors:
            print(f"  {Colors.RED}失败: {len(self.parse_errors)}{Colors.RESET}")
        print()

    def _step_init_db(self):
        """步骤 3: 初始化 SQLite 数据库"""
        print(f"{Colors.BOLD}[3/6] 初始化 SQLite 数据库...{Colors.RESET}")

        # 重建模式：删除旧数据库
        if self.rebuild and os.path.exists(self.db_path):
            os.remove(self.db_path)
            print(f"  已删除旧数据库: {self.db_path}")

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self._conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA cache_size=-8000;")  # 8MB cache

        self.conn.executescript(SQL_SCHEMA)
        self.conn.commit()
        print(f"  {Colors.GREEN}✓ 数据库已初始化 (WAL 模式){Colors.RESET}")
        print()

    def _step_populate_tables(self):
        """步骤 4: 填充索引表"""
        print(f"{Colors.BOLD}[4/6] 填充索引表...{Colors.RESET}")

        cursor = self.conn.cursor()

        # 清空已有数据
        tables = [
            "trigger_index",
            "entity_index",
            "graph_index",
            "hyperedge_index",
            "summary_index",
        ]
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")

        # 实体共同出现计数（用于超边构建）
        entity_memory_map: Dict[str, List[str]] = {}
        # 主题记忆映射
        topic_memories: Dict[str, List[Tuple[str, Optional[str]]]] = {}

        for mem in self.memories:
            fm = mem["frontmatter"]
            memory_name = fm.get("name", mem["relpath"])
            mem_type = fm.get("type", "fact")

            # ── trigger_index ──
            triggers = fm.get("triggers", {})
            if isinstance(triggers, dict):
                # 描述性触发器
                desc = triggers.get("descriptive", {})
                if isinstance(desc, dict):
                    for keyword in desc.get("keywords", []):
                        if isinstance(keyword, str):
                            cursor.execute(
                                "INSERT OR REPLACE INTO trigger_index VALUES (?, ?, 'descriptive', NULL, 1.0)",
                                (memory_name, keyword),
                            )
                    for temporal in desc.get("temporal", []):
                        if isinstance(temporal, str):
                            cursor.execute(
                                "INSERT OR REPLACE INTO trigger_index VALUES (?, ?, 'descriptive', NULL, 1.0)",
                                (memory_name, f"t:{temporal}"),
                            )
                    for spatial in desc.get("spatial", []):
                        if isinstance(spatial, str):
                            cursor.execute(
                                "INSERT OR REPLACE INTO trigger_index VALUES (?, ?, 'descriptive', NULL, 1.0)",
                                (memory_name, f"s:{spatial}"),
                            )

                # 关联性触发器
                assoc = triggers.get("associative", {})
                if isinstance(assoc, dict):
                    for q in assoc.get("queries", []):
                        if isinstance(q, dict):
                            query_text = q.get("query", "")
                            confidence = q.get("confidence", 0.5)
                            cursor.execute(
                                "INSERT OR REPLACE INTO trigger_index VALUES (?, ?, 'associative', NULL, ?)",
                                (memory_name, query_text, confidence),
                            )

            # ── entity_index ──
            entities = fm.get("entities", [])
            if isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, dict):
                        ename = entity.get("name", "")
                        etype = entity.get("type")
                        ectx = entity.get("context")
                        cursor.execute(
                            "INSERT OR REPLACE INTO entity_index VALUES (?, ?, ?, ?, 1)",
                            (ename, etype, ectx, memory_name),
                        )
                        # 收集实体→记忆映射（用于超边）
                        entity_memory_map.setdefault(ename, []).append(memory_name)

            # ── graph_index ──
            cross_links = fm.get("cross_links", [])
            if isinstance(cross_links, list):
                for link in cross_links:
                    if isinstance(link, dict):
                        target = link.get("target", "")
                        relation = link.get("relation", "")
                        if target and relation:
                            cursor.execute(
                                "INSERT OR REPLACE INTO graph_index VALUES (?, ?, ?, 1.0)",
                                (memory_name, target, relation),
                            )

            # ── summary_index ──
            if mem_type == "summary":
                topic = memory_name
                coverage = fm.get("coverage", [])
                if isinstance(coverage, list):
                    for area in coverage:
                        if isinstance(area, str):
                            cursor.execute(
                                "INSERT OR REPLACE INTO summary_index VALUES (?, ?, ?)",
                                (topic, memory_name, area),
                            )
                # 如果 coverage 为空，插入自身
                if not coverage or not isinstance(coverage, list) or len(coverage) == 0:
                    cursor.execute(
                        "INSERT OR REPLACE INTO summary_index VALUES (?, ?, NULL)",
                        (topic, memory_name),
                    )

        # ── hyperedge_index (co_occurrence 类型) ──
        for entity_name, mem_list in entity_memory_map.items():
            if len(mem_list) >= 2:
                # 为共享 2+ 记忆的实体创建超边
                hyperedge_id = f"cooc_{entity_name}"
                nodes_json = json.dumps(sorted(mem_list), ensure_ascii=False)
                cursor.execute(
                    "INSERT OR REPLACE INTO hyperedge_index VALUES (?, ?, 'co_occurrence', ?)",
                    (hyperedge_id, nodes_json, len(mem_list)),
                )

        self.conn.commit()

        # 统计各表行数
        for table in tables:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            self.stats[table] = count
            print(f"  {table}: {count} 行")

        print()

    def _step_build_faiss(self):
        """步骤 5: 生成 embedding 并构建 FAISS 向量索引"""
        print(f"{Colors.BOLD}[5/6] 构建 FAISS 向量索引...{Colors.RESET}")

        # 收集需要编码的关联性触发器（仅 facts/ 和 summaries/）
        texts_to_encode: List[Tuple[str, str, str, float]] = []
        # (memory_name, trigger_text, trigger_type, confidence)

        for mem in self.memories:
            fm = mem["frontmatter"]
            mem_type = fm.get("type", "")
            if mem_type not in ("fact", "summary"):
                continue  # 仅向量化 facts 和 summaries

            memory_name = fm.get("name", mem["relpath"])
            triggers = fm.get("triggers", {})

            if isinstance(triggers, dict):
                assoc = triggers.get("associative", {})
                if isinstance(assoc, dict):
                    for q in assoc.get("queries", []):
                        if isinstance(q, dict) and q.get("query"):
                            texts_to_encode.append((
                                memory_name,
                                q["query"],
                                "associative",
                                float(q.get("confidence", 0.5)),
                            ))

        if not texts_to_encode:
            print(f"  {Colors.YELLOW}⚠ 没有需要向量化的关联性触发器，跳过 FAISS 构建{Colors.RESET}")
            self.stats["faiss_vectors"] = 0
            return

        print(f"  待编码文本: {len(texts_to_encode)} 条")
        texts = [t[1] for t in texts_to_encode]

        # 生成 embedding
        t0 = time.time()
        print(f"  正在生成 embedding ({DIMENSION} 维)...")
        embeddings = self.embedder.encode(texts, show_progress_bar=True)
        elapsed = time.time() - t0
        print(f"  {Colors.GREEN}✓ embedding 生成完成 ({elapsed:.1f}s){Colors.RESET}")

        # 确保 embeddings 是 float32 numpy 数组
        embeddings = np.asarray(embeddings, dtype=np.float32)
        n_vectors, dim = embeddings.shape
        print(f"  向量矩阵: {n_vectors} × {dim}")

        # ── 构建 IndexIVFPQ ──
        # 训练参数
        nlist = max(4, int(n_vectors * N_CENTROIDS_RATIO))  # IVF 聚类中心数
        nlist = min(nlist, n_vectors)  # 聚类中心不超过向量数

        # PQ 参数
        m = min(PQ_M, dim)  # 子向量数
        # 确保 dim % m == 0
        while dim % m != 0 and m > 1:
            m -= 1
        bits_per_idx = 8  # 每个子向量 8 bits

        print(f"  FAISS 参数: nlist={nlist}, M={m}, dim={dim}")

        # 量化器
        quantizer = faiss.IndexFlatL2(dim)

        # IndexIVFPQ
        index = faiss.IndexIVFPQ(quantizer, dim, nlist, m, bits_per_idx)

        # 训练 (IVF 需要训练)
        if n_vectors < nlist:
            print(f"  {Colors.YELLOW}⚠ 向量数 ({n_vectors}) 少于聚类数 ({nlist})，降级为 IndexFlatL2{Colors.RESET}")
            index = faiss.IndexFlatL2(dim)
            index.add(embeddings)
        else:
            print(f"  正在训练 IVF 量化器...")
            index.train(embeddings)
            index.add(embeddings)

        # 保存到磁盘（mmap 兼容的写法）
        os.makedirs(self.faiss_dir, exist_ok=True)
        faiss_path = os.path.join(self.faiss_dir, INDEX_FILENAME)

        # 使用 faiss.write_index 保存（支持 mmap 加载）
        faiss.write_index(index, faiss_path)
        print(f"  {Colors.GREEN}✓ FAISS 索引已保存: {faiss_path}{Colors.RESET}")

        # 保存元数据
        meta = {
            "model": self.embedding_model_name,
            "dimension": dim,
            "n_vectors": n_vectors,
            "index_type": "IndexIVFPQ" if n_vectors >= nlist else "IndexFlatL2",
            "nlist": nlist if n_vectors >= nlist else None,
            "M": m if n_vectors >= nlist else None,
            "created": date.today().isoformat(),
            "index_file": INDEX_FILENAME,
        }
        meta_path = os.path.join(self.faiss_dir, METADATA_FILENAME)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        print(f"  {Colors.GREEN}✓ 元数据已保存: {meta_path}{Colors.RESET}")

        # 将 embedding_id 写回 trigger_index
        cursor = self.conn.cursor()
        for i, (mem_name, trigger_text, trigger_type, confidence) in enumerate(texts_to_encode):
            emb_bytes = embeddings[i].tobytes()
            cursor.execute(
                "UPDATE trigger_index SET trigger_embedding = ? "
                "WHERE memory_name = ? AND trigger_text = ? AND trigger_type = ?",
                (emb_bytes, mem_name, trigger_text, trigger_type),
            )
        self.conn.commit()

        # 统计
        self.stats["faiss_vectors"] = n_vectors
        faiss_size = os.path.getsize(faiss_path)
        self.stats["faiss_size"] = faiss_size
        print(f"  向量数: {n_vectors}")
        print(f"  索引文件大小: {human_size(faiss_size)}")
        print()

    def _step_report(self):
        """步骤 6: 输出汇总报告"""
        print(f"{Colors.BOLD}[6/6] 索引统计汇总{Colors.RESET}")
        print(f"{'─' * 45}")

        if self.dry_run:
            print(f"  {Colors.CYAN}[预览模式] 未实际修改文件{Colors.RESET}")
            print(f"  记忆文件: {len(self.files)}")
            print(f"  可解析:   {len(self.memories)}")
            print(f"  解析失败: {len(self.parse_errors)}")
        else:
            print(f"  记忆文件:       {len(self.files)}")
            print(f"  成功解析:       {len(self.memories)}")
            if self.parse_errors:
                print(f"  {Colors.YELLOW}解析失败:       {len(self.parse_errors)}{Colors.RESET}")

            # SQLite 表统计
            table_names = {
                "trigger_index": "触发器索引",
                "entity_index": "实体索引",
                "graph_index": "关系图索引",
                "hyperedge_index": "超边索引",
                "summary_index": "摘要索引",
            }
            for table, label in table_names.items():
                count = self.stats.get(table, 0)
                print(f"  {label}:{' ' * (13 - len(label))}{count} 行")

            # FAISS 统计
            faiss_count = self.stats.get("faiss_vectors", 0)
            faiss_size = self.stats.get("faiss_size", 0)
            print(f"  FAISS 向量:     {faiss_count}")
            print(f"  FAISS 文件大小: {human_size(faiss_size)}")

            # 数据库文件大小
            if os.path.exists(self.db_path):
                db_size = os.path.getsize(self.db_path)
                print(f"  SQLite 文件大小: {human_size(db_size)}")

        if self.parse_errors:
            print(f"\n  {Colors.RED}解析失败文件:{Colors.RESET}")
            for fname, err in self.parse_errors:
                print(f"    - {fname}: {err}")

        print()
        print(f"{Colors.GREEN}{Colors.BOLD}✓ 索引初始化完成{Colors.RESET}")


# ── 主逻辑 ────────────────────────────────────────────────

def main():
    Colors.enable()

    parser = argparse.ArgumentParser(
        description="HIMRA v4.1 索引初始化器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python init_indices.py                                      # 默认配置
  python init_indices.py --rebuild                            # 重建所有索引
  python init_indices.py --memory-dir /path/to/memory         # 指定目录
  python init_indices.py --embedding-model BAAI/bge-small-zh-v1.5  # 中文模型
  python init_indices.py --dry-run                            # 预览模式
        """,
    )
    parser.add_argument(
        "--memory-dir",
        default="memory",
        help="记忆文件目录（默认: memory/）",
    )
    parser.add_argument(
        "--embedding-model",
        default="BAAI/bge-small-en-v1.5",
        help="嵌入模型名称或路径（默认: BAAI/bge-small-en-v1.5）",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="SQLite 数据库路径（默认: <memory-dir>/.indices.db）",
    )
    parser.add_argument(
        "--faiss-dir",
        default=None,
        help="FAISS 索引目录（默认: <memory-dir>/.embeddings）",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="重建所有索引（删除现有数据库和向量索引）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅扫描和预览，不实际修改文件",
    )
    args = parser.parse_args()

    memory_dir = os.path.abspath(args.memory_dir)
    if not os.path.isdir(memory_dir):
        sys.exit(f"错误: 目录不存在 — {memory_dir}")

    db_path = args.db_path or os.path.join(memory_dir, ".indices.db")
    faiss_dir = args.faiss_dir or os.path.join(memory_dir, ".embeddings")

    builder = IndexBuilder(
        memory_dir=memory_dir,
        db_path=db_path,
        embedding_model_name=args.embedding_model,
        faiss_dir=faiss_dir,
        rebuild=args.rebuild,
        dry_run=args.dry_run,
    )
    builder.run()


if __name__ == "__main__":
    main()
