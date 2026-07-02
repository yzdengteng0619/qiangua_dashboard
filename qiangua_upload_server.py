#!/usr/bin/env python3
"""
芯鲜事千瓜数据服务 v3 — 4层Pipeline分析引擎
============================================
上传 → 解析入库 → 4层LLM分析 → 看板生成

Pipeline架构:
  Layer 1: 热词+话题聚类（一次LLM）
  Layer 2: 聚类深度分析（一次LLM）
  Layer 3: 爆款笔记分析（一次LLM）
  Layer 4: 选题推荐（一次LLM）

分析完成后自动生成HTML看板。
上传页面实时展示进度。

Usage:
    python3 qiangua_upload_server.py --port 8090
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tarfile
import time
import threading
import zipfile
import gzip
import shutil
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:
    import pandas as pd
except ImportError:
    print("缺少 pandas: pip3 install pandas xlrd")
    sys.exit(1)

try:
    import requests as http_requests
except ImportError:
    http_requests = None

# ─── 配置 ─────────────────────────────────────────────────────────────────────
UPLOAD_DIR = Path.home() / "clawd" / "qiangua_uploads"
SCRIPT_DIR = Path.home() / "clawd" / "scripts"
DASHBOARD_DIR = Path.home() / "clawd" / "xhs_hot_reports"
DB_PATH = Path.home() / "clawd" / "knowledge" / "qiangua_xhs.db"
MINIMAX_KEY_FILE = Path.home() / ".minimax_key"
MINIMAX_API_URL = "https://api.minimaxi.com/v1/chat/completions"

# SSE事件存储
sse_events = {}  # task_id -> list of events
task_run_ids = {}  # task_id -> analysis_runs.id


def parse_date_from_path(path):
    parsed = urlparse(path)
    qs_date = parse_qs(parsed.query).get("date", [None])[0]
    if qs_date:
        return qs_date
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[0] in {"dashboard", "insights"}:
        return parts[1]
    return datetime.now().strftime("%Y-%m-%d")


def is_upload_page_path(path):
    parsed = urlparse(path)
    return parsed.path in {"/", "/index.html", "/upload"}


def update_task_run(run_id, status=None, current_stage=None, total_rows=None, error=None, finish=False):
    if not run_id:
        return
    try:
        import db

        conn = db.init_db(DB_PATH)
        if finish:
            db.finish_analysis_run(conn, run_id, status or "done", error=error)
        else:
            db.update_analysis_run(
                conn,
                run_id,
                status=status,
                current_stage=current_stage,
                total_rows=total_rows,
                error=error,
            )
        conn.close()
    except Exception as exc:
        print(f"[RUN STATUS] update failed: {exc}")

# ─── 数据库初始化 ─────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
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
    conn.commit()
    return conn

# ─── 文件类型识别 ──────────────────────────────────────────────────────────────
def detect_sheet_type(filename):
    fn = filename.lower()
    if "实时笔记榜单" in fn and "低粉" not in fn and "6小时" not in fn:
        return "realtime_notes"
    elif "实时笔记榜单" in fn and "6小时" in fn:
        return "realtime_notes_6h"
    elif "低粉笔记榜单" in fn:
        return "low_fan_notes"
    elif "商业笔记榜单" in fn:
        return "commercial_notes"
    elif "热词增量榜" in fn:
        return "hotwords_delta"
    elif "热词总量榜" in fn:
        return "hotwords_total"
    elif "热门话题增量榜" in fn:
        return "topics_delta"
    elif "热门话题总量榜" in fn:
        return "topics_total"
    elif "流量扶持榜" in fn:
        return "traffic_boost"
    return "unknown"

# ─── 归档解压 ──────────────────────────────────────────────────────────────────
ARCHIVE_EXTS = ('.xls', '.xlsx')
def is_excel(name):
    return any(name.endswith(ext) for ext in ARCHIVE_EXTS)

def extract_archive(archive_path, dest_dir):
    fn = os.path.basename(archive_path)
    extracted = []
    try:
        if fn.endswith('.tar'):
            with tarfile.open(str(archive_path)) as tar:
                for m in tar.getmembers():
                    if m.isfile() and is_excel(m.name):
                        m.name = os.path.basename(m.name)
                        tar.extract(m, str(dest_dir))
                        extracted.append(m.name)
        elif fn.endswith(('.tar.gz', '.tgz')):
            with tarfile.open(str(archive_path), 'r:gz') as tar:
                for m in tar.getmembers():
                    if m.isfile() and is_excel(m.name):
                        m.name = os.path.basename(m.name)
                        tar.extract(m, str(dest_dir))
                        extracted.append(m.name)
        elif fn.endswith('.zip'):
            with zipfile.ZipFile(str(archive_path)) as zf:
                for info in zf.infolist():
                    if not info.is_dir() and is_excel(info.filename):
                        info.filename = os.path.basename(info.filename)
                        zf.extract(info, str(dest_dir))
                        extracted.append(info.filename)
        elif fn.endswith('.gz') and not fn.endswith('.tar.gz'):
            base = fn[:-3]
            if is_excel(base):
                with gzip.open(str(archive_path), 'rb') as gz_in:
                    with open(str(dest_dir / base), 'wb') as f_out:
                        shutil.copyfileobj(gz_in, f_out)
                extracted.append(base)
    except Exception as e:
        print(f"[ARCHIVE ERROR] {fn}: {e}")
    return extracted

# ─── 数据解析入库 ──────────────────────────────────────────────────────────────
def safe_int(v):
    if pd.isna(v): return 0
    s = str(v).replace(",", "").replace("万", "0000").replace("+", "")
    try: return int(float(s))
    except: return 0


REQUIRED_COLUMNS = {
    "realtime_notes": ["排名", "笔记标题", "笔记链接", "互动量"],
    "realtime_notes_6h": ["排名", "笔记标题", "笔记链接", "互动量"],
    "low_fan_notes": ["排名", "笔记标题", "笔记链接", "互动量"],
    "commercial_notes": ["排名", "笔记标题", "笔记链接", "互动量"],
    "traffic_boost": ["排名", "笔记标题", "笔记链接", "互动量"],
    "hotwords_delta": ["排名", "热搜词名称"],
    "hotwords_total": ["排名", "热搜词名称"],
    "topics_delta": ["排名", "话题名称"],
    "topics_total": ["排名", "话题名称"],
}


def validate_upload_file(filepath):
    filename = os.path.basename(filepath)
    sheet_type = detect_sheet_type(filename)
    result = {
        "ok": False,
        "filename": filename,
        "sheet_type": sheet_type,
        "row_count": 0,
        "errors": [],
    }
    if sheet_type == "unknown":
        result["errors"].append(f"未识别的千瓜文件类型: {filename}")
        return result
    try:
        df = pd.read_excel(filepath, nrows=5)
    except Exception as exc:
        result["errors"].append(f"Excel 读取失败: {exc}")
        return result
    if df.empty:
        result["errors"].append("Excel 内容为空")
        return result
    required = REQUIRED_COLUMNS.get(sheet_type, [])
    missing = [column for column in required if column not in df.columns]
    if missing:
        result["errors"].append(f"缺少必要字段: {', '.join(missing)}")
        return result
    result["ok"] = True
    result["row_count"] = len(df.index)
    return result

def ingest_file(conn, filepath):
    filename = os.path.basename(filepath)
    sheet_type = detect_sheet_type(filename)
    import_date = datetime.now().strftime("%Y-%m-%d")
    if sheet_type == "unknown": return 0, sheet_type
    try:
        df = pd.read_excel(filepath)
    except: return 0, sheet_type

    inserted = 0
    if sheet_type in ("realtime_notes", "realtime_notes_6h", "low_fan_notes", "commercial_notes", "traffic_boost"):
        for _, row in df.iterrows():
            try:
                conn.execute("""INSERT OR IGNORE INTO xhs_notes
                    (rank,publish_time,title,is_brand_partner,is_commercial,is_promoted,
                     note_type,note_form,brand_name,note_url,tags,interactions,likes,
                     collects,comments,shares,author_name,followers,xhs_level,author_attr,
                     region,author_url,qiangua_url,file_source,sheet_type,import_date)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (int(row.get("排名",0) or 0), str(row.get("笔记发布时间","") or ""),
                     str(row.get("笔记标题","") or "")[:500],
                     str(row.get("是否品牌合作人","") or ""), str(row.get("是否商业笔记","") or ""),
                     str(row.get("是否推广笔记","") or ""), str(row.get("笔记类型","") or ""),
                     str(row.get("笔记形式","") or ""), str(row.get("报备合作品牌","") or ""),
                     str(row.get("笔记链接","") or ""), str(row.get("笔记标签","") or ""),
                     safe_int(row.get("互动量")), safe_int(row.get("点赞")),
                     safe_int(row.get("收藏")), safe_int(row.get("评论")),
                     safe_int(row.get("分享")), str(row.get("达人昵称","") or ""),
                     safe_int(row.get("粉丝数")), str(row.get("红薯等级","") or ""),
                     str(row.get("达人属性","") or ""), str(row.get("地域","") or ""),
                     str(row.get("达人小红书主页地址","") or ""),
                     str(row.get("达人千瓜主页地址","") or ""),
                     filename, sheet_type, import_date))
                inserted += 1
            except sqlite3.IntegrityError: pass
    elif sheet_type in ("hotwords_delta", "hotwords_total"):
        for _, row in df.iterrows():
            word = str(row.get("热搜词名称","") or "")
            if not word or word == "nan": continue
            try:
                conn.execute("""INSERT OR IGNORE INTO xhs_hotwords
                    (rank,word,heat_value,current_notes,prev_notes,note_delta,growth_rate,
                     current_commercial,prev_commercial,commercial_delta,commercial_growth,
                     category,file_source,import_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (int(row.get("排名",0) or 0), word, safe_int(row.get("当前热度值")),
                     safe_int(row.get("当前周期笔记数")), safe_int(row.get("上一周期笔记数")),
                     safe_int(row.get("相关笔记增量")), str(row.get("增幅","") or ""),
                     safe_int(row.get("当前周期商业笔记数")), safe_int(row.get("上一周期商业笔记数")),
                     safe_int(row.get("商业笔记增量")), str(row.get("商业笔记增幅","") or ""),
                     str(row.get("所属分类","") or ""), filename, import_date))
                inserted += 1
            except sqlite3.IntegrityError: pass
    elif sheet_type in ("topics_delta", "topics_total"):
        for _, row in df.iterrows():
            topic = str(row.get("话题名称","") or "")
            if not topic or topic == "nan": continue
            try:
                conn.execute("""INSERT OR IGNORE INTO xhs_topics
                    (rank,topic_name,topic_intro,launch_time,heat_delta,view_delta,
                     interact_delta,note_delta,file_source,import_date)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (int(row.get("排名",0) or 0), topic,
                     str(row.get("话题简介","") or ""), str(row.get("上线时间","") or ""),
                     safe_int(row.get("热度增量")), safe_int(row.get("浏览增量")),
                     safe_int(row.get("互动增量")), safe_int(row.get("笔记增量")),
                     filename, import_date))
                inserted += 1
            except sqlite3.IntegrityError: pass
    conn.commit()
    return inserted, sheet_type

