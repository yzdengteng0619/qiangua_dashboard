# Qiangua Dashboard Insights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the current single generated HTML report into a web service with separate data dashboard and insight daily pages.

**Architecture:** Keep one Python service for now. Extract data access, analysis artifacts, and HTML rendering into focused modules, then expose `/dashboard` for operational data views and `/insights` for AI HOT-style daily analysis reading.

**Tech Stack:** Python 3.10+, stdlib `http.server`, SQLite, pandas, MiniMax API, server-rendered HTML/CSS/JS.

---

## File Structure

- Create `db.py`: database path, schema initialization, connection helper, run/artifact helpers.
- Create `ingest.py`: file type detection, archive extraction, Excel parsing, database insert functions.
- Create `analysis.py`: MiniMax calls, JSON parsing, 4-layer pipeline orchestration, artifact persistence.
- Create `renderers.py`: upload page, dashboard page, insights page, history page, task page.
- Modify `qiangua_upload_server.py`: reduce to HTTP routing and request handling.
- Keep `dashboard_generator.py`: temporarily available for compatibility, then route new report rendering through `renderers.py`.
- Create `tests/test_db.py`, `tests/test_ingest.py`, `tests/test_renderers.py`, `tests/test_analysis.py`.
- Create `requirements.txt`: document runtime dependencies.

## Task 1: Test Harness And Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Add dependency file**

Create `requirements.txt`:

```txt
pandas
xlrd
openpyxl
requests
pytest
```

- [ ] **Step 2: Add smoke test**

Create `tests/test_smoke.py`:

```python
def test_smoke():
    assert True
```

- [ ] **Step 3: Run smoke test**

Run:

```powershell
& 'C:/Users/yzden/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m pytest tests/test_smoke.py -v
```

Expected: `1 passed`.

- [ ] **Step 4: Commit**

```powershell
git add requirements.txt tests/test_smoke.py
git commit -m "test: add project test harness"
```

## Task 2: Database Module

**Files:**
- Create: `db.py`
- Test: `tests/test_db.py`

- [ ] **Step 1: Write database tests**

Create `tests/test_db.py`:

```python
import json
import sqlite3

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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
& 'C:/Users/yzden/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m pytest tests/test_db.py -v
```

Expected: FAIL because `db.py` does not exist.

- [ ] **Step 3: Implement `db.py`**

Create `db.py`:

```python
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
        error TEXT,
        created_at TEXT NOT NULL,
        finished_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS analysis_artifacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL,
        artifact_type TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(run_id, artifact_type))""")
    conn.commit()
    return conn


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def create_analysis_run(conn, analysis_date, model=None):
    cur = conn.execute(
        "INSERT INTO analysis_runs (analysis_date,status,model,created_at) VALUES (?,?,?,?)",
        (analysis_date, "running", model, now_iso()),
    )
    conn.commit()
    return cur.lastrowid


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
```

- [ ] **Step 4: Run tests**

Run:

```powershell
& 'C:/Users/yzden/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m pytest tests/test_db.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add db.py tests/test_db.py
git commit -m "feat: add database run and artifact module"
```

## Task 3: Renderer Module With Separate Pages

**Files:**
- Create: `renderers.py`
- Test: `tests/test_renderers.py`

- [ ] **Step 1: Write renderer tests**

Create `tests/test_renderers.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
& 'C:/Users/yzden/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m pytest tests/test_renderers.py -v
```

Expected: FAIL because `renderers.py` does not exist.

- [ ] **Step 3: Implement renderer functions**

Create `renderers.py`:

