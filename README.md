# HIMRA: Hierarchical Indexed Memory Retrieval Architecture for LLM-Based Autonomous Agents

**A Hybrid Rule-Semantic Memory System with Knowledge Graph Integration**

---

## Abstract

Current LLM-based autonomous agents employ flat memory architectures where all persistent knowledge is stored in a single file and injected into every conversation turn. This causes **memory pollution**, **capacity constraints**, and **context inefficiency**.

This paper proposes **HIMRA**, a hybrid memory system combining three retrieval paradigms — **rule-based routing**, **semantic vector search**, and **knowledge graph traversal** — within a hierarchical directory structure. The core insight is to transform the constrained memory file from a storage container into a **multi-stage retrieval router**.

Drawing on RAG and RAG-Anything (HKUDS 2025), we present an architecture that is explainable, resource-efficient (2GB RAM), and incrementally deployable.

**Keywords:** autonomous agents, memory management, RAG, knowledge graph, context engineering

---

## 1. Introduction

### 1.1 Background

LLM-based autonomous agents (Hermes Agent, Claude Code, OpenClaw) require persistent memory across sessions. Current implementations use flat files (limited) or vector databases (resource-intensive). Neither satisfies scalability + explainability + resource efficiency simultaneously.

### 1.2 The Memory Problem

| Approach | Example | Strength | Fatal Weakness |
|----------|---------|----------|----------------|
| Flat file | Hermes MEMORY.md | Simple, deterministic | 2,200-char ceiling |
| Vector DB | Hindsight/Mem0 | Unlimited, semantic | 1-2GB RAM, opaque |
| Knowledge graph | RAG-Anything | Rich relationships | Heavy, designed for documents |

### 1.3 Research Questions

> **RQ1:** Can a hierarchical directory structure with routing rules replace flat-file memory within the existing character budget?
>
> **RQ2:** Can rule-based, semantic, and graph retrieval be combined into a unified pipeline?
>
> **RQ3:** Can this operate within 2GB RAM without external databases?

### 1.4 Architecture Evolution

```
Stage 1: Rule-Based Router (HIMRA v1)
  Solution: Directory structure + keyword triggers
  Limitation: Synonym blindness

         + entity extraction

Stage 2: Entity-Enhanced (HIMRA v2)
  Solution: LLM-extracted entity index
  Limitation: No relationship awareness

         + knowledge graph + semantic search

Stage 3: Graph-Enhanced Hybrid (HIMRA v3)
  Solution: Entity graph + embedding fallback
  Inspired by: RAG-Anything (HKUDS, 2025)
```

---

## 2. Problem Analysis

### 2.1 Flat Memory Anatomy

Every turn, Hermes injects ALL of MEMORY.md (2200 chars) + USER.md (1375 chars) regardless of topic. When discussing servers, memories about Obsidian and coding style waste ~70% of budget.

### 2.2 Failure Modes

- **Type I - Pollution:** Irrelevant memories degrade performance
- **Type II - Starvation:** Character limit forces eviction of valuable knowledge
- **Type III - Collision:** Multiple facts compressed, losing precision
- **Type IV - Staleness:** Outdated info persists

### 2.3 Numbers

| Metric | Value |
|--------|-------|
| Capacity | 2,200 chars |
| Max entries | ~14 facts |
| Saturation time | ~7 days |
| Context waste | ~70% |

---

## 3. Design Principles

### 3.1 Separation of Routing and Storage

The router (MEMORY.md, 2200 chars) = rules + paths. The store (external files) = actual knowledge, unlimited.

### 3.2 Lazy Loading

Only relevant memories loaded. Four-stage pipeline determines relevance.

### 3.3 Bounded Core, Unbounded Periphery

```
Bounded (2200 chars):           Unlimited:
+---------------------+         +---------------------------+
|  MEMORY.md          |         |  memory/                  |
|  (rules + paths)    |-------->|  user/ context/ lessons/  |
+---------------------+         |  .entities/ .embeddings/  |
  "The card catalog"            +---------------------------+
                                  "The library stacks"
```

### 3.4 Explainable Retrieval

Every injection justified: "Loaded because SSH matches trigger in context/server.md"

### 3.5 Graceful Degradation

Works at three levels. Embedding unavailable -> rules only. Entity index corrupted -> keywords only. Never fails completely.

---

## 4. Architecture Overview

Five components:

```
+----------------------------------------------------------+
| Component          | Role                                 |
|--------------------|--------------------------------------|
| 1. Memory Store    | *.md files with YAML frontmatter     |
| 2. Entity Index    | entity -> file mapping (JSON)        |
| 3. Vector Index    | FAISS embeddings (optional)          |
| 4. Graph Index     | entity relationships (JSON)          |
| 5. Retrieval Router| MEMORY.md rules (always loaded)      |
+----------------------------------------------------------+
```

### Component 1: Memory Store

```
memory/
+-- user/profile.md           # Who the user is (always loaded)
+-- context/server.md         # ECS config, SSH, security groups
+-- context/feishu.md         # Feishu integration details
+-- lessons/corrections.md    # User corrections
+-- lessons/discoveries.md    # New tools/methods
+-- index.md                  # Full catalog
```

