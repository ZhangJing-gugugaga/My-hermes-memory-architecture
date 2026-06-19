# HIMRA v4 Memory Max — 服务器端架构审查报告

**审查人**: yifanfeng97 (Hyper-Extract 作者视角)
**日期**: 2026-06-19
**结论**: 有条件通过

## 致命问题 (P0)

### 1. FAISS 内存估算严重偏低
README 估算 50MB，实际 ~950MB（19倍差距）。
- 50万×384维 float32 原始向量 = 768MB
- IVF 索引结构 = +80MB
- 搜索缓冲区 = +100MB
- **解决方案**: mmap + IVF-PQ 压缩，或只索引 facts/+summaries/

### 2. 五个 JSON 索引无事务保证
写入中途崩溃 → 静默召回失败或索引损坏。
- **解决方案**: 用 SQLite 统一四个 JSON 索引，WAL 模式原子事务

## 严重问题 (P1)

### 3. 关联性触发器 LLM 成本高
10万条记忆 → 42小时 API 调用（串行）。
- **解决方案**: 异步批处理，攒够 10 条一起生成

### 4. 巩固过程 O(n²)
10万条记忆的 cross-link 检测 = 50亿次比较。
- **解决方案**: 分层增量（每日轻量/每周深度/每月归档），用 entity_index 做粗筛选降为 O(n·k²)

## 改进建议

### 来自知识图谱专家
1. **类型化关系** — cross_links 加 depends_on/contradicts/generalizes/exemplifies/temporally_after
2. **实体消歧** — entities 加 type+context（ECS → cloud_server:aliyun）
3. **查询改写** — Stage 0 增加 Query Rewriting 步骤
4. **超边支持** — graph_index 加 hyperedges（多实体联合查询）
5. **时间一等公民** — temporal 升级为 valid_from/valid_until/observed_at/event_time

### 工程优化
1. FAISS 改 mmap + 只索引 facts/summaries/
2. JSON 索引改 SQLite
3. 写入拆分同步+异步
4. 巩固分三层（日/周/月）
5. 磁盘分配：记忆2GB + 索引2GB + 向量1GB + 原始知识50GB(LRU) + 归档10GB + 余量5GB
