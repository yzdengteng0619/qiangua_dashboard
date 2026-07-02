import db
import report_data


def test_dashboard_summary_counts_rows(tmp_path):
    conn = db.init_db(tmp_path / "qiangua.db")
    conn.execute(
        "INSERT INTO xhs_notes (title,note_url,import_date,interactions) VALUES (?,?,?,?)",
        ("A", "u1", "2026-07-02", 10),
    )
    conn.execute(
        "INSERT INTO xhs_hotwords (word,import_date,category) VALUES (?,?,?)",
        ("AI PC", "2026-07-02", "tech"),
    )
    conn.execute(
        "INSERT INTO xhs_topics (topic_name,import_date) VALUES (?,?)",
        ("电脑", "2026-07-02"),
    )
    conn.commit()
    summary = report_data.dashboard_summary(conn, "2026-07-02")
    assert summary == {"note_count": 1, "hotword_count": 1, "topic_count": 1}


def test_history_uses_latest_runs(tmp_path):
    conn = db.init_db(tmp_path / "qiangua.db")
    run_id = db.create_analysis_run(conn, "2026-07-02")
    db.save_artifact(conn, run_id, "daily_report", {"headline": "今日重点"})
    history = report_data.insights_history(conn)
    assert history[0]["date"] == "2026-07-02"
    assert history[0]["headline"] == "今日重点"