Each file has frontmatter:

```yaml
name: server-configuration
triggers: [server, ECS, SSH, security-group, swap, aliyun]
entities: [123.57.30.132, ecs.e-c1m1.large, Ubuntu 26.04]
always_load: false
priority: medium
updated: 2026-06-18
```

**Key fields:**
- `triggers` — keywords for rule-based retrieval (Stage 1)
- `entities` — extracted concepts for entity matching (Stage 2, auto-generated)
- `priority` — loading priority when multiple files match
- `always_load` — if true, injected every turn (only user/profile.md)

### Component 2: Entity Index

Maps entities to source files. Auto-generated by LLM when files are created/updated.

```json
{
  "123.57.30.132": ["context/server.md"],
  "Ubuntu 26.04":  ["context/server.md"],
  "feishu":        ["context/feishu.md"],
  "paramiko":      ["lessons/discoveries.md"]
}
```

**Why this matters:** Catches synonyms automatically. "server", "ECS", "server", "aliyun" all map to server.md without manual enumeration. This solves the biggest limitation of pure keyword-based retrieval.

### Component 3: Vector Index (Optional)

FAISS + BGE-small-en-v1.5 (384-dim). Only activates when rules + entities produce < 2 matches. ~150MB RAM.

```
.embeddings/
+-- index.faiss          # Vector index
+-- metadata.json        # vector_id -> (file, chunk, timestamp)
+-- config.json          # model, dimension, chunk params
```

### Component 4: Graph Index

Entity relationships for cross-topic navigation:

```
"ECS Server" --[runs]--> "hermes-gateway"
"hermes-gateway" --[depends_on]--> "lark-oapi"
"lark-oapi" --[installed_on]--> "123.57.30.132"
```

When user asks about "server", graph reveals that "hermes-gateway" and "lark-oapi" are related. System can auto-load context/feishu.md as supplementary context.

Stored as simple JSON (~10MB RAM). No Neo4j needed.

### Component 5: Retrieval Router (MEMORY.md)

The 2200-char rule file that orchestrates the four-stage pipeline. Always loaded into LLM context.

---

## 5. Four-Stage Retrieval Pipeline

```
User Query: "my server swap config?"
                |
    +-----------+-----------+
    | Stage 1: Rule Match   | "server" + "swap" -> server.md
    | Stage 2: Entity Match | [server, swap] -> server.md (dup)
    | Stage 3: Semantic     | Skip (>=2 matches)
    | Stage 4: Graph        | server -> hermes-gateway (no new files)
    +-----------+-----------+
                |
                v
    Injected: user/profile.md + context/server.md
```

| Stage | Method | Cost | Handles |
|-------|--------|------|---------|
| 1. Rules | Keyword matching | Free | Common vocabulary |
| 2. Entities | Index lookup | Free | Synonyms, technical terms |
| 3. Semantic | Embedding similarity | ~50ms | Novel phrasings |
| 4. Graph | Relationship traversal | ~10ms | Cross-topic links |

### Scoring

Score(f) = alpha * [rule match] + beta * [entity match] + gamma * sim(q,f) + delta * graph(f)

Where alpha > beta > gamma > delta (deterministic weighted higher).

### Fallback

If nothing matches -> load index.md (catalog) -> LLM browses and requests files.

---

## 6. Memory Lifecycle

### Update Triggers