```python
from html import escape


BASE_CSS = """
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;background:#f7f8fb;color:#111827}
a{color:inherit;text-decoration:none}.app{display:grid;grid-template-columns:220px 1fr;min-height:100vh}
.side{border-right:1px solid #e5e7eb;background:#fff;padding:18px;position:sticky;top:0;height:100vh}
.brand{font-weight:800;margin-bottom:22px}.nav a{display:block;padding:9px 10px;border-radius:6px;color:#4b5563;margin-bottom:4px}.nav a.active{background:#111827;color:#fff}
.main{padding:24px 32px}.toolbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
.muted{color:#6b7280}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-bottom:18px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:14px}.num{font-size:26px;font-weight:800}.label{font-size:12px;color:#6b7280}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden}th,td{padding:10px;border-bottom:1px solid #edf0f5;text-align:left;font-size:13px}th{color:#6b7280;background:#fafafa}
.reader{display:grid;grid-template-columns:280px minmax(0,780px);gap:28px}.history{background:#fff;border-right:1px solid #e5e7eb;padding:20px;min-height:100vh}.history a{display:block;padding:10px 0;border-bottom:1px solid #f0f2f5}
.daily{padding:30px 0}.vol{font-size:12px;letter-spacing:.12em;color:#6b7280;text-transform:uppercase}.daily h1{font-size:44px;line-height:1;margin:8px 0 10px}
.lead{font-size:18px;line-height:1.7;color:#374151}.section{margin-top:34px}.section-head{display:flex;align-items:end;gap:12px;border-top:1px solid #d1d5db;padding-top:18px}
.section-num{font-size:32px;font-weight:800;color:#d1d5db}.section h2{margin:0;font-size:24px}.kicker{color:#6b7280;font-size:12px}
.article{padding:18px 0;border-bottom:1px solid #e5e7eb}.article h3{margin:0 0 6px;font-size:19px}.source{font-size:12px;color:#6b7280;margin-bottom:8px}.article p{line-height:1.7;color:#374151}
@media(max-width:800px){.app,.reader{display:block}.side,.history{position:static;height:auto;border-right:0;border-bottom:1px solid #e5e7eb}.main{padding:18px}.cards{grid-template-columns:1fr}.daily{padding:20px}.daily h1{font-size:34px}}
"""


def page(title, body):
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><style>{BASE_CSS}</style></head><body>{body}</body></html>"""


def nav(active):
    items = [("上传数据", "/upload"), ("数据看板", "/dashboard"), ("洞察日报", "/insights"), ("历史记录", "/history")]
    links = "".join(
        f'<a class="{"active" if name == active else ""}" href="{href}">{name}</a>'
        for name, href in items
    )
    return f'<aside class="side"><div class="brand">千瓜 Intel</div><nav class="nav">{links}</nav></aside>'


def render_dashboard_page(date_str, summary, top_notes, hotwords, topics):
    stat_cards = "".join(
        f'<div class="card"><div class="num">{escape(str(value))}</div><div class="label">{label}</div></div>'
        for label, value in [
            ("笔记", summary.get("note_count", 0)),
            ("热词", summary.get("hotword_count", 0)),
            ("话题", summary.get("topic_count", 0)),
        ]
    )
    note_rows = "".join(
        f"<tr><td>{escape(str(n.get('title','')))}</td><td>{escape(str(n.get('author','')))}</td><td>{escape(str(n.get('interactions',0)))}</td></tr>"
        for n in top_notes
    ) or '<tr><td colspan="3" class="muted">暂无笔记数据</td></tr>'
    body = f"""
    <div class="app">{nav("数据看板")}<main class="main">
      <div class="toolbar"><div><h1>数据看板</h1><p class="muted">{escape(date_str)} · 原始数据、排行和筛选</p></div><a href="/insights?date={escape(date_str)}">打开洞察日报</a></div>
      <section class="cards">{stat_cards}</section>
      <h2>爆款笔记</h2>
      <table><thead><tr><th>标题</th><th>作者</th><th>互动</th></tr></thead><tbody>{note_rows}</tbody></table>
    </main></div>
    """
    return page("数据看板", body)


def render_insights_page(date_str, history, report):
    history_html = "".join(
        f'<a href="/insights/{escape(h["date"])}"><strong>{escape(h["date"])}</strong><br><span class="muted">{escape(h.get("headline",""))}</span></a>'
        for h in history
    )
    points = "".join(f"<li>{escape(p)}</li>" for p in report.get("key_points", []))
    sections = []
    for idx, section in enumerate(report.get("sections", []), 1):
        articles = "".join(
            f'''<article class="article"><h3>{escape(item.get("title",""))}</h3><div class="source">{escape(item.get("source",""))}</div><p>{escape(item.get("summary",""))}</p></article>'''
            for item in section.get("items", [])
        )
        sections.append(
            f'''<section class="section"><div class="section-head"><div class="section-num">{idx:02d}</div><div><h2>{escape(section.get("title",""))}</h2><div class="kicker">{escape(section.get("kicker",""))}</div></div></div>{articles}</section>'''
        )
    body = f"""
    <div class="reader">
      <aside class="history"><div class="brand">千瓜 Intel</div><h2>日报历史</h2>{history_html}<p><a href="/dashboard?date={escape(date_str)}">打开数据看板</a></p></aside>
      <main class="daily"><div class="vol">VOL.{escape(date_str)} · QIANGUA DAILY</div><h1>洞察日报</h1><p class="lead">{escape(report.get("headline","暂无日报"))}</p><ul>{points}</ul>{''.join(sections)}</main>
    </div>
    """
    return page("洞察日报", body)
```

