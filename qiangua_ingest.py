#!/usr/bin/env python3
"""
千瓜小红书数据解析入库 + HTML看板生成
======================================
Usage:
    # 解析单个文件
    python3 qiangua_ingest.py /path/to/file.xls

    # 解析目录下所有xls文件
    python3 qiangua_ingest.py /path/to/dir/

    # 解析后生成HTML看板
    python3 qiangua_ingest.py /path/to/dir/ --dashboard

    # 仅生成看板（不解析新数据）
    python3 qiangua_ingest.py --dashboard-only --date 2026-07-02
"""

import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("缺少 pandas: pip3 install pandas xlrd")
    sys.exit(1)

# ─── 配置 ─────────────────────────────────────────────────────────────────────
DB_PATH = os.path.expanduser("~/clawd/knowledge/qiangua_xhs.db")
UPLOAD_DIR = Path.home() / "clawd" / "qiangua_uploads"
DASHBOARD_DIR = Path.home() / "clawd" / "xhs_hot_reports"

# ─── 数据库初始化 ─────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    # 笔记榜单（实时/低粉/商业 通用）
    conn.execute("""CREATE TABLE IF NOT EXISTS xhs_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rank INTEGER,
        publish_time TEXT,
        title TEXT,
        is_brand_partner TEXT,
        is_commercial TEXT,
        is_promoted TEXT,
        note_type TEXT,
        note_form TEXT,
        brand_name TEXT,
        note_url TEXT,
        tags TEXT,
        interactions INTEGER,
        likes INTEGER,
        collects INTEGER,
        comments INTEGER,
        shares INTEGER,
        author_name TEXT,
        followers INTEGER,
        xhs_level TEXT,
        author_attr TEXT,
        region TEXT,
        author_url TEXT,
        qiangua_url TEXT,
        file_source TEXT,
        sheet_type TEXT,
        import_date TEXT,
        UNIQUE(note_url, import_date)
    )""")

    # 热词榜
    conn.execute("""CREATE TABLE IF NOT EXISTS xhs_hotwords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rank INTEGER,
        word TEXT,
        heat_value INTEGER,
        current_notes INTEGER,
        prev_notes INTEGER,
        note_delta INTEGER,
        growth_rate TEXT,
        current_commercial INTEGER,
        prev_commercial INTEGER,
        commercial_delta INTEGER,
        commercial_growth TEXT,
        category TEXT,
        file_source TEXT,
        import_date TEXT,
        UNIQUE(word, import_date, category)
    )""")

    # 话题榜
    conn.execute("""CREATE TABLE IF NOT EXISTS xhs_topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rank INTEGER,
        topic_name TEXT,
        topic_intro TEXT,
        launch_time TEXT,
        heat_delta INTEGER,
        view_delta INTEGER,
        interact_delta INTEGER,
        note_delta INTEGER,
        file_source TEXT,
        import_date TEXT,
        UNIQUE(topic_name, import_date)
    )""")

    # 上传日志
    conn.execute("""CREATE TABLE IF NOT EXISTS upload_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        file_size INTEGER,
        sheet_type TEXT,
        row_count INTEGER,
        import_time TEXT,
        status TEXT
    )""")

    conn.commit()
    return conn


# ─── 文件类型识别 ──────────────────────────────────────────────────────────────
def detect_sheet_type(filename):
    """从文件名识别数据类型"""
    fn = filename.lower()
    if "实时笔记榜单" in fn and "低粉" not in fn and "6小时" not in fn:
        return "realtime_notes"
    elif "实时笔记榜单" in fn and "6小时" in fn:
        return "realtime_notes_6h"
    elif "实时低粉笔记榜单" in fn:
        return "low_fan_notes"
    elif "商业笔记榜单" in fn:
        return "commercial_notes"
    elif "热词增量榜" in fn:
        return "hotwords_delta"
    elif "热词总量榜" in fn:
        return "hotwords_total"
    elif "热门话题增量榜" in fn:
        return "topics_delta"
    elif "流量扶持榜" in fn:
        return "traffic_boost"
    else:
        return "unknown"


