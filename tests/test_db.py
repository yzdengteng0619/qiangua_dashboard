import db


def test_init_db_creates_core_tables(tmp_path):
    path = tmp_path / "qiangua.db"
    conn = db.init_db(path)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "xhs_notes" in tables
    assert "xhs_hotwords" in tables
    assert "xhs_topics" in tables
    assert "xhs_analysis" in tables
    assert "upload_log" in tables
    assert "analysis_runs" in tables
    assert "upload_batches" in tables
    assert "analysis_artifacts" in tables


def test_artifact_round_trip(tmp_path):
    path = tmp_path / "qiangua.db"
    conn = db.init_db(path)
    run_id = db.create_analysis_run(conn, "2026-07-02")
    db.save_artifact(conn, run_id, "daily_report", {"headline": "test"})
    assert db.get_artifact(conn, run_id, "daily_report") == {"headline": "test"}