# ─── LLM调用 ──────────────────────────────────────────────────────────────────
def get_minimax_key():
    if MINIMAX_KEY_FILE.exists():
        return MINIMAX_KEY_FILE.read_text().strip()
    return os.environ.get("MINIMAX_API_KEY", "")

def llm_analyze(prompt, max_retries=2):
    """调用MiniMax M3做分析，返回解析后的JSON"""
    if http_requests is None:
        import requests as _req
        _http = _req
    else:
        _http = http_requests

    key = get_minimax_key()
    if not key:
        return {"error": "No MiniMax API key"}

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    payload = {
        "model": "MiniMax-Text-01",
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 8192,
        "temperature": 0.3,
    }

    for attempt in range(max_retries + 1):
        try:
            resp = _http.post(MINIMAX_API_URL, json=payload, headers=headers, timeout=180)
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                print(f"  [LLM] 空响应, attempt={attempt}")
                if attempt < max_retries:
                    time.sleep(5)
                continue
            # 解析JSON
            return _parse_json_from_llm(content)
        except Exception as e:
            print(f"  [LLM] 错误: {e}, attempt={attempt}")
            if attempt < max_retries:
                time.sleep(5)
    return {"error": "LLM调用失败，多次重试后放弃"}

def _parse_json_from_llm(content):
    """从LLM响应中提取JSON"""
    # 尝试提取```json ... ```
    if "```json" in content:
        json_str = content.split("```json")[1].split("```")[0].strip()
        try: return json.loads(json_str)
        except: pass
    # 尝试提取``` ... ```
    if "```" in content:
        parts = content.split("```")
        if len(parts) >= 2:
            json_str = parts[1].strip()
            if json_str.startswith("json"):
                json_str = json_str[4:].strip()
            try: return json.loads(json_str)
            except: pass
    # 尝试直接解析
    try: return json.loads(content)
    except: pass
    # 返回原始内容
    return {"raw": content}