- [ ] **Step 4: Run renderer tests**

Run:

```powershell
& 'C:/Users/yzden/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m pytest tests/test_renderers.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add renderers.py tests/test_renderers.py
git commit -m "feat: add separate dashboard and insights renderers"
```

## Task 4: API Data Builders

**Files:**
- Create: `report_data.py`
- Test: `tests/test_report_data.py`

- [ ] **Step 1: Write data builder tests**

Create `tests/test_report_data.py`:

```python
import db
import report_data


def test_dashboard_summary_counts_rows(tmp_path):
    conn = db.init_db(tmp_path / "qiangua.db")
    conn.execute("INSERT INTO xhs_notes (title,note_url,import_date,interactions) VALUES (?,?,?,?)", ("A", "u1", "2026-07-02", 10))
    conn.execute("INSERT INTO xhs_hotwords (word,import_date,category) VALUES (?,?,?)", ("AI PC", "2026-07-02", "tech"))
    conn.execute("INSERT INTO xhs_topics (topic_name,import_date) VALUES (?,?)", ("电脑", "2026-07-02"))
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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
& 'C:/Users/yzden/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m pytest tests/test_report_data.py -v
```

Expected: FAIL because `report_data.py` does not exist.

- [ ] **Step 3: Implement data builders**

Create `report_data.py`:

```python
import json


def dashboard_summary(conn, date_str):
    return {
        "note_count": conn.execute("SELECT COUNT(*) FROM xhs_notes WHERE import_date=?", (date_str,)).fetchone()[0],
        "hotword_count": conn.execute("SELECT COUNT(*) FROM xhs_hotwords WHERE import_date=?", (date_str,)).fetchone()[0],
        "topic_count": conn.execute("SELECT COUNT(*) FROM xhs_topics WHERE import_date=?", (date_str,)).fetchone()[0],
    }


def top_notes(conn, date_str, limit=50):
    rows = conn.execute(
        """SELECT title, author_name, interactions, note_url
           FROM xhs_notes WHERE import_date=?
           ORDER BY interactions DESC LIMIT ?""",
        (date_str, limit),
    ).fetchall()
    return [
        {"title": r[0] or "", "author": r[1] or "", "interactions": r[2] or 0, "url": r[3] or ""}
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
        {"word": r[0] or "", "heat_value": r[1] or 0, "note_delta": r[2] or 0, "category": r[3] or ""}
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
        {"topic": r[0] or "", "view_delta": r[1] or 0, "interact_delta": r[2] or 0, "note_delta": r[3] or 0}
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
```

- [ ] **Step 4: Run data builder tests**

Run:

```powershell
& 'C:/Users/yzden/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m pytest tests/test_report_data.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add report_data.py tests/test_report_data.py
git commit -m "feat: add dashboard and insights data builders"
```

## Task 5: Route New Pages From Existing Server

**Files:**
- Modify: `qiangua_upload_server.py`
- Test: `tests/test_server_routes.py`

- [ ] **Step 1: Write route helper tests**

Create `tests/test_server_routes.py`:

```python
import qiangua_upload_server as server


def test_normalize_date_route():
    assert server.parse_date_from_path("/insights/2026-07-02") == "2026-07-02"
    assert server.parse_date_from_path("/dashboard?date=2026-07-02") == "2026-07-02"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
& 'C:/Users/yzden/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m pytest tests/test_server_routes.py -v
```

