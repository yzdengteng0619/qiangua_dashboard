import json
import sqlite3
from datetime import datetime
from pathlib import Path


DEFAULT_DB_PATH = Path.home() / "clawd" / "knowledge" / "qiangua_xhs.db"


def connect(db_path=None):
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path=None):
    conn = connect(db_path)
    conn.execute("""CREATE TABLE IF NOT EXISTS xhs_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rank INTEGER, publish_time TEXT, title TEXT,
        is_brand_partner TEXT, is_commercial TEXT, is_promoted TEXT,
        note_type TEXT, note_form TEXT, brand_name TEXT,
        note_url TEXT, tags TEXT,
        interactions INTEGER, likes INTEGER, collects INTEGER,
        comments INTEGER, shares INTEGER,
        author_name TEXT, followers INTEGER, xhs_level TEXT,
        author_attr TEXT, region TEXT, author_url TEXT, qiangua_url TEXT,
        file_source TEXT, sheet_type TEXT, import_date TEXT,
        UNIQUE(note_url, import_date))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS xhs_hotwords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rank INTEGER, word TEXT, heat_value INTEGER,
        current_notes INTEGER, prev_notes INTEGER,
        note_delta INTEGER, growth_rate TEXT,
        current_commercial INTEGER, prev_commercial INTEGER,
        commercial_delta INTEGER, commercial_growth TEXT,
        category TEXT, file_source TEXT, import_date TEXT,
        UNIQUE(word, import_date, category))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS xhs_topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rank INTEGER, topic_name TEXT, topic_intro TEXT,
        launch_time TEXT, heat_delta INTEGER, view_delta INTEGER,
        interact_delta INTEGER, note_delta INTEGER,
        file_source TEXT, import_date TEXT,
        UNIQUE(topic_name, import_date))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS xhs_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_date TEXT, analysis_type TEXT,
        content TEXT, model TEXT, created_at TEXT,
        UNIQUE(analysis_date, analysis_type))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS upload_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT, file_size INTEGER, sheet_type TEXT,
        row_count INTEGER, import_time TEXT, status TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS upload_batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'created')""")
    conn.execute("""CREATE TABLE IF NOT EXISTS analysis_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_date TEXT NOT NULL,
        status TEXT NOT NULL,
        model TEXT,
        current_stage TEXT,
        total_rows INTEGER DEFAULT 0,
        error TEXT,
        created_at TEXT NOT NULL,
        finished_at TEXT)""")
    ensure_column(conn, "analysis_runs", "current_stage", "TEXT")
    ensure_column(conn, "analysis_runs", "total_rows", "INTEGER DEFAULT 0")
    conn.execute("""CREATE TABLE IF NOT EXISTS analysis_artifacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL,
        artifact_type TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(run_id, artifact_type))""")
    conn.commit()
    return conn


def ensure_column(conn, table, column, definition):
    columns = {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def create_analysis_run(conn, analysis_date, model=None):
    cur = conn.execute(
        "INSERT INTO analysis_runs (analysis_date,status,model,current_stage,total_rows,created_at) VALUES (?,?,?,?,?,?)",
        (analysis_date, "running", model, "等待上传", 0, now_iso()),
    )
    conn.commit()
    return cur.lastrowid


def update_analysis_run(conn, run_id, status=None, current_stage=None, total_rows=None, error=None):
    updates = []
    params = []
    if status is not None:
        updates.append("status=?")
        params.append(status)
    if current_stage is not None:
        updates.append("current_stage=?")
        params.append(current_stage)
    if total_rows is not None:
        updates.append("total_rows=?")
        params.append(total_rows)
    if error is not None:
        updates.append("error=?")
        params.append(error)
    if not updates:
        return
    params.append(run_id)
    conn.execute(f"UPDATE analysis_runs SET {', '.join(updates)} WHERE id=?", params)
    conn.commit()


def finish_analysis_run(conn, run_id, status="done", error=None):
    conn.execute(
        "UPDATE analysis_runs SET status=?, error=?, finished_at=? WHERE id=?",
        (status, error, now_iso(), run_id),
    )
    conn.commit()


def save_artifact(conn, run_id, artifact_type, content):
    conn.execute(
        """INSERT OR REPLACE INTO analysis_artifacts
           (run_id, artifact_type, content, created_at) VALUES (?,?,?,?)""",
        (run_id, artifact_type, json.dumps(content, ensure_ascii=False), now_iso()),
    )
    conn.commit()


def get_artifact(conn, run_id, artifact_type):
    row = conn.execute(
        "SELECT content FROM analysis_artifacts WHERE run_id=? AND artifact_type=?",
        (run_id, artifact_type),
    ).fetchone()
    return json.loads(row[0]) if row else None


def latest_run(conn, analysis_date=None):
    if analysis_date:
        return conn.execute(
            "SELECT id, analysis_date, status, model, error, created_at, finished_at "
            "FROM analysis_runs WHERE analysis_date=? ORDER BY id DESC LIMIT 1",
            (analysis_date,),
        ).fetchone()
    return conn.execute(
        "SELECT id, analysis_date, status, model, error, created_at, finished_at "
        "FROM analysis_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()


def recent_analysis_runs(conn, limit=5):
    rows = conn.execute(
        """SELECT id, analysis_date, status, model, current_stage, total_rows, error, created_at, finished_at
           FROM analysis_runs ORDER BY id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [
        {
            "id": row[0],
            "analysis_date": row[1],
            "status": row[2],
            "model": row[3] or "",
            "current_stage": row[4] or "",
            "total_rows": row[5] or 0,
            "error": row[6] or "",
            "created_at": row[7] or "",
            "finished_at": row[8] or "",
        }
        for row in rows
    ]
