---
name: [unique-name]
type: fact
triggers:
  descriptive:
    entities: []
    temporal: []
    spatial: []
  associative:
    queries:
      - query: "[用户未来可能问的问题 1]"
        confidence: 0.85
      - query: "[用户未来可能问的问题 2]"
        confidence: 0.72
    pathways:
      - "[主题A] → [主题B] → [主题C]"
always_load: false
priority: medium
updated: YYYY-MM-DD
summary: [一句话描述，<100字符]
version: 4
cross_links: []
---

[事实内容，简洁精确，<500字符]