| Event | Target | Action |
|-------|--------|--------|
| User says "remember" | Domain file | Write |
| Correction | lessons/corrections.md | Append |
| Config change | context/*.md | Overwrite |
| Task failure | lessons/failures.md | Append |

### Entity Maintenance

On file update: re-extract entities -> update index -> update graph -> re-embed (if vector index active).

### Aging

- 0-30 days: Active (full retrieval)
- 30-90 days: Stale (exact match only)
- 90+ days: Archive (excluded)

### Self-Healing

Agent detects memory gaps and writes corrective entries with root cause analysis.

---

## 7. MEMORY.md Specification

### Budget Allocation (2200 chars)

| Section | Budget | Content |
|---------|--------|---------|
| Retrieval rules | ~1200 (55%) | Keywords, entity triggers |
| Update rules | ~300 (14%) | Write triggers and format |
| Lifecycle rules | ~200 (9%) | Aging, archival |
| Pipeline config | ~200 (9%) | Stage weights, thresholds |
| Path index | ~200 (9%) | Directory structure |
| Metadata | ~100 (4%) | Version, audit date |

### Reference Template

```
# Memory Router v3.0

## Paths
user/ = user profile | context/ = project context | lessons/ = accumulated knowledge
index.md = full catalog | .entities/ = entity index | .embeddings/ = vector index

## Stage 1: Rules
Always load: user/profile.md
Keyword triggers:
- server|ECS|SSH|swap|systemd -> context/server.md
- feishu|lark|bot|gateway -> context/feishu.md
- Hermes|config|skill|toolset -> context/hermes-local.md
- wiki|Obsidian|notes -> context/obsidian.md
- correct|wrong|fix -> lessons/corrections.md
- discover|new tool -> lessons/discoveries.md

## Stage 2: Entities
Auto-retrieved from .entity_index.json

## Stage 3: Semantic
Trigger: Stage 1+2 matches < 2 files
Model: BGE-small-en-v1.5 | Threshold: > 0.6

## Stage 4: Graph
Trigger: >= 1 file matched
Depth: 1 (direct neighbors only)

## Update
Trigger: "remember" / correction / config change / task failure
Write: target file -> update entity index -> update vector index

## Lifecycle
>90d unmatched -> archive/ | monthly cleanup | MEMORY.md <=2200 chars
```

---

## 8. Comparison

| Dimension | Flat File | Vector DB | RAG-Anything | **HIMRA** |
|-----------|-----------|-----------|--------------|-----------|
| Capacity | 2200 chars | Unlimited | Unlimited | **Unlimited** |
| Retrieval | Full inject | Semantic | Graph+Semantic | **Rules+Entity+Semantic+Graph** |
| Explainability | High | Low | Medium | **High** |
| Resources | ~0 | 1-2GB | 2-4GB | **~150MB** |
| Setup | None | High | Very high | **Low** |
| Degradation | N/A | Fails | Fails | **Graceful** |

### Relationship to RAG

HIMRA is a specialized RAG for agent memory:

1. **Structured source material:** Agent memories have predictable structure (prefs, configs, lessons). HIMRA exploits this through typed directories and frontmatter metadata.

2. **Hybrid retrieval:** Standard RAG uses one method (embedding similarity). HIMRA combines four methods in a priority cascade, using expensive methods only when cheap ones fail.

3. **Write-aware:** RAG is read-only. HIMRA has a full write path — the agent actively maintains its own memory.

### RAG-Anything Contributions

1. **Entity extraction as indexing:** RAG-Anything extracts entities into a knowledge graph. HIMRA applies this to memory files — building an entity index that improves retrieval beyond keywords.

2. **Context-aware loading:** RAG-Anything provides surrounding text when analyzing images. HIMRA applies this — loading related files in the same directory.

3. **Hierarchical relationships:** RAG-Anything's `belongs_to` edges. HIMRA's graph edges (runs, depends_on, configured_by) provide the same navigation.

---

## 9. Implementation Strategy

| Phase | Effort | What | Resources |
|-------|--------|------|-----------|
| 1. Rules | 1-2h | Directory + triggers | 0 |
| 2. Entities | 2-4h | Entity extraction + index | 0 |
| 3. Semantic | 4-8h | FAISS + BGE-small | 150MB RAM |
| 4. Graph | 4-8h | Entity graph + traversal | 10MB RAM |

---

## 10. Evaluation

| # | Condition | Active Stages |
|---|-----------|---------------|
| 1 | Baseline | Flat MEMORY.md |
| 2 | HIMRA v1 | Rules (1) |
| 3 | HIMRA v2 | Rules + Entities (1-2) |
| 4 | HIMRA v2.5 | + Semantic (1-3) |
| 5 | HIMRA v3 | All four (1-4) |

Metrics: Precision@K > 85%, Recall@K > 80%, Pollution < 15%, Latency < 100ms

---

## 11. Limitations

1. Entity extraction quality depends on LLM
2. Graph needs periodic refresh
3. Fixed priority weights (could be adaptive)
4. No cross-memory inference

## 12. Future Work

1. Adaptive stage weights based on query type
2. LLM-in-the-loop intent classification
3. Automatic trigger expansion from missed queries
4. Multi-agent memory sharing with access control
5. LLM-based memory compression and summarization

---

## 13. Conclusion

HIMRA combines rule matching, entity indexing, semantic search, and graph traversal in a priority cascade. Rules catch common cases (free, explainable), entities catch synonyms (free, automatic), semantic search catches novel phrasings (cheap), graph traversal catches cross-topic links (cheap).

The architecture is incrementally deployable: Stage 1-2 need zero infrastructure, Stage 3-4 add ~150MB RAM. Suitable for 2GB servers where vector databases are infeasible.

Key insight: **agent memory has predictable structure** that can be exploited through typed directories, entity extraction, and relationship graphs. A 2200-character router can govern an effectively unlimited knowledge base.

---

## References

1. Nous Research. (2026). Hermes Agent. https://github.com/NousResearch/hermes-agent
2. Zhang, J. (2026). Hindsight Memory Guide. https://github.com/haitao338241-collab/hermes-hindsight-guide
3. Li, Z., et al. (2025). RAG-Anything: All-in-One Multimodal RAG. HKUDS. arXiv:2510.12323
4. Guo, Z., et al. (2024). LightRAG. HKUDS. arXiv:2410.05779
5. Packer, C., et al. (2023). MemGPT. arXiv:2310.08560
6. Lewis, P., et al. (2020). RAG. NeurIPS 2020
7. Gao, Y., et al. (2024). RAG Survey. arXiv:2312.10997
8. Xiao, S., et al. (2024). BGE. arXiv:2308.03281
9. Zhong, W., et al. (2024). MemoryBank. AAAI 2024
10. Anthropic. (2026). Skills Specification. https://github.com/anthropics/skills

---

*Architecture design by Zhang Jing, 2026.*