# ─── 数据解析 ──────────────────────────────────────────────────────────────────
def parse_notes(df, sheet_type, filename, import_date):
    """解析笔记榜单数据"""
    rows = []
    for _, row in df.iterrows():
        note_url = str(row.get("笔记链接", "") or "")
        title = str(row.get("笔记标题", "") or "")[:500]

        def safe_int(v):
            if pd.isna(v): return 0
            s = str(v).replace(",", "").replace("万", "0000").replace("+", "")
            try: return int(float(s))
            except: return 0

        rows.append((
            int(row.get("排名", 0) or 0),
            str(row.get("笔记发布时间", "") or ""),
            title,
            str(row.get("是否品牌合作人", "") or ""),
            str(row.get("是否商业笔记", "") or ""),
            str(row.get("是否推广笔记", "") or ""),
            str(row.get("笔记类型", "") or ""),
            str(row.get("笔记形式", "") or ""),
            str(row.get("报备合作品牌", "") or ""),
            note_url,
            str(row.get("笔记标签", "") or ""),
            safe_int(row.get("互动量")),
            safe_int(row.get("点赞")),
            safe_int(row.get("收藏")),
            safe_int(row.get("评论")),
            safe_int(row.get("分享")),
            str(row.get("达人昵称", "") or ""),
            safe_int(row.get("粉丝数")),
            str(row.get("红薯等级", "") or ""),
            str(row.get("达人属性", "") or ""),
            str(row.get("地域", "") or ""),
            str(row.get("达人小红书主页地址", "") or ""),
            str(row.get("达人千瓜主页地址", "") or ""),
            filename,
            sheet_type,
            import_date,
        ))
    return rows


def parse_hotwords(df, sheet_type, filename, import_date):
    """解析热词榜数据"""
    rows = []
    for _, row in df.iterrows():
        word = str(row.get("热搜词名称", "") or "")
        if not word or word == "nan": continue

        def safe_int(v):
            if pd.isna(v): return 0
            s = str(v).replace(",", "")
            try: return int(float(s))
            except: return 0

        rows.append((
            int(row.get("排名", 0) or 0),
            word,
            safe_int(row.get("当前热度值")),
            safe_int(row.get("当前周期笔记数")),
            safe_int(row.get("上一周期笔记数")),
            safe_int(row.get("相关笔记增量")),
            str(row.get("增幅", "") or ""),
            safe_int(row.get("当前周期商业笔记数")),
            safe_int(row.get("上一周期商业笔记数")),
            safe_int(row.get("商业笔记增量")),
            str(row.get("商业笔记增幅", "") or ""),
            str(row.get("所属分类", "") or ""),
            filename,
            import_date,
        ))
    return rows


def parse_topics(df, sheet_type, filename, import_date):
    """解析话题榜数据"""
    rows = []
    for _, row in df.iterrows():
        topic = str(row.get("话题名称", "") or "")
        if not topic or topic == "nan": continue

        def safe_int(v):
            if pd.isna(v): return 0
            s = str(v).replace(",", "")
            try: return int(float(s))
            except: return 0

        rows.append((
            int(row.get("排名", 0) or 0),
            topic,
            str(row.get("话题简介", "") or ""),
            str(row.get("上线时间", "") or ""),
            safe_int(row.get("热度增量")),
            safe_int(row.get("浏览增量")),
            safe_int(row.get("互动增量")),
            safe_int(row.get("笔记增量")),
            filename,
            import_date,
        ))
    return rows