Expected: FAIL because `parse_date_from_path` does not exist.

- [ ] **Step 3: Add route helper**

In `qiangua_upload_server.py`, add near the imports:

```python
from urllib.parse import parse_qs, urlparse
```

Add helper near constants:

```python
def parse_date_from_path(path):
    parsed = urlparse(path)
    qs_date = parse_qs(parsed.query).get("date", [None])[0]
    if qs_date:
        return qs_date
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[0] in {"dashboard", "insights"}:
        return parts[1]
    return datetime.now().strftime("%Y-%m-%d")
```

- [ ] **Step 4: Add GET routes**

Inside `UploadHandler.do_GET`, before the old `/dashboard/` branch, add:

```python
        elif self.path.startswith('/dashboard'):
            self.send_dashboard_page()
        elif self.path.startswith('/insights'):
            self.send_insights_page()
```

Add methods on `UploadHandler`:

```python
    def send_html(self, html):
        body = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_dashboard_page(self):
        import db
        import report_data
        import renderers
        date_str = parse_date_from_path(self.path)
        conn = db.init_db(DB_PATH)
        html = renderers.render_dashboard_page(
            date_str,
            report_data.dashboard_summary(conn, date_str),
            report_data.top_notes(conn, date_str),
            report_data.top_hotwords(conn, date_str),
            report_data.top_topics(conn, date_str),
        )
        conn.close()
        self.send_html(html)

    def send_insights_page(self):
        import db
        import report_data
        import renderers
        date_str = parse_date_from_path(self.path)
        conn = db.init_db(DB_PATH)
        run = db.latest_run(conn, date_str)
        report = report_data.daily_report(conn, run[0]) if run else {"headline": "暂无洞察日报", "key_points": [], "sections": []}
        html = renderers.render_insights_page(date_str, report_data.insights_history(conn), report)
        conn.close()
        self.send_html(html)
```

- [ ] **Step 5: Run route tests**

Run:

```powershell
& 'C:/Users/yzden/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m pytest tests/test_server_routes.py -v
```

Expected: PASS.

- [ ] **Step 6: Run full test suite**

Run:

```powershell
& 'C:/Users/yzden/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m pytest -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add qiangua_upload_server.py tests/test_server_routes.py
git commit -m "feat: route dashboard and insights pages"
```

## Task 6: Convert LLM Output Into Daily Report Artifact

**Files:**
- Create: `analysis_artifacts.py`
- Test: `tests/test_analysis_artifacts.py`
- Modify: `qiangua_upload_server.py`

- [ ] **Step 1: Write artifact conversion test**

Create `tests/test_analysis_artifacts.py`:

```python
import analysis_artifacts


def test_build_daily_report_from_layers():
    l1 = {"clusters": [{"cluster_name": "AI PC", "trend_direction": "上升"}]}
    l2 = {"cluster_analyses": [{"cluster_name": "AI PC", "trend_analysis": "讨论升温"}]}
    l3 = {"content_trends": [{"trend": "教程型内容增长", "evidence": "互动高", "intel_action": "做教程"}]}
    l4 = {"weekly_theme": "AI PC 内容机会", "recommendations": [{"topic_title": "AI PC 怎么选", "intel_angle": "强调体验", "hook_suggestion": "三步判断"}]}
    report = analysis_artifacts.build_daily_report(l1, l2, l3, l4)
    assert report["headline"] == "AI PC 内容机会"
    assert report["sections"][0]["title"] == "趋势聚类"
    assert report["sections"][-1]["title"] == "选题推荐"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
& 'C:/Users/yzden/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m pytest tests/test_analysis_artifacts.py -v
```

Expected: FAIL because `analysis_artifacts.py` does not exist.

- [ ] **Step 3: Implement conversion**

Create `analysis_artifacts.py`:

