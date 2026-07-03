import sqlite3

from dashboard_generator import generate_dashboard


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE xhs_notes (import_date TEXT)")
    conn.execute("CREATE TABLE xhs_hotwords (import_date TEXT)")
    conn.execute("CREATE TABLE xhs_topics (import_date TEXT)")
    conn.execute("CREATE TABLE xhs_analysis (id INTEGER PRIMARY KEY AUTOINCREMENT, analysis_type TEXT, content TEXT)")
    return conn


def test_dashboard_generator_escapes_llm_content(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    malicious = '<script>alert("x")</script>'

    path = generate_dashboard(
        "2026-07-03",
        {"clusters": [{"cluster_name": malicious, "hotwords": [malicious], "topics": [], "intel_relevance": "高"}]},
        {"cluster_analyses": [{"cluster_name": malicious, "trend_analysis": malicious}]},
        {"clusters": []},
        {
            "recommendations": [
                {
                    "topic_title": malicious,
                    "intel_angle": malicious,
                    "hook_suggestion": malicious,
                    "reference_notes": [{"url": "javascript:alert(1)", "title": malicious}],
                }
            ]
        },
        _conn(),
    )

    html = open(path, encoding="utf-8").read()
    assert malicious not in html
    assert "&lt;script&gt;" in html
    assert "javascript:alert" not in html