# ─── 数据构建辅助 ──────────────────────────────────────────────────────────────
def _build_hotword_data(conn, ds, limit=80):
    """构建热词分析数据"""
    rows = conn.execute("""
        SELECT word, heat_value, note_delta, growth_rate, category, file_source,
               current_notes, prev_notes
        FROM xhs_hotwords WHERE import_date >= ?
        ORDER BY note_delta DESC LIMIT ?
    """, (ds, limit)).fetchall()
    lines = []
    for r in rows:
        cat = r[4] or "全站"
        lines.append(f"{r[0]}: 热度{r[1]}, 笔记增量+{r[2]}, 增幅{r[3]}, 分类={cat}, 周期笔记数:{r[6]}/{r[7]}")
    return "\n".join(lines)

def _build_topic_data(conn, ds, limit=80):
    """构建话题分析数据"""
    rows = conn.execute("""
        SELECT topic_name, heat_delta, view_delta, interact_delta, note_delta, file_source, topic_intro
        FROM xhs_topics WHERE import_date >= ?
        ORDER BY view_delta DESC LIMIT ?
    """, (ds, limit)).fetchall()
    lines = []
    for r in rows:
        # 从file_source推断分类
        fs = r[5] or ""
        cat = "全站"
        lines.append(f"{r[0]}: 热度+{r[1]}, 浏览+{r[2]}, 互动+{r[3]}, 笔记+{r[4]}, 简介:{r[6][:60] if r[6] else '无'}")
    return "\n".join(lines)

def _build_notes_data_all(conn, ds):
    """构建全部笔记数据（不按file_source过滤）"""
    # 实时热门笔记
    high = conn.execute("""
        SELECT title, author_name, followers, likes, collects, comments, shares, interactions,
               note_form, note_type, note_url, author_attr, region
        FROM xhs_notes WHERE import_date >= ? AND sheet_type IN ('realtime_notes','realtime_notes_6h')
        ORDER BY interactions DESC LIMIT 40
    """, (ds,)).fetchall()
    high_lines = []
    for r in high:
        high_lines.append(f"[高互动] {r[0]} | 作者:{r[1]} 粉:{r[2]} 赞:{r[3]} 藏:{r[4]} 评:{r[5]} 转:{r[6]} 互动:{r[7]} 形式:{r[8]} 类型:{r[9]} 链接:{r[10]}")

    # 低粉爆款
    low = conn.execute("""
        SELECT title, author_name, followers, likes, collects, comments, interactions,
               note_form, note_type, note_url, author_attr
        FROM xhs_notes WHERE import_date >= ? AND sheet_type = 'low_fan_notes'
        ORDER BY interactions DESC LIMIT 30
    """, (ds,)).fetchall()
    low_lines = []
    for r in low:
        low_lines.append(f"[低粉爆款] {r[0]} | 作者:{r[1]} 粉:{r[2]} 赞:{r[3]} 藏:{r[4]} 评:{r[5]} 互动:{r[6]} 形式:{r[7]} 类型:{r[8]} 链接:{r[9]}")

    return "\n".join(high_lines), "\n".join(low_lines)

# ─── 4层Pipeline分析 ──────────────────────────────────────────────────────────
def run_analysis_pipeline(task_id, date_str, run_id=None):
    """
    4层Pipeline分析：
    L1: 热词+话题聚类
    L2: 聚类深度分析
    L3: 爆款笔记分析
    L4: 选题推荐
    """
    # 导入prompt模板
    sys.path.insert(0, str(SCRIPT_DIR))
    from intel_brand_knowledge import (
        L1_CLUSTER_PROMPT,
        L2_DEEP_ANALYSIS_PROMPT,
        L3_NOTES_ANALYSIS_PROMPT,
        L4_TOPIC_RECOMMENDATIONS_PROMPT,
    )

    sse_events[task_id] = []

    def emit(stage, msg, data=None):
        event = {"stage": stage, "msg": msg, "time": datetime.now().strftime("%H:%M:%S")}
        if data: event["data"] = data
        sse_events[task_id].append(event)
        print(f"  [{stage}] {msg}")

    emit("分析启动", f"开始4层Pipeline分析 {date_str} ...")

    conn = init_db()
    update_task_run(run_id, status="running", current_stage="准备数据")

    # 准备数据
    emit("数据准备", "构建热词+话题数据...")
    hotword_data = _build_hotword_data(conn, date_str)
    topic_data = _build_topic_data(conn, date_str)
    high_notes, low_notes = _build_notes_data_all(conn, date_str)

    emit("数据准备", f"热词{len(hotword_data.splitlines())}条, 话题{len(topic_data.splitlines())}条, 笔记{len(high_notes.splitlines())}+{len(low_notes.splitlines())}条")

    # ── Layer 1: 聚类 ──
    update_task_run(run_id, status="running", current_stage="L1 趋势聚类")
    emit("Layer 1/4", "热词+话题主题聚类分析中...")
    l1_prompt = L1_CLUSTER_PROMPT.format(hotword_data=hotword_data, topic_data=topic_data)
    l1_result = llm_analyze(l1_prompt)
    emit("Layer 1/4", "聚类完成", l1_result)

    # ── Layer 2: 深度分析 ──
    update_task_run(run_id, status="running", current_stage="L2 深度机会")
    emit("Layer 2/4", "聚类深度分析（趋势+借势+机会）...")
    l1_json_str = json.dumps(l1_result, ensure_ascii=False)
    l2_prompt = L2_DEEP_ANALYSIS_PROMPT.format(
        l1_clusters_json=l1_json_str,
        hotword_data=hotword_data,
        topic_data=topic_data,
    )
    l2_result = llm_analyze(l2_prompt)
    emit("Layer 2/4", "深度分析完成", l2_result)

    # ── Layer 3: 爆款分析 ──
    update_task_run(run_id, status="running", current_stage="L3 爆款拆解")
    emit("Layer 3/4", "爆款笔记分析（分类+归组+原因）...")
    l3_prompt = L3_NOTES_ANALYSIS_PROMPT.format(
        l1_clusters_json=l1_json_str,
        high_engagement_notes=high_notes,
        low_fan_notes=low_notes,
    )
    l3_result = llm_analyze(l3_prompt)
    emit("Layer 3/4", "爆款分析完成", l3_result)

    # ── Layer 4: 选题推荐 ──
    update_task_run(run_id, status="running", current_stage="L4 选题推荐")
    emit("Layer 4/4", "综合选题推荐（基于L1-L3）...")
    l2_json_str = json.dumps(l2_result, ensure_ascii=False)
    l3_json_str = json.dumps(l3_result, ensure_ascii=False)
    l4_prompt = L4_TOPIC_RECOMMENDATIONS_PROMPT.format(
        l1_clusters_json=l1_json_str,
        l2_analysis_json=l2_json_str,
        l3_analysis_json=l3_json_str,
    )
    l4_result = llm_analyze(l4_prompt)
    emit("Layer 4/4", "选题推荐完成", l4_result)

    # ── 保存所有结果 ──
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    layers = [
        ("L1_clusters", l1_result),
        ("L2_deep_analysis", l2_result),
        ("L3_notes_analysis", l3_result),
        ("L4_recommendations", l4_result),
    ]
    for atype, adata in layers:
        try:
            conn.execute(
                "INSERT OR REPLACE INTO xhs_analysis (analysis_date,analysis_type,content,model,created_at) VALUES (?,?,?,?,?)",
                (date_str, atype, json.dumps(adata, ensure_ascii=False), "minimax-m3", now)
            )
        except: pass

    # 保存原始笔记数据
    raw_notes = conn.execute("""
        SELECT title, author_name, followers, likes, collects, comments, shares, interactions,
               note_form, note_type, note_url, author_attr, region, sheet_type
        FROM xhs_notes WHERE import_date = ?
        ORDER BY interactions DESC LIMIT 60
    """, (date_str,)).fetchall()
    raw_data = [dict(zip(["title","author","fans","likes","collects","comments","shares","interactions","form","type","url","attr","region","sheet_type"], r)) for r in raw_notes]
    try:
        conn.execute(
            "INSERT OR REPLACE INTO xhs_analysis (analysis_date,analysis_type,content,model,created_at) VALUES (?,?,?,?,?)",
            (date_str, "raw_notes", json.dumps(raw_data, ensure_ascii=False), "database", now)
        )
    except: pass

    artifact_run_id = run_id
    conn.commit()

    try:
        import analysis_artifacts
        import db

        artifact_conn = db.init_db(DB_PATH)
        if artifact_run_id is None:
            artifact_run_id = db.create_analysis_run(artifact_conn, date_str, model="MiniMax-Text-01")
        db.save_artifact(artifact_conn, artifact_run_id, "l1_clusters", l1_result)
        db.save_artifact(artifact_conn, artifact_run_id, "l2_opportunities", l2_result)
        db.save_artifact(artifact_conn, artifact_run_id, "l3_note_patterns", l3_result)
        db.save_artifact(artifact_conn, artifact_run_id, "l4_recommendations", l4_result)
        db.save_artifact(
            artifact_conn,
            artifact_run_id,
            "daily_report",
            analysis_artifacts.build_daily_report(l1_result, l2_result, l3_result, l4_result),
        )
        db.update_analysis_run(artifact_conn, artifact_run_id, current_stage="生成页面")
        artifact_conn.close()
    except Exception as e:
        emit("洞察日报", f"结构化日报保存失败: {e}")

    conn.commit()
    conn.close()

    emit("分析完成", "✅ 4层Pipeline分析全部完成", {
        "L1": l1_result, "L2": l2_result, "L3": l3_result, "L4": l4_result
    })

    # 生成看板（Signal Style）
    emit("看板生成", "正在生成HTML看板（Signal Style）...")
    try:
        from dashboard_generator import generate_dashboard
        conn2 = init_db()
        generate_dashboard(date_str, l1_result, l2_result, l3_result, l4_result, conn2)
        conn2.close()
        update_task_run(artifact_run_id, current_stage="已完成")
        update_task_run(artifact_run_id, status="done", finish=True)
        emit("看板就绪", f"✅ 看板已生成", {"url": f"/dashboard/{date_str}"})
    except Exception as e:
        import traceback
        update_task_run(artifact_run_id, status="failed", current_stage="生成页面失败", error=str(e))
        update_task_run(artifact_run_id, status="failed", error=str(e), finish=True)
        emit("看板错误", f"看板生成失败: {e}")
        traceback.print_exc()
        emit("看板就绪", "⚠️ 分析完成但看板生成失败", {"error": str(e)})

    return {"L1": l1_result, "L2": l2_result, "L3": l3_result, "L4": l4_result}