# ─── 入库 ──────────────────────────────────────────────────────────────────────
def insert_notes(conn, rows):
    inserted = 0
    for r in rows:
        try:
            conn.execute("""INSERT OR IGNORE INTO xhs_notes
                (rank,publish_time,title,is_brand_partner,is_commercial,is_promoted,
                 note_type,note_form,brand_name,note_url,tags,interactions,likes,
                 collects,comments,shares,author_name,followers,xhs_level,author_attr,
                 region,author_url,qiangua_url,file_source,sheet_type,import_date)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", r)
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return inserted


def insert_hotwords(conn, rows):
    inserted = 0
    for r in rows:
        try:
            conn.execute("""INSERT OR IGNORE INTO xhs_hotwords
                (rank,word,heat_value,current_notes,prev_notes,note_delta,growth_rate,
                 current_commercial,prev_commercial,commercial_delta,commercial_growth,
                 category,file_source,import_date)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", r)
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return inserted


def insert_topics(conn, rows):
    inserted = 0
    for r in rows:
        try:
            conn.execute("""INSERT OR IGNORE INTO xhs_topics
                (rank,topic_name,topic_intro,launch_time,heat_delta,view_delta,
                 interact_delta,note_delta,file_source,import_date)
                VALUES (?,?,?,?,?,?,?,?,?,?)""", r)
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return inserted


# ─── 主解析流程 ────────────────────────────────────────────────────────────────
def ingest_file(conn, filepath):
    filename = os.path.basename(filepath)
    sheet_type = detect_sheet_type(filename)
    import_date = datetime.now().strftime("%Y-%m-%d")

    print(f"  📄 {filename} → {sheet_type}")

    if sheet_type == "unknown":
        print(f"    ⚠️ 未识别的文件类型，跳过")
        return 0

    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        print(f"    ❌ 读取失败: {e}")
        return 0

    total_inserted = 0

    if sheet_type in ("realtime_notes", "realtime_notes_6h", "low_fan_notes", "commercial_notes"):
        rows = parse_notes(df, sheet_type, filename, import_date)
        inserted = insert_notes(conn, rows)
        total_inserted = inserted
        print(f"    ✓ {inserted}/{len(rows)} 条笔记入库")

    elif sheet_type in ("hotwords_delta", "hotwords_total"):
        rows = parse_hotwords(df, sheet_type, filename, import_date)
        inserted = insert_hotwords(conn, rows)
        total_inserted = inserted
        print(f"    ✓ {inserted}/{len(rows)} 条热词入库")

    elif sheet_type == "topics_delta":
        rows = parse_topics(df, sheet_type, filename, import_date)
        inserted = insert_topics(conn, rows)
        total_inserted = inserted
        print(f"    ✓ {inserted}/{len(rows)} 条话题入库")

    elif sheet_type == "traffic_boost":
        # 流量扶持榜结构类似笔记榜
        rows = parse_notes(df, sheet_type, filename, import_date)
        inserted = insert_notes(conn, rows)
        total_inserted = inserted
        print(f"    ✓ {inserted}/{len(rows)} 条入库")

    # 记录上传日志
    conn.execute("INSERT INTO upload_log (filename,file_size,sheet_type,row_count,import_time,status) VALUES (?,?,?,?,?,?)",
                 (filename, os.path.getsize(filepath), sheet_type, len(df), datetime.now().isoformat(), "ok"))
    conn.commit()
    return total_inserted


# ─── HTML 看板 ────────────────────────────────────────────────────────────────
def fmt(n):
    if n is None: return "0"
    if n >= 10000: return f"{n/10000:.1f}w"
    if n >= 1000: return f"{n/1000:.1f}k"
    return str(n)


def generate_dashboard(conn, date_str):
    """从数据库生成HTML看板"""
    sections = []

    # 1. 实时笔记榜（科技数码）
    rows = conn.execute("""
        SELECT rank, title, author_name, followers, likes, collects, comments, shares, interactions, note_form, note_url, author_attr
        FROM xhs_notes
        WHERE import_date >= ? AND sheet_type IN ('realtime_notes','realtime_notes_6h')
        AND (file_source LIKE '%科技数码%' OR file_source LIKE '%全部行业%')
        ORDER BY interactions DESC LIMIT 30
    """, (date_str,)).fetchall()

    if rows:
        items = ""
        for r in rows[:20]:
            rank, title, author, fans, likes, collects, comments, shares, interactions, form, url, attr = r
            title = (title or "")[:45]
            url = url or "#"
            items += f'''<tr>
                <td>{rank}</td>
                <td><a href="{url}" target="_blank">{title}</a></td>
                <td>{author}</td>
                <td>{fmt(fans)}</td>
                <td>{fmt(likes)}</td>
                <td>{fmt(collects)}</td>
                <td>{fmt(comments)}</td>
                <td>{fmt(interactions)}</td>
                <td>{form}</td>
            </tr>'''
        sections.append(f'''
        <div class="section">
            <h2>📱 实时笔记榜 · 科技数码 <span class="badge">TOP20</span></h2>
            <table><thead><tr><th>#</th><th>标题</th><th>达人</th><th>粉丝</th><th>👍</th><th>⭐</th><th>💬</th><th>互动</th><th>形式</th></tr></thead>
            <tbody>{items}</tbody></table>
        </div>''')

    # 2. 低粉爆款
    rows = conn.execute("""
        SELECT rank, title, author_name, followers, likes, collects, comments, interactions, note_url
        FROM xhs_notes
        WHERE import_date >= ? AND sheet_type = 'low_fan_notes'
        ORDER BY interactions DESC LIMIT 20
    """, (date_str,)).fetchall()

    if rows:
        items = ""
        for r in rows[:15]:
            rank, title, author, fans, likes, collects, comments, interactions, url = r
            title = (title or "")[:45]
            url = url or "#"
            items += f'''<tr>
                <td>{rank}</td>
                <td><a href="{url}" target="_blank">{title}</a></td>
                <td>{author}</td>
                <td>{fmt(fans)}</td>
                <td>{fmt(likes)}</td>
                <td>{fmt(collects)}</td>
                <td>{fmt(interactions)}</td>
            </tr>'''
        sections.append(f'''
        <div class="section">
            <h2>🌱 低粉爆款（KOC选人） <span class="badge">TOP15</span></h2>
            <table><thead><tr><th>#</th><th>标题</th><th>达人</th><th>粉丝</th><th>👍</th><th>⭐</th><th>互动</th></tr></thead>
            <tbody>{items}</tbody></table>
        </div>''')

    # 3. 热词增量
    rows = conn.execute("""
        SELECT rank, word, heat_value, note_delta, growth_rate, category
        FROM xhs_hotwords
        WHERE import_date >= ? AND file_source LIKE '%科技数码%'
        AND category != '教育'
        ORDER BY note_delta DESC LIMIT 20
    """, (date_str,)).fetchall()

    if rows:
        items = ""
        for r in rows[:15]:
            rank, word, heat, delta, growth, cat = r
            items += f'''<tr>
                <td>{rank}</td>
                <td><strong>{word}</strong></td>
                <td>{heat}</td>
                <td>+{delta}</td>
                <td>{growth}</td>
                <td>{cat}</td>
            </tr>'''
        sections.append(f'''
        <div class="section">
            <h2>🔥 热词增量 · 科技数码 <span class="badge">TOP15</span></h2>
            <table><thead><tr><th>#</th><th>热词</th><th>热度</th><th>笔记增量</th><th>增幅</th><th>分类</th></tr></thead>
            <tbody>{items}</tbody></table>
        </div>''')

    # 4. 话题增量
    rows = conn.execute("""
        SELECT rank, topic_name, heat_delta, view_delta, interact_delta, note_delta
        FROM xhs_topics
        WHERE import_date >= ?
        ORDER BY heat_delta DESC LIMIT 20
    """, (date_str,)).fetchall()

    if rows:
        items = ""
        for r in rows[:15]:
            rank, topic, heat, views, interact, notes = r
            items += f'''<tr>
                <td>{rank}</td>
                <td><strong>{topic}</strong></td>
                <td>+{heat}</td>
                <td>{fmt(views)}</td>
                <td>{fmt(interact)}</td>
                <td>+{notes}</td>
            </tr>'''
        sections.append(f'''
        <div class="section">
            <h2>💬 话题增量榜 <span class="badge">TOP15</span></h2>
            <table><thead><tr><th>#</th><th>话题</th><th>热度增量</th><th>浏览增量</th><th>互动增量</th><th>笔记增量</th></tr></thead>
            <tbody>{items}</tbody></table>
        </div>''')

    # 5. 商业笔记
    rows = conn.execute("""
        SELECT rank, title, brand_name, author_name, followers, likes, interactions, note_url
        FROM xhs_notes
        WHERE import_date >= ? AND sheet_type = 'commercial_notes'
        ORDER BY interactions DESC LIMIT 15
    """, (date_str,)).fetchall()

    if rows:
        items = ""
        for r in rows[:10]:
            rank, title, brand, author, fans, likes, interactions, url = r
            title = (title or "")[:40]
            url = url or "#"
            items += f'''<tr>
                <td>{rank}</td>
                <td><a href="{url}" target="_blank">{title}</a></td>
                <td>{brand}</td>
                <td>{author}</td>
                <td>{fmt(fans)}</td>
                <td>{fmt(likes)}</td>
                <td>{fmt(interactions)}</td>
            </tr>'''
        sections.append(f'''
        <div class="section">
            <h2>💼 商业笔记榜 <span class="badge">TOP10</span></h2>
            <table><thead><tr><th>#</th><th>标题</th><th>品牌</th><th>达人</th><th>粉丝</th><th>👍</th><th>互动</th></tr></thead>
            <tbody>{items}</tbody></table>
        </div>''')

    if not sections:
        print(f"  ⚠️ {date_str} 无数据")
        return None

    # 统计
    note_count = conn.execute("SELECT COUNT(*) FROM xhs_notes WHERE import_date >= ?", (date_str,)).fetchone()[0]
    hotword_count = conn.execute("SELECT COUNT(*) FROM xhs_hotwords WHERE import_date >= ?", (date_str,)).fetchone()[0]
    topic_count = conn.execute("SELECT COUNT(*) FROM xhs_topics WHERE import_date >= ?", (date_str,)).fetchone()[0]

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        date_cn = f"{dt.year}年{dt.month}月{dt.day}日 星期{weekdays[dt.weekday()]}"
    except:
        date_cn = date_str

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>千瓜小红书数据看板 · {date_str}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,sans-serif;background:#0f0f0f;color:#e8e4df;padding:1.5rem;line-height:1.5}}
.hdr{{text-align:center;padding:2rem 0 1rem}}
.hdr h1{{font-size:2rem;color:#FF2442}}
.hdr p{{color:#888;margin-top:0.4rem}}
.stats{{display:flex;justify-content:center;gap:2rem;padding:0.8rem;margin:0.8rem 0}}
.stat-v{{font-size:1.3rem;font-weight:bold;color:#FF2442}}
.stat-l{{font-size:0.75rem;color:#888}}
.section{{margin:2rem 0}}
.section h2{{font-size:1.2rem;color:#fff;margin-bottom:0.8rem;display:flex;align-items:center;gap:0.5rem}}
.badge{{font-size:0.7rem;background:#FF2442;color:#fff;padding:0.1rem 0.4rem;border-radius:8px;font-weight:normal}}
table{{width:100%;border-collapse:collapse;font-size:0.82rem}}
th{{background:#1a1a1a;color:#FF2442;padding:0.5rem 0.6rem;text-align:left;border-bottom:2px solid #333;position:sticky;top:0}}
td{{padding:0.4rem 0.6rem;border-bottom:1px solid #222}}
tr:hover{{background:#1a1a1a}}
a{{color:#e8e4df;text-decoration:none}}
a:hover{{color:#FF2442}}
.footer{{text-align:center;padding:2rem;color:#444;font-size:0.75rem}}
</style>
</head>
<body>
<div class="hdr">
    <h1>📊 千瓜小红书数据看板</h1>
    <p>{date_cn} · Intel芯鲜事运营</p>
</div>
<div class="stats">
    <div style="text-align:center"><div class="stat-v">{note_count}</div><div class="stat-l">笔记</div></div>
    <div style="text-align:center"><div class="stat-v">{hotword_count}</div><div class="stat-l">热词</div></div>
    <div style="text-align:center"><div class="stat-v">{topic_count}</div><div class="stat-l">话题</div></div>
</div>
{"".join(sections)}
<div class="footer">千瓜数据 · {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
</body>
</html>'''
    return html


# ─── 主流程 ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="千瓜数据解析入库+看板生成")
    parser.add_argument("path", nargs="?", help="文件或目录路径")
    parser.add_argument("--dashboard", action="store_true", help="解析后生成看板")
    parser.add_argument("--dashboard-only", action="store_true", help="仅生成看板")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    conn = init_db()

    if not args.dashboard_only:
        if not args.path:
            print("请指定文件或目录路径")
            sys.exit(1)

        path = Path(args.path)
        files = []
        if path.is_file():
            files = [path]
        elif path.is_dir():
            files = sorted(path.glob("*.xls")) + sorted(path.glob("*.xlsx"))

        if not files:
            print(f"未找到xls/xlsx文件: {args.path}")
            sys.exit(1)

        print(f"📥 解析 {len(files)} 个文件...")
        total = 0
        for f in files:
            inserted = ingest_file(conn, str(f))
            total += inserted
        print(f"\n✅ 共入库 {total} 条记录")

    if args.dashboard or args.dashboard_only:
        print(f"\n📊 生成看板 ({args.date})...")
        DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
        html = generate_dashboard(conn, args.date)
        if html:
            path = DASHBOARD_DIR / f"qiangua_dashboard_{args.date}.html"
            path.write_text(html, encoding="utf-8")
            print(f"  ✓ {path}")
        else:
            print(f"  ⚠️ 无数据可生成")

    conn.close()


if __name__ == "__main__":
    main()
