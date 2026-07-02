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


def test_analysis_run_stage_and_recent_history(tmp_path):
    path = tmp_path / "qiangua.db"
    conn = db.init_db(path)
    run_id = db.create_analysis_run(conn, "2026-07-02", model="MiniMax-Text-01")
    db.update_analysis_run(conn, run_id, status="running", current_stage="解析入库", total_rows=42)
    db.finish_analysis_run(conn, run_id, status="done")

    runs = db.recent_analysis_runs(conn)
    assert runs[0]["id"] == run_id
    assert runs[0]["analysis_date"] == "2026-07-02"
    assert runs[0]["status"] == "done"
    assert runs[0]["current_stage"] == "解析入库"
    assert runs[0]["total_rows"] == 42
