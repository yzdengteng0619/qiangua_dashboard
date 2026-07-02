def build_daily_report(l1, l2, l3, l4):
    headline = l4.get("weekly_theme") or l1.get("summary") or "今日千瓜洞察"
    key_points = []
    for rec in l4.get("recommendations", [])[:3]:
        title = rec.get("topic_title")
        if title:
            key_points.append(title)
    sections = [
        {
            "title": "趋势聚类",
            "kicker": "Trend Clusters",
            "items": [
                {
                    "title": c.get("cluster_name", ""),
                    "source": "热词与话题",
                    "summary": f"{c.get('trend_direction', '')}。{c.get('relevance_reason', '')}",
                }
                for c in l1.get("clusters", [])
            ],
        },
        {
            "title": "深度机会",
            "kicker": "Opportunities",
            "items": [
                {
                    "title": a.get("cluster_name", ""),
                    "source": "LLM Layer 2",
                    "summary": a.get("trend_analysis", ""),
                }
                for a in l2.get("cluster_analyses", [])
            ],
        },
        {
            "title": "内容趋势",
            "kicker": "Content Patterns",
            "items": [
                {
                    "title": t.get("trend", ""),
                    "source": "爆款笔记",
                    "summary": f"{t.get('evidence', '')} {t.get('intel_action', '')}",
                }
                for t in l3.get("content_trends", [])
            ],
        },
        {
            "title": "选题推荐",
            "kicker": "Recommendations",
            "items": [
                {
                    "title": r.get("topic_title", ""),
                    "source": r.get("content_type", "选题"),
                    "summary": f"{r.get('intel_angle', '')} {r.get('hook_suggestion', '')}",
                }
                for r in l4.get("recommendations", [])
            ],
        },
    ]
    return {"headline": headline, "key_points": key_points, "sections": sections}
