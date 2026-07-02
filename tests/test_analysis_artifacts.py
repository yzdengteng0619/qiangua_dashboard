import analysis_artifacts


def test_build_daily_report_from_layers():
    l1 = {"clusters": [{"cluster_name": "AI PC", "trend_direction": "上升"}]}
    l2 = {"cluster_analyses": [{"cluster_name": "AI PC", "trend_analysis": "讨论升温"}]}
    l3 = {
        "content_trends": [
            {"trend": "教程型内容增长", "evidence": "互动高", "intel_action": "做教程"}
        ]
    }
    l4 = {
        "weekly_theme": "AI PC 内容机会",
        "recommendations": [
            {
                "topic_title": "AI PC 怎么选",
                "intel_angle": "强调体验",
                "hook_suggestion": "三步判断",
            }
        ],
    }
    report = analysis_artifacts.build_daily_report(l1, l2, l3, l4)
    assert report["headline"] == "AI PC 内容机会"
    assert report["sections"][0]["title"] == "趋势聚类"
    assert report["sections"][-1]["title"] == "选题推荐"
