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
def test_dashboard_page_has_polished_visual_sections():
    html = renderers.render_dashboard_page(
        date_str="2026-07-02",
        summary={"note_count": 10, "hotword_count": 3, "topic_count": 2},
        top_notes=[{"title": "AI PC 怎么选", "author": "作者A", "interactions": 1200}],
        hotwords=[{"word": "AI PC", "note_delta": 300, "heat_value": 9000}],
        topics=[{"topic": "开学电脑", "view_delta": 50000, "interact_delta": 1200}],
    )
    assert "hero-panel" in html
    assert "metric-strip" in html
    assert "mini-board" in html
    assert "visual-rank" in html


def test_insights_page_has_editorial_visual_sections():
    html = renderers.render_insights_page(
        date_str="2026-07-02",
        history=[{"date": "2026-07-02", "headline": "今日重点"}],
        report={
            "headline": "今日重点",
            "key_points": ["机会一", "机会二"],
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
    assert "daily-cover" in html
    assert "signal-list" in html
    assert "insight-card" in html