# ─── 看板生成（v3临时版，后续重构） ───────────────────────────────────────────
def fmt(n):
    if n is None: return "0"
    if n >= 10000: return f"{n/10000:.1f}w"
    if n >= 1000: return f"{n/1000:.1f}k"
    return str(n)

def generate_dashboard_v3(date_str, l1, l2, l3, l4):
    """基于4层Pipeline结果的HTML看板"""
    conn = init_db()
    sections = []

    # 统计
    note_count = conn.execute("SELECT COUNT(*) FROM xhs_notes WHERE import_date >= ?", (date_str,)).fetchone()[0]
    hw_count = conn.execute("SELECT COUNT(*) FROM xhs_hotwords WHERE import_date >= ?", (date_str,)).fetchone()[0]
    tp_count = conn.execute("SELECT COUNT(*) FROM xhs_topics WHERE import_date >= ?", (date_str,)).fetchone()[0]

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        date_cn = f"{dt.year}年{dt.month}月{dt.day}日 星期{weekdays[dt.weekday()]}"
    except: date_cn = date_str

    # ── Layer 4: 选题推荐（置顶） ──
    recs = l4.get("recommendations", []) if isinstance(l4, dict) else []
    if recs:
        recs_html = ""
        for i, r in enumerate(recs[:5], 1):
            topic = r.get("topic_title", "")
            derivation = r.get("derivation", "")
            ctype = r.get("content_type", "")
            angle = r.get("intel_angle", "")
            hook = r.get("hook_suggestion", "")
            timing = r.get("timing", "")
            refs = r.get("reference_notes", [])
            refs_html = "".join([f'<a href="{n.get("url","#")}" target="_blank" style="color:#FF2442;font-size:0.8rem">→ {n.get("title","")[:30]}</a><br>' for n in refs[:2]])
            data_s = r.get("data_support", "")
            recs_html += f'''
            <div class="rec-card">
                <div class="rec-num">{i}</div>
                <div class="rec-content">
                    <h4>{topic}</h4>
                    <p class="rec-derive">📊 {derivation}</p>
                    <p class="rec-angle">💡 Intel角度：{angle}</p>
                    <p>📱 形式：{ctype} | ⏰ {timing}</p>
                    <p class="rec-hook">🪝 钩子：{hook}</p>
                    <p style="font-size:0.8rem;color:#888">📈 {data_s}</p>
                    {refs_html}
                </div>
            </div>'''
        weekly = l4.get("weekly_theme", "") if isinstance(l4, dict) else ""
        sections.append(f'''
        <div class="section highlight">
            <h2>🎯 选题推荐</h2>
            {f'<p style="color:#888;margin-bottom:1rem">本周主题：{weekly}</p>' if weekly else ''}
            <div class="rec-grid">{recs_html}</div>
        </div>''')

    # ── Layer 1: 聚类结果 ──
    clusters = l1.get("clusters", []) if isinstance(l1, dict) else []
    if clusters:
        cl_html = ""
        for cl in clusters:
            cname = cl.get("cluster_name", "")
            hws = cl.get("hotwords", [])
            tps = cl.get("topics", [])
            rel = cl.get("intel_relevance", "")
            reason = cl.get("relevance_reason", "")
            trend = cl.get("trend_direction", "")
            vd = cl.get("total_view_delta", 0)
            id_ = cl.get("total_interact_delta", 0)
            rel_class = {"高": "rel-high", "中": "rel-mid", "低": "rel-low", "无关": "rel-low"}.get(rel, "")
            hw_tags = " ".join([f'<span class="tag">{w}</span>' for w in hws[:10]])
            tp_tags = " ".join([f'<span class="tag topic">{t}</span>' for t in tps[:8]])
            cl_html += f'''
            <div class="cluster-card">
                <h3>{cname} <span class="rel-badge {rel_class}">Intel {rel}</span> <span class="trend">{trend}</span></h3>
                <p style="font-size:0.85rem;color:#555;margin:0.3rem 0">{reason}</p>
                <div style="margin-top:0.5rem"><strong style="font-size:0.8rem;color:#888">热词：</strong><div class="tag-cloud">{hw_tags}</div></div>
                <div style="margin-top:0.3rem"><strong style="font-size:0.8rem;color:#888">话题：</strong><div class="tag-cloud">{tp_tags}</div></div>
                <p style="font-size:0.8rem;color:#888;margin-top:0.3rem">浏览+{fmt(vd)} 互动+{fmt(id_)}</p>
            </div>'''
        sections.append(f'''
        <div class="section">
            <h2>📊 平台趋势总览 · 主题聚类</h2>
            {cl_html}
        </div>''')

    # ── Layer 2: 深度分析 ──
    cluster_analyses = l2.get("cluster_analyses", []) if isinstance(l2, dict) else []
    if cluster_analyses:
        la_html = ""
        for ca in cluster_analyses:
            cname = ca.get("cluster_name", "")
            trend_a = ca.get("trend_analysis", "")
            ideas = ca.get("cross_category_ideas", [])
            opps = ca.get("hotword_opportunities", [])
            actions = ca.get("action_items", [])
            ideas_html = "".join([f'<li><strong>{i.get("angle","")}</strong>：{i.get("content_suggestion","")} <em>({i.get("reference_data","")})</em></li>' for i in ideas[:3]])
            opps_html = "".join([f'<span class="tag">{o.get("keyword","")}</span> ' for o in opps[:5]])
            actions_html = "".join([f"<li>{a}</li>" for a in actions[:3]])
            la_html += f'''
            <div class="cluster-card deep">
                <h3>{cname}</h3>
                <p style="font-size:0.9rem;color:#333;margin:0.5rem 0">{trend_a}</p>
                <div style="margin-top:0.5rem">
                    <strong style="font-size:0.85rem">🔗 跨品类借势：</strong>
                    <ul style="font-size:0.85rem;color:#555;padding-left:1.2rem">{ideas_html}</ul>
                </div>
                <div style="margin-top:0.5rem">
                    <strong style="font-size:0.85rem">🔥 热词机会：</strong>
                    <div class="tag-cloud" style="margin-top:0.3rem">{opps_html}</div>
                </div>
                <div style="margin-top:0.5rem">
                    <strong style="font-size:0.85rem">📋 行动建议：</strong>
                    <ul style="font-size:0.85rem;color:#FF2442;padding-left:1.2rem">{actions_html}</ul>
                </div>
            </div>'''
        priority_hw = l2.get("priority_hotwords", []) if isinstance(l2, dict) else []
        p_html = ""
        if priority_hw:
            p_items = "".join([f'<li><strong>{h.get("keyword","")}</strong>：{h.get("reason","")} <em>({h.get("deadline","")})</em></li>' for h in priority_hw[:3]])
            p_html = f'<div style="margin-top:1rem;padding:0.8rem;background:#fff5f5;border-radius:8px"><strong>⚡ 优先热词：</strong><ul style="padding-left:1.2rem;font-size:0.85rem">{p_items}</ul></div>'
        sections.append(f'''
        <div class="section">
            <h2>🔍 热词趋势深度分析</h2>
            {la_html}
            {p_html}
        </div>''')

    # ── Layer 3: 爆款分析 ──
    l3_clusters = l3.get("clusters", []) if isinstance(l3, dict) else []
    l3_trends = l3.get("content_trends", []) if isinstance(l3, dict) else []
    l3_patterns = l3.get("replicable_patterns", []) if isinstance(l3, dict) else []
    fmt_dist = l3.get("format_distribution", {}) if isinstance(l3, dict) else {}

    if l3_clusters:
        nc_html = ""
        for nc in l3_clusters:
            cname = nc.get("cluster_name", "")
            notes = nc.get("notes", [])
            top_analyses = nc.get("top_analysis", [])
            notes_html = ""
            for n in notes[:6]:
                url = n.get("url", "#")
                title = (n.get("title", "") or "")[:35]
                form = n.get("form", "")
                interactions = n.get("interactions", 0)
                author = n.get("author", "")
                fans = n.get("fans", 0)
                notes_html += f'<a href="{url}" target="_blank" style="display:block;padding:0.3rem 0;border-bottom:1px solid #f0f0f0;font-size:0.85rem;color:#333;text-decoration:none">📝 {title} <span style="color:#888">· {author}(粉{fmt(fans)}) 👍{fmt(interactions)} [{form}]</span></a>'
            analysis_html = ""
            for a in top_analyses[:3]:
                analysis_html += f'''
                <div style="padding:0.5rem;background:#f8f9fa;border-radius:6px;margin:0.3rem 0;font-size:0.85rem">
                    <strong>{a.get("title","")[:40]}</strong><br>
                    <span style="color:#dc2626">为什么火：</span>{a.get("why_hot","")}<br>
                    <span style="color:#16a34a">可复制：</span>{a.get("replicable","")}<br>
                    <span style="color:#FF2442">Intel怎么做：</span>{a.get("intel_howto","")}
                </div>'''
            nc_html += f'''
            <div class="cluster-card notes">
                <h3>{cname} <span class="badge-count">{len(notes)}篇</span></h3>
                {notes_html}
                {f'<div style="margin-top:0.5rem"><strong>爆款分析：</strong>{analysis_html}</div>' if analysis_html else ''}
            </div>'''

        fmt_insight = fmt_dist.get("insight", "")
        fmt_info = f'<p style="color:#888;margin-bottom:0.5rem">图文 {fmt_dist.get("image_count",0)}篇 · 视频 {fmt_dist.get("video_count",0)}篇 — {fmt_insight}</p>' if fmt_dist else ""

        sections.append(f'''
        <div class="section">
            <h2>📝 爆款笔记分析 · 按聚类归组</h2>
            {fmt_info}
            {nc_html}
        </div>''')

    if l3_trends:
        trends_html = "".join([f'<li><strong>{t.get("trend","")}</strong>：<span style="color:#555">{t.get("evidence","")}</span> → <span style="color:#FF2442">{t.get("intel_action","")}</span></li>' for t in l3_trends[:5]])
        sections.append(f'''
        <div class="section">
            <h2>📈 内容趋势</h2>
            <ul style="font-size:0.9rem;padding-left:1.2rem">{trends_html}</ul>
        </div>''')

    if l3_patterns:
        p_html = ""
        for p in l3_patterns[:3]:
            notes_ex = "、".join([f'"{n[:20]}"' for n in p.get("example_notes", [])[:2]])
            p_html += f'''
            <div style="padding:0.6rem;background:#f8f9fa;border-radius:6px;margin:0.3rem 0">
                <strong>{p.get("pattern","")}</strong> <span style="color:#888;font-size:0.8rem">例：{notes_ex}</span><br>
                <span style="color:#FF2442;font-size:0.85rem">Intel模板：{p.get("intel_template","")}</span>
            </div>'''
        sections.append(f'''
        <div class="section">
            <h2>♻️ 可复制内容模式</h2>
            {p_html}
        </div>''')

    # ── 原始数据（含链接） ──
    raw_row = conn.execute("SELECT content FROM xhs_analysis WHERE analysis_type='raw_notes' ORDER BY id DESC LIMIT 1").fetchone()
    if raw_row:
        try:
            raw_list = json.loads(raw_row[0])
            if raw_list:
                rows_html = ""
                for n in raw_list[:30]:
                    title = (n.get("title","") or "")[:35]
                    author = n.get("author","")
                    fans = fmt(n.get("fans",0))
                    likes = fmt(n.get("likes",0))
                    interactions = fmt(n.get("interactions",0))
                    form_val = n.get("form","")
                    url = n.get("url","#") or "#"
                    stype = n.get("sheet_type","")
                    tag = "低粉" if "low_fan" in stype else ""
                    rows_html += f'<tr><td><a href="{url}" target="_blank">{title}</a></td><td>{author}</td><td>{fans}</td><td>{likes}</td><td>{interactions}</td><td>{form_val}</td><td>{tag}</td></tr>'
                sections.append(f'''
                <div class="section">
                    <h2>📋 原始数据 · 全部笔记 <span class="badge-count">TOP30</span></h2>
                    <table class="data-table"><thead><tr><th>标题</th><th>达人</th><th>粉丝</th><th>👍</th><th>互动</th><th>形式</th><th>标签</th></tr></thead>
                    <tbody>{rows_html}</tbody></table>
                </div>''')
        except: pass

    conn.close()

    if not sections:
        sections.append('<div class="section"><p style="color:#888">暂无分析数据</p></div>')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>芯鲜事运营看板 · {date_str}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:#fafbfc;color:#1a1a1a;line-height:1.6}}