```python
def build_daily_report(l1, l2, l3, l4):
    headline = l4.get("weekly_theme") or l1.get("summary") or "今日千瓜洞察"
    key_points = []
    for rec in l4.get("recommendations", [])[:3]:
        title = rec.get("topic_title")
        if title:
            key_points.append(title)
    sections = [
        {
            "title": "趋势聚类",
            "kicker": "Trend Clusters",
            "items": [
                {
                    "title": c.get("cluster_name", ""),
                    "source": "热词与话题",
                    "summary": f"{c.get('trend_direction','')}。{c.get('relevance_reason','')}",
                }
                for c in l1.get("clusters", [])
            ],
        },
        {
            "title": "深度机会",
            "kicker": "Opportunities",
            "items": [
                {
                    "title": a.get("cluster_name", ""),
                    "source": "LLM Layer 2",
                    "summary": a.get("trend_analysis", ""),
                }
                for a in l2.get("cluster_analyses", [])
            ],
        },
        {
            "title": "内容趋势",
            "kicker": "Content Patterns",
            "items": [
                {
                    "title": t.get("trend", ""),
                    "source": "爆款笔记",
                    "summary": f"{t.get('evidence','')} {t.get('intel_action','')}",
                }
                for t in l3.get("content_trends", [])
            ],
        },
        {
            "title": "选题推荐",
            "kicker": "Recommendations",
            "items": [
                {
                    "title": r.get("topic_title", ""),
                    "source": r.get("content_type", "选题"),
                    "summary": f"{r.get('intel_angle','')} {r.get('hook_suggestion','')}",
                }
                for r in l4.get("recommendations", [])
            ],
        },
    ]
    return {"headline": headline, "key_points": key_points, "sections": sections}
```

- [ ] **Step 4: Persist `daily_report` after L4**

In `run_analysis_pipeline`, after `l4_result` is created and before the HTML generation event, add:

```python
    import db
    import analysis_artifacts
    run_id = db.create_analysis_run(conn, date_str, model="MiniMax-Text-01")
    db.save_artifact(conn, run_id, "l1_clusters", l1_result)
    db.save_artifact(conn, run_id, "l2_opportunities", l2_result)
    db.save_artifact(conn, run_id, "l3_note_patterns", l3_result)
    db.save_artifact(conn, run_id, "l4_recommendations", l4_result)
    db.save_artifact(conn, run_id, "daily_report", analysis_artifacts.build_daily_report(l1_result, l2_result, l3_result, l4_result))
    db.finish_analysis_run(conn, run_id, "done")
```

- [ ] **Step 5: Run tests**

Run:

```powershell
& 'C:/Users/yzden/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m pytest tests/test_analysis_artifacts.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add analysis_artifacts.py tests/test_analysis_artifacts.py qiangua_upload_server.py
git commit -m "feat: persist structured insights daily report"
```

## Task 7: Manual Browser Verification

**Files:**
- Modify only if verification finds layout or route defects.

- [ ] **Step 1: Start server**

Run:

```powershell
& 'C:/Users/yzden/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' qiangua_upload_server.py --host 127.0.0.1 --port 8090
```

Expected: service prints a local URL and stays running.

- [ ] **Step 2: Open upload page**

Open `http://127.0.0.1:8090/`.

Expected: upload page loads.

- [ ] **Step 3: Open dashboard page**

Open `http://127.0.0.1:8090/dashboard`.

Expected: page title is `数据看板`, left navigation is visible, empty state appears if no data exists.

- [ ] **Step 4: Open insights page**

Open `http://127.0.0.1:8090/insights`.

Expected: page title is `洞察日报`, left history panel is visible, empty state appears if no report exists.

- [ ] **Step 5: Check mobile width**

Set viewport near 390 px wide.

Expected: navigation and history stack above content, text does not overlap.

- [ ] **Step 6: Commit any fixes**

```powershell
git add qiangua_upload_server.py renderers.py
git commit -m "fix: polish dashboard and insights routes"
```

## Self-Review Notes

- Spec coverage: upload flow, two-page product structure, history, artifacts, errors, and tests are covered.
- Scope: this plan intentionally avoids FastAPI, React, authentication, and deployment. Those are follow-up projects after the service has stable page boundaries.
- Risk: Task 6 touches the existing long `run_analysis_pipeline`; implement it carefully and avoid changing prompt behavior in the same commit.
