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


def test_upload_page_has_task_center_sections():
    html = renderers.render_upload_page("2026-07-02")
    assert "upload-command-center" in html
    assert "drop-zone" in html
    assert "pipeline-steps" in html
    assert "quick-links" in html
    assert "recent-runs" in html


def test_upload_page_preserves_upload_contract():
    html = renderers.render_upload_page("2026-07-02")
    assert 'type="file"' in html
    assert "multiple" in html
    assert "fetch('/upload'" in html
    assert "EventSource('/progress/'" in html


def test_upload_page_renders_recent_runs():
    html = renderers.render_upload_page(
        "2026-07-02",
        recent_runs=[
            {
                "id": 7,
                "analysis_date": "2026-07-02",
                "status": "done",
                "current_stage": "生成页面",
                "total_rows": 128,
            }
        ],
    )
    assert "2026-07-02" in html
    assert "done" in html
    assert "生成页面" in html
    assert "128" in html
    assert 'href="/runs/7"' in html


def test_upload_page_renders_recent_run_error_detail():
    html = renderers.render_upload_page(
        "2026-07-02",
        recent_runs=[
            {
                "analysis_date": "2026-07-02",
                "status": "failed",
                "current_stage": "校验失败",
                "total_rows": 0,
                "error": "未识别的千瓜文件类型: bad.xlsx",
            }
        ],
    )
    assert "failed" in html
    assert "校验失败" in html
    assert "未识别的千瓜文件类型" in html


def test_run_detail_page_renders_quality_panel():
    html = renderers.render_run_detail_page(
        {
            "run": {
                "id": 7,
                "analysis_date": "2026-07-02",
                "status": "done",
                "current_stage": "已完成",
                "total_rows": 128,
                "error": "",
            },
            "quality": {
                "note_count": 80,
                "hotword_count": 30,
                "topic_count": 18,
            },
        }
    )
    assert "任务详情" in html
    assert "数据质量" in html
    assert "2026-07-02" in html
    assert "80" in html


def test_run_detail_page_renders_file_checks():
    html = renderers.render_run_detail_page(
        {
            "run": {
                "id": 7,
                "analysis_date": "2026-07-02",
                "status": "failed",
                "current_stage": "校验失败",
                "total_rows": 0,
                "error": "文件校验失败",
            },
            "quality": {"note_count": 0, "hotword_count": 0, "topic_count": 0},
            "file_checks": [
                {
                    "filename": "bad.xlsx",
                    "sheet_type": "unknown",
                    "status": "failed",
                    "row_count": 0,
                    "error": "未识别的千瓜文件类型",
                }
            ],
        }
    )
    assert "上传文件明细" in html
    assert "bad.xlsx" in html
    assert "未识别的千瓜文件类型" in html