.container{{max-width:1100px;margin:0 auto;padding:1.5rem}}
.hdr{{text-align:center;padding:2rem 0 1rem;border-bottom:2px solid #FF2442;margin-bottom:1.5rem}}
.hdr h1{{font-size:1.8rem;color:#1a1a1a}}.hdr h1 span{{color:#FF2442}}.hdr p{{color:#888;margin-top:0.3rem;font-size:0.9rem}}
.stats{{display:flex;justify-content:center;gap:2.5rem;padding:1rem 0}}
.stat{{text-align:center}}.stat-v{{font-size:1.6rem;font-weight:700;color:#FF2442}}.stat-l{{font-size:0.75rem;color:#888}}
.section{{margin:2rem 0;background:#fff;border-radius:12px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,0.06)}}
.section.highlight{{border-left:4px solid #FF2442;background:#fff5f5}}
.section h2{{font-size:1.15rem;color:#1a1a1a;margin-bottom:1rem;padding-bottom:0.5rem;border-bottom:1px solid #f0f0f0}}
.rec-grid{{display:flex;flex-direction:column;gap:1rem}}
.rec-card{{display:flex;gap:1rem;padding:1rem;background:#f8f9fa;border-radius:8px;border:1px solid #eee}}
.rec-num{{width:36px;height:36px;background:#FF2442;color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:1.1rem;flex-shrink:0}}
.rec-content h4{{font-size:1rem;margin-bottom:0.3rem}}.rec-content p{{font-size:0.85rem;color:#555;margin:0.15rem 0}}
.rec-derive{{color:#8b5cf6}}.rec-angle{{color:#FF2442}}.rec-hook{{color:#059669}}
.cluster-card{{padding:1rem;background:#f8f9fa;border-radius:8px;margin:0.8rem 0;border-left:3px solid #FF2442}}
.cluster-card h3{{font-size:0.95rem;margin-bottom:0.3rem}}
.cluster-card.deep{{border-left-color:#8b5cf6}}
.cluster-card.notes{{border-left-color:#10b981}}
.trend{{color:#888;font-size:0.8rem}}
.tag-cloud{{display:flex;flex-wrap:wrap;gap:0.4rem;margin:0.3rem 0}}
.tag{{padding:0.2rem 0.6rem;border-radius:12px;font-size:0.8rem;background:#f3f4f6;color:#374151}}
.tag.topic{{background:#ede9fe;color:#7c3aed}}
.data-table{{width:100%;border-collapse:collapse;font-size:0.82rem}}
.data-table th{{background:#f8f9fa;color:#555;padding:0.5rem;text-align:left;font-weight:600;border-bottom:2px solid #eee}}
.data-table td{{padding:0.4rem 0.5rem;border-bottom:1px solid #f0f0f0;vertical-align:top}}
.data-table tr:hover{{background:#fafbfc}}
.rel-badge,.badge-count{{display:inline-block;padding:0.15rem 0.5rem;border-radius:4px;font-size:0.72rem;font-weight:600;margin-left:0.5rem}}
.rel-high{{background:#fef2f2;color:#dc2626}}.rel-mid{{background:#fffbeb;color:#d97706}}.rel-low{{background:#f0f9ff;color:#6b7280}}
.badge-count{{background:#f3f4f6;color:#6b7280}}
.footer{{text-align:center;padding:2rem;color:#aaa;font-size:0.8rem}}
</style>
</head>
<body>
<div class="container">
<div class="hdr">
    <h1>📱 <span>芯鲜事</span> 运营看板</h1>
    <p>{date_cn} · 千瓜数据 · 4层Pipeline AI分析</p>
</div>
<div class="stats">
    <div class="stat"><div class="stat-v">{note_count}</div><div class="stat-l">笔记</div></div>
    <div class="stat"><div class="stat-v">{hw_count}</div><div class="stat-l">热词</div></div>
    <div class="stat"><div class="stat-v">{tp_count}</div><div class="stat-l">话题</div></div>
</div>
{"".join(sections)}
<div class="footer">千瓜数据 · MiniMax M3 · 4层Pipeline分析 · {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>
</div>
</body>
</html>'''

    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    path = DASHBOARD_DIR / f"qiangua_dashboard_{date_str}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)

# ─── HTTP服务 ──────────────────────────────────────────────────────────────────
HTML_PAGE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>芯鲜事 · 千瓜数据上传</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC",sans-serif;background:#fafbfc;color:#1a1a1a;min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:2rem}
h1{font-size:1.8rem;margin-bottom:0.3rem}h1 span{color:#FF2442}
.sub{color:#888;margin-bottom:2rem;font-size:0.9rem}
.zone{width:100%;max-width:600px;border:2px dashed #ddd;border-radius:12px;padding:2.5rem;text-align:center;cursor:pointer;transition:all .3s;background:#fff}
.zone:hover,.zone.drag{border-color:#FF2442;background:#fff5f5}
.zone h2{font-size:1.1rem;margin-bottom:0.3rem}.zone p{color:#888;font-size:0.85rem}.zone input{display:none}
.btn{display:inline-block;margin-top:1rem;padding:.6rem 1.5rem;background:#FF2442;color:#fff;border:none;border-radius:8px;font-size:.95rem;cursor:pointer}
.btn:hover{background:#e01f3d}.btn:disabled{background:#ccc;cursor:not-allowed}
.progress{width:100%;max-width:600px;margin-top:1.5rem;display:none}
.progress-bar{height:4px;background:#eee;border-radius:2px;overflow:hidden;margin-bottom:1rem}
.progress-fill{height:100%;background:#FF2442;width:0;transition:width .5s}
.stages{font-size:.85rem}
.stage{padding:.4rem 0;display:flex;align-items:center;gap:.5rem}
.stage .icon{width:20px;text-align:center}.stage.active{color:#FF2442;font-weight:600}.stage.done{color:#22c55e}.stage.wait{color:#ccc}
.result{width:100%;max-width:600px;margin-top:1.5rem;display:none}
.files{width:100%;max-width:600px;margin-top:1rem}
.fi{display:flex;justify-content:space-between;padding:.4rem .6rem;background:#fff;border-radius:6px;margin-bottom:.3rem;font-size:.85rem;border:1px solid #eee}
.dash-link{display:inline-block;margin-top:1rem;padding:.5rem 1.2rem;background:#22c55e;color:#fff;text-decoration:none;border-radius:6px;font-size:.9rem}
</style>
</head>
<body>
<h1>📱 <span>芯鲜事</span> 数据上传</h1>
<p class="sub">上传千瓜数据 → 4层AI分析 → 运营看板</p>

<div class="zone" id="dz">
    <h2>📁 拖拽文件到这里</h2>
    <p>或点击选择（xls / xlsx / tar / zip / gz）</p>
    <input type="file" id="fi" multiple>
    <button class="btn" id="ub">上传并分析</button>
</div>

<div class="progress" id="pg">
    <div class="progress-bar"><div class="progress-fill" id="pf"></div></div>
    <div class="stages" id="stages">
        <div class="stage" id="s1"><span class="icon">⏳</span> 上传文件</div>
        <div class="stage" id="s2"><span class="icon">⏳</span> 解析入库</div>
        <div class="stage" id="s3"><span class="icon">⏳</span> L1 聚类分析</div>
        <div class="stage" id="s4"><span class="icon">⏳</span> L2 深度分析</div>
        <div class="stage" id="s5"><span class="icon">⏳</span> L3 爆款分析</div>
        <div class="stage" id="s6"><span class="icon">⏳</span> L4 选题推荐</div>
        <div class="stage" id="s7"><span class="icon">⏳</span> 生成看板</div>
    </div>
</div>

<div class="result" id="rs">
    <a class="dash-link" id="dl" href="#" target="_blank">📊 查看看板</a>
</div>

<div class="files" id="fl"></div>

<script>
const dz=document.getElementById('dz'),fi=document.getElementById('fi'),ub=document.getElementById('ub');
const pg=document.getElementById('pg'),pf=document.getElementById('pf'),rs=document.getElementById('rs'),dl=document.getElementById('dl'),fl=document.getElementById('fl');
let sel=[];
dz.addEventListener('click',()=>fi.click());
dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('drag')});
dz.addEventListener('dragleave',()=>dz.classList.remove('drag'));
dz.addEventListener('drop',e=>{e.preventDefault();dz.classList.remove('drag');hf(e.dataTransfer.files)});
fi.addEventListener('change',e=>hf(e.target.files));
function hf(files){
    sel=Array.from(files).filter(f=>{const n=f.name.toLowerCase();return n.endsWith('.xls')||n.endsWith('.xlsx')||n.endsWith('.tar')||n.endsWith('.tar.gz')||n.endsWith('.tgz')||n.endsWith('.zip')||n.endsWith('.gz')});
    if(!sel.length){alert('不支持的文件格式');return}
    fl.innerHTML=sel.map(f=>'<div class="fi"><span>'+f.name+'</span><span>'+(f.size/1024).toFixed(0)+'KB</span></div>').join('');
    ub.disabled=false;ub.textContent='上传 '+sel.length+' 个文件';
}
ub.addEventListener('click',doUpload);
async function doUpload(){
    if(!sel.length)return;
    ub.disabled=true;pg.style.display='block';rs.style.display='none';
    setStage(1,'active');
    const fd=new FormData();sel.forEach(f=>fd.append('files',f));
    try{
        const r=await fetch('/upload',{method:'POST',body:fd});
        const d=await r.json();
        if(d.ok){
            setStage(1,'done');setStage(2,'active');
            listenSSE(d.task_id);
        }else{alert('上传失败: '+d.message);ub.disabled=false}
    }catch(e){alert('上传失败: '+e.message);ub.disabled=false}
}
function listenSSE(taskId){
    const es=new EventSource('/progress/'+taskId);
    es.onmessage=function(e){
        const d=JSON.parse(e.data);
        if(d.stage){
            if(d.stage.includes('解析完成')){setStage(2,'done');setStage(3,'active')}
            if(d.stage.includes('Layer 1')){setStage(2,'done');setStage(3,'active');if(d.stage.includes('完成'))setStage(3,'done')}
            if(d.stage.includes('Layer 2')){setStage(3,'done');setStage(4,'active');if(d.stage.includes('完成'))setStage(4,'done')}
            if(d.stage.includes('Layer 3')){setStage(4,'done');setStage(5,'active');if(d.stage.includes('完成'))setStage(5,'done')}
            if(d.stage.includes('Layer 4')){setStage(5,'done');setStage(6,'active');if(d.stage.includes('完成'))setStage(6,'done')}
            if(d.stage.includes('看板就绪')){
                setStage(7,'done');es.close();
                pf.style.width='100%';
                if(d.data&&d.data.url){dl.href=d.data.url;rs.style.display='block'}
                ub.disabled=false;ub.textContent='再传一批';
            }
            if(d.stage.includes('分析完成')){setStage(6,'done');setStage(7,'active')}
        }
    };
    es.onerror=function(){es.close();ub.disabled=false};
}
function setStage(n,state){
    const el=document.getElementById('s'+n);if(!el)return;
    el.className='stage '+state;
    const icons={active:'🔄',done:'✅',wait:'⏳'};
    el.querySelector('.icon').textContent=icons[state]||'⏳';
    const pcts={1:8,2:15,3:25,4:40,5:55,6:70,7:95};
    if(state==='done')pf.style.width=pcts[n]+'%';
}
</script>
</body>
</html>'''


class UploadHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if is_upload_page_path(self.path):
            self.send_upload_page()
        elif self.path.startswith('/dashboard'):
            self.send_dashboard_page()
        elif self.path.startswith('/insights'):
            self.send_insights_page()
        elif self.path.startswith('/progress/'):
            task_id = self.path.split('/')[-1]
            self.handle_sse(task_id)
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        else:
            self.send_response(404)
            self.end_headers()

    def send_html(self, html):
        body = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_upload_page(self):
        import db
        import renderers
        conn = db.init_db(DB_PATH)
        recent_runs = db.recent_analysis_runs(conn)
        conn.close()
        self.send_html(renderers.render_upload_page(
            datetime.now().strftime("%Y-%m-%d"),
            recent_runs=recent_runs,
        ))

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
        report = (
            report_data.daily_report(conn, run[0])
            if run else {"headline": "暂无洞察日报", "key_points": [], "sections": []}
        )
        html = renderers.render_insights_page(
            date_str,
            report_data.insights_history(conn),
            report,
        )
        conn.close()
        self.send_html(html)

    def handle_sse(self, task_id):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        idx = 0
        while True:
            events = sse_events.get(task_id, [])
            while idx < len(events):
                evt = events[idx]
                data = json.dumps(evt, ensure_ascii=False)
                self.wfile.write(f"data: {data}\n\n".encode('utf-8'))
                self.wfile.flush()
                idx += 1
                if evt.get("stage") == "看板就绪":
                    return
            time.sleep(0.5)

    def do_POST(self):
        if self.path == '/upload':
            self.handle_upload()
        else:
            self.send_response(404)
            self.end_headers()

    def handle_upload(self):
        import cgi
        content_type = self.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
            self.send_json(False, '请使用 multipart/form-data 上传')
            return

        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
            environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': content_type})

        files = form['files']
        if not isinstance(files, list): files = [files]

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        saved = []
        for item in files:
            if item.filename:
                fn = os.path.basename(item.filename)
                raw_path = UPLOAD_DIR / fn
                with open(raw_path, 'wb') as f:
                    f.write(item.file.read())
                if fn.endswith(('.xls', '.xlsx')):
                    saved.append(fn)
                else:
                    extracted = extract_archive(raw_path, UPLOAD_DIR)
                    saved.extend(extracted)

        if not saved:
            self.send_json(False, '未找到有效的 xls/xlsx 文件')
            return

        task_id = f"task_{int(time.time()*1000)}"
        today = datetime.now().strftime("%Y-%m-%d")
        run_id = None
        try:
            import db

            run_conn = db.init_db(DB_PATH)
            run_id = db.create_analysis_run(run_conn, today, model="MiniMax-Text-01")
            db.update_analysis_run(run_conn, run_id, current_stage="等待解析")
            run_conn.close()
            task_run_ids[task_id] = run_id
        except Exception as exc:
            print(f"[RUN STATUS] create failed: {exc}")
        threading.Thread(target=self.run_pipeline, args=(task_id, saved, run_id), daemon=True).start()
        self.send_json(True, f'上传 {len(saved)} 个文件，开始处理', extra={"task_id": task_id, "run_id": run_id})

    def run_pipeline(self, task_id, files, run_id=None):
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            # Step 1: Parse
            update_task_run(run_id, status="running", current_stage="解析入库")
            sse_events[task_id] = [{"stage": "解析中", "msg": f"解析 {len(files)} 个文件...", "time": datetime.now().strftime("%H:%M:%S")}]
            validation_results = [
                validate_upload_file(UPLOAD_DIR / fn)
                for fn in files
                if os.path.exists(UPLOAD_DIR / fn)
            ]
            invalid_results = [item for item in validation_results if not item["ok"]]
            valid_files = [item["filename"] for item in validation_results if item["ok"]]
            if invalid_results:
                detail = "；".join(
                    f'{item["filename"]}: {" / ".join(item["errors"])}'
                    for item in invalid_results
                )
                sse_events[task_id].append({"stage": "校验提醒", "msg": detail, "time": datetime.now().strftime("%H:%M:%S")})
            if not valid_files:
                detail = "；".join(
                    f'{item["filename"]}: {" / ".join(item["errors"])}'
                    for item in invalid_results
                ) or "未找到可解析的 Excel 文件"
                update_task_run(run_id, status="failed", current_stage="校验失败", error=detail)
                update_task_run(run_id, status="failed", error=detail, finish=True)
                sse_events[task_id].append({"stage": "错误", "msg": detail, "time": datetime.now().strftime("%H:%M:%S")})
                return
            conn = init_db()
            total = 0
            for fn in valid_files:
                fp = str(UPLOAD_DIR / fn)
                if os.path.exists(fp):
                    inserted, stype = ingest_file(conn, fp)
                    total += inserted
            conn.close()
            update_task_run(run_id, status="running", current_stage="AI 分析", total_rows=total)
            sse_events[task_id].append({"stage": "解析完成", "msg": f"入库 {total} 条记录", "time": datetime.now().strftime("%H:%M:%S")})

            # Step 2: 4-layer Pipeline
            run_analysis_pipeline(task_id, today, run_id=run_id)

        except Exception as e:
            import traceback
            update_task_run(run_id, status="failed", current_stage="处理失败", error=str(e))
            update_task_run(run_id, status="failed", error=str(e), finish=True)
            sse_events[task_id].append({"stage": "错误", "msg": str(e), "time": datetime.now().strftime("%H:%M:%S")})
            sse_events[task_id].append({"stage": "错误详情", "msg": traceback.format_exc(), "time": datetime.now().strftime("%H:%M:%S")})

    def send_json(self, ok, message, extra=None):
        data = {"ok": ok, "message": message, "date": datetime.now().strftime("%Y-%m-%d")}
        if extra: data.update(extra)
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    server = HTTPServer((args.host, args.port), UploadHandler)
    print(f"🚀 芯鲜事数据服务 v3 | 4层Pipeline | http://0.0.0.0:{args.port}")
    server.serve_forever()

if __name__ == "__main__":
    main()
