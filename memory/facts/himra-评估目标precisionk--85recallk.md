---
name: himra-评估目标precisionk--85recallk
type: fact
triggers:
  descriptive:
    keywords: ["HIMRA"]
    temporal: ['2026-06']
    spatial: []
  associative:
    queries:
      - query: "HIMRA 评估目标：Precision@K > 85%、Recall@K > 80%、污染率 < 15%、延迟 < 1"
        confidence: 0.6
    pathways: []
entities:
  - name: HIMRA
    type: concept
    context: 
temporal:
  valid_from: 2026-06-18
  valid_until: null
  observed_at: 2026-06-18
  event_time: 2026-06-18
always_load: false
priority: medium
updated: 2026-06-18
summary: "HIMRA 评估目标：Precision@K > 85%、Recall@K > 80%、污染率 < 15%、延迟 < 100ms。"
version: 4
cross_links: []
---

HIMRA 评估目标：Precision@K > 85%、Recall@K > 80%、污染率 < 15%、延迟 < 100ms。
