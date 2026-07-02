import renderers


def test_dashboard_page_has_data_workbench_language():
    html = renderers.render_dashboard_page(
        date_str="2026-07-02",
        summary={"note_count": 10, "hotword_count": 3, "topic_count": 2},
        top_notes=[],
        hotwords=[],
        topics=[],
    )
    assert "数据看板" in html
    assert "洞察日报" in html
    assert "笔记" in html
    assert "热词" in html


def test_insights_page_has_daily_reader_structure():
    html = renderers.render_insights_page(
        date_str="2026-07-02",
        history=[{"date": "2026-07-02", "headline": "今日重点"}],
        report={
            "headline": "今日重点",
            "key_points": ["机会一"],
            "sections": [
                {
                    "title": "趋势聚类",
                    "kicker": "Trends",
                    "items": [
                        {
                            "title": "AI PC 讨论升温",
                            "source": "千瓜热词",
                            "summary": "热词和话题同时增长。",
                        }
                    ],
                }
            ],
        },
    )
    assert "洞察日报" in html
    assert "日报历史" in html
    assert "AI PC 讨论升温" in html
