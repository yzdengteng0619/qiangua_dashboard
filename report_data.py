import json


def dashboard_summary(conn, date_str):
    return {
        "note_count": conn.execute(
            "SELECT COUNT(*) FROM xhs_notes WHERE import_date=?", (date_str,)
        ).fetchone()[0],
        "hotword_count": conn.execute(
            "SELECT COUNT(*) FROM xhs_hotwords WHERE import_date=?", (date_str,)
        ).fetchone()[0],
        "topic_count": conn.execute(
            "SELECT COUNT(*) FROM xhs_topics WHERE import_date=?", (date_str,)
        ).fetchone()[0],
    }


def top_notes(conn, date_str, limit=50):
    rows = conn.execute(
        """SELECT title, author_name, interactions, note_url
           FROM xhs_notes WHERE import_date=?
           ORDER BY interactions DESC LIMIT ?""",
        (date_str, limit),
    ).fetchall()
    return [
        {
            "title": r[0] or "",
            "author": r[1] or "",
            "interactions": r[2] or 0,
            "url": r[3] or "",
        }
        for r in rows
    ]


def top_hotwords(conn, date_str, limit=50):
    rows = conn.execute(
        """SELECT word, heat_value, note_delta, category
           FROM xhs_hotwords WHERE import_date=?
           ORDER BY note_delta DESC LIMIT ?""",
        (date_str, limit),
    ).fetchall()
    return [
        {
            "word": r[0] or "",
            "heat_value": r[1] or 0,
            "note_delta": r[2] or 0,
            "category": r[3] or "",
        }
        for r in rows
    ]


def top_topics(conn, date_str, limit=50):
    rows = conn.execute(
        """SELECT topic_name, view_delta, interact_delta, note_delta
           FROM xhs_topics WHERE import_date=?
           ORDER BY view_delta DESC LIMIT ?""",
        (date_str, limit),
    ).fetchall()
    return [
        {
            "topic": r[0] or "",
            "view_delta": r[1] or 0,
            "interact_delta": r[2] or 0,
            "note_delta": r[3] or 0,
        }
        for r in rows
    ]


def insights_history(conn, limit=30):
    rows = conn.execute(
        """SELECT r.id, r.analysis_date
           FROM analysis_runs r
           ORDER BY r.analysis_date DESC, r.id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    history = []
    seen = set()
    for run_id, date_str in rows:
        if date_str in seen:
            continue
        seen.add(date_str)
        artifact = conn.execute(
            "SELECT content FROM analysis_artifacts WHERE run_id=? AND artifact_type='daily_report'",
            (run_id,),
        ).fetchone()
        headline = ""
        if artifact:
            headline = json.loads(artifact[0]).get("headline", "")
        history.append({"date": date_str, "headline": headline})
    return history


def daily_report(conn, run_id):
    row = conn.execute(
        "SELECT content FROM analysis_artifacts WHERE run_id=? AND artifact_type='daily_report'",
        (run_id,),
    ).fetchone()
    if not row:
        return {"headline": "暂无洞察日报", "key_points": [], "sections": []}
    return json.loads(row[0])
