#!/usr/bin/env python3
"""
芯鲜事看板HTML生成器 V2 — 渐进式信息架构
从4层Pipeline结果生成HTML看板，核心改变：点击展开而非全部平铺
"""
import json
from datetime import datetime
from html import escape as html_escape
from pathlib import Path
from urllib.parse import urlparse

TEMPLATE_PATH = Path(__file__).parent / "dashboard_template.html"

def esc(value):
    return html_escape(str(value or ""), quote=True)

def safe_href(value):
    href = str(value or "#")
    parsed = urlparse(href)
    if parsed.scheme in {"http", "https"}:
        return esc(href)
    return "#"

def fmt(n):
    if n is None: return "0"
    if n >= 10000: return f"{n/10000:.1f}w"
    if n >= 1000: return f"{n/1000:.1f}k"
    return str(n)

def generate_dashboard(date_str, l1, l2, l3, l4, db_conn):
    sections = []

    # Stats
    note_count = db_conn.execute("SELECT COUNT(*) FROM xhs_notes WHERE import_date >= ?", (date_str,)).fetchone()[0]
    hw_count = db_conn.execute("SELECT COUNT(*) FROM xhs_hotwords WHERE import_date >= ?", (date_str,)).fetchone()[0]
    tp_count = db_conn.execute("SELECT COUNT(*) FROM xhs_topics WHERE import_date >= ?", (date_str,)).fetchone()[0]

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekdays = ["一","二","三","四","五","六","日"]
        date_cn = f"{dt.year}.{dt.month}.{dt.day} 星期{weekdays[dt.weekday()]}"
    except: date_cn = date_str
    date_cn = esc(date_cn)

    # ═══ Header ═══
    sections.append(f'''
    <div class="hdr">
        <div class="hdr-mark">📱</div>
        <div class="hdr-text">
            <h1>芯鲜事 · 小红书运营看板</h1>
            <p>{date_cn} · 千瓜数据 · AI分析</p>
        </div>
    </div>
    <div class="stats">
        <div class="stat hl"><div class="n">{note_count}</div><div class="l">笔记</div></div>
        <div class="stat"><div class="n">{hw_count}</div><div class="l">热词</div></div>
        <div class="stat"><div class="n">{tp_count}</div><div class="l">话题</div></div>
    </div>''')

    # ═══ HOT TOP BAR — 选题推荐（最高优先级，4条） ═══
    recs = l4.get("recommendations", []) if isinstance(l4, dict) else []
    if recs:
        weekly = esc(l4.get("weekly_theme", "")) if isinstance(l4, dict) else ""
        items_html = ""
        for i, r in enumerate(recs[:4], 1):
            topic = esc(r.get("topic_title", ""))
            ctype = esc(r.get("content_type", ""))
            angle = esc(str(r.get("intel_angle", ""))[:80])
            hook = esc(r.get("hook_suggestion", ""))
            derivation = esc(str(r.get("derivation", ""))[:60])
            refs = r.get("reference_notes", [])
            ref_link = safe_href(refs[0].get("url","#")) if refs else "#"
            ref_title = esc(str(refs[0].get("title",""))[:30]) if refs else ""
            rclass = "r1" if i == 1 else ""
            detail_html = f'<div class="detail"><strong>Intel角度：</strong>{angle}<br><strong>钩子：</strong>{hook}<br><strong>来源：</strong><a href="{ref_link}" target="_blank">{ref_title}</a></div>'
            items_html += f'''
            <div class="hot-item">
                <div class="hot-item-head">
                    <span class="rank {rclass}">{i}</span>
                    <span class="title">{topic}</span>
                    <span class="meta">{ctype} <span class="tag {'tag-high' if i<=2 else 'tag-mid'}">{'高优' if i<=2 else '中优'}</span></span>
                    <span class="arrow">&#9654;</span>
                </div>
                {detail_html}
            </div>'''
        sections.append(f'''
        <div class="hotbar">
            <div class="hotbar-head">
                <div class="hot-dot"></div>
                <h2>选题推荐</h2>
                <span style="font-size:11px;color:var(--muted);margin-left:auto">{weekly}</span>
            </div>
            <div class="hotbar-items">{items_html}</div>
        </div>''')

    # ═══ CLUSTER CARDS — 聚类（点击展开） ═══
    clusters = l1.get("clusters", []) if isinstance(l1, dict) else []
    analyses = l2.get("cluster_analyses", []) if isinstance(l2, dict) else []
    # Build lookup for L2 analyses by cluster_id
    a_lookup = {a.get("cluster_id"): a for a in analyses if a.get("cluster_id")}
    # Also try name-based matching
    a_by_name = {a.get("cluster_name",""): a for a in analyses}

    if clusters:
        cl_html = ""
        for cl in clusters:
            cname = esc(cl.get("cluster_name", ""))
            hws = cl.get("hotwords", [])
            tps = cl.get("topics", [])
            rel_raw = cl.get("intel_relevance", "")
            rel = esc(rel_raw)
            reason = esc(cl.get("relevance_reason", ""))
            trend = esc(cl.get("trend_direction", ""))
            vd = cl.get("total_view_delta", 0)
            id_ = cl.get("total_interact_delta", 0)

            # Find matching L2 analysis
            a = a_lookup.get(cl.get("cluster_id")) or a_by_name.get(cl.get("cluster_name", ""), {})
            trend_a = esc(a.get("trend_analysis", ""))
            ideas = a.get("cross_category_ideas", [])
            opps = a.get("hotword_opportunities", [])
            actions = a.get("action_items", [])

            icon_cls = {"高":"high","中":"mid","低":"low","无关":"low"}.get(rel_raw,"low")
            badge_cls = icon_cls
            icon_emoji = {"高":"🎯","中":"🔗","低":"⬇️","无关":"✕"}.get(rel_raw,"·")

            # Tags
            hw_tags = " ".join([f'<span class="tag">{esc(w)}</span>' for w in hws[:8]])
            tp_tags = " ".join([f'<span class="tag topic">{esc(t)}</span>' for t in tps[:6]])

            # Deep analysis body
            body_parts = []
            if hw_tags or tp_tags:
                body_parts.append(f'<div><strong style="font-size:11px;color:var(--muted)">热词</strong><div class="tags">{hw_tags}</div></div>')
                body_parts.append(f'<div><strong style="font-size:11px;color:var(--muted)">话题</strong><div class="tags">{tp_tags}</div></div>')
            if trend_a:
                body_parts.append(f'<div class="insight">{trend_a}</div>')
            if ideas:
                ideas_li = "".join([f'<li><strong>{esc(i.get("angle",""))}</strong>：{esc(i.get("content_suggestion",""))}</li>' for i in ideas[:3]])
                body_parts.append(f'<div style="margin-top:8px"><strong style="font-size:11px;color:var(--muted)">跨品类借势</strong><ul style="font-size:12px;color:var(--text2);padding-left:16px;line-height:1.6">{ideas_li}</ul></div>')
            if opps:
                opps_html = " ".join([f'<span class="tag">{esc(o.get("keyword",""))}</span>' for o in opps[:4]])
                body_parts.append(f'<div style="margin-top:8px"><strong style="font-size:11px;color:var(--muted)">热词机会</strong><div class="tags">{opps_html}</div></div>')
            if actions:
                act_html = "".join([f"<li>{esc(action)}</li>" for action in actions[:3]])
                body_parts.append(f'<div class="action">⚡ {" · ".join(esc(action) for action in actions[:2])}</div>')

            # For low-relevance: always show reason as insight
            if rel_raw in ("低", "无关") and reason:
                body_parts.append(f'<div class="insight">{reason}</div>')
            body = "\n".join(body_parts)
            cl_html += f'''
            <div class="cluster">
                <div class="cluster-head">
                    <div class="icon {icon_cls}">{icon_emoji}</div>
                    <div class="info">
                        <div class="name">{cname}</div>
                        <div class="sub">热词{len(hws)} · 话题{len(tps)} · 浏览+{fmt(vd)}</div>
                    </div>
                    <span class="badge {badge_cls}">Intel {rel}</span>
                    <span class="arrow">▶</span>
                </div>
                <div class="cluster-body">
                    {body}
                </div>
            </div>'''
        sections.append(f'''
        <div class="sec"><h2>📊 趋势聚类</h2><span class="ln"></span><span class="count">{len(clusters)}个</span></div>
        <div class="cluster-list">{cl_html}</div>''')

    # ═══ NOTES — 爆款笔记（时间线风格，点击展开） ═══
    l3_clusters = l3.get("clusters", []) if isinstance(l3, dict) else []
    fmt_dist = l3.get("format_distribution", {}) if isinstance(l3, dict) else {}
    if l3_clusters:
        # Flatten all notes from all clusters
        all_notes = []
        for nc in l3_clusters:
            cname = nc.get("cluster_name", "")
            for n in nc.get("notes", []):
                n["_cluster"] = cname
                all_notes.append(n)
        # Sort by interactions desc
        all_notes.sort(key=lambda x: x.get("interactions", 0), reverse=True)

        # Build analysis lookup
        a_lookup = {}
        for nc in l3_clusters:
            for a in nc.get("top_analysis", []):
                a_lookup[a.get("title","")] = a

        notes_html = ""
        for n in all_notes[:15]:
            form = esc(n.get("form", ""))
            form_cls = "vid" if form == "视频" else "img"
            title = esc(str(n.get("title","") or "")[:45])
            interactions = n.get("interactions", 0)
            author = esc(n.get("author", ""))
            fans = n.get("fans", 0)
            url = safe_href(n.get("url", "#"))
            cluster = esc(n.get("_cluster", ""))
            a = a_lookup.get(n.get("title",""), {})

            body_parts = []
            body_parts.append(f'<div class="note-meta">{author} · 粉{fmt(fans)} · {cluster}</div>')
            if url and url != "#":
                body_parts.append(f'<a class="note-link" href="{url}" target="_blank">查看原笔记 →</a>')
            if a:
                body_parts.append(f'''<div class="analysis">
                    <div class="label why">为什么火</div><p>{esc(a.get("why_hot",""))}</p>
                    <div class="label how">Intel怎么做</div><p>{esc(a.get("intel_howto",""))}</p>
                </div>''')

            body = "\n".join(body_parts)
            notes_html += f'''
            <div class="note">
                <div class="note-head">
                    <span class="note-form {form_cls}">{form[:1]}</span>
                    <span class="note-title">{title}</span>
                    <span class="note-stats">👍{fmt(interactions)}</span>
                    <span class="note-arrow">▶</span>
                </div>
                <div class="note-body">{body}</div>
            </div>'''

        fmt_info = ""
        if fmt_dist:
            fmt_info = f' · 图文{fmt_dist.get("image_count",0)}/视频{fmt_dist.get("video_count",0)}'
        sections.append(f'''
        <div class="sec"><h2>📝 爆款笔记</h2><span class="ln"></span><span class="count">{len(all_notes)}篇{fmt_info}</span></div>
        <div class="timeline">{notes_html}</div>''')

    # ═══ TRENDS ═══
    l3_trends = l3.get("content_trends", []) if isinstance(l3, dict) else []
    if l3_trends:
        trends_html = ""
        for t in l3_trends[:4]:
            trends_html += f'''
            <div class="trend">
                    <div class="trend-title">{esc(t.get("trend",""))}</div>
                    <div class="trend-body">{esc(t.get("evidence",""))}</div>
                    <div class="trend-action">→ {esc(t.get("intel_action",""))}</div>
            </div>'''
        sections.append(f'''
        <div class="sec"><h2>📈 内容趋势</h2><span class="ln"></span></div>
        <div class="trends">{trends_html}</div>''')

    # ═══ Raw Data (折叠) ═══
    raw_row = db_conn.execute("SELECT content FROM xhs_analysis WHERE analysis_type='raw_notes' ORDER BY id DESC LIMIT 1").fetchone()
    if raw_row:
        try:
            raw_list = json.loads(raw_row[0])
            if raw_list:
                rows_html = ""
                for n in raw_list[:20]:
                    title = esc(str(n.get("title","") or "")[:30])
                    author = esc(n.get("author",""))
                    fans = fmt(n.get("fans",0))
                    likes = fmt(n.get("likes",0))
                    interactions = fmt(n.get("interactions",0))
                    form_val = esc(n.get("form",""))
                    url = safe_href(n.get("url","#") or "#")
                    rows_html += f'<tr><td><a href="{url}" target="_blank">{title}</a></td><td>{author}</td><td>{fans}</td><td>{likes}</td><td>{interactions}</td><td>{form_val}</td></tr>'
                sections.append(f'''
                <div class="sec"><h2>📋 原始数据</h2><span class="ln"></span><span class="count">TOP20</span></div>
                <details class="raw">
                    <summary>展开查看原始笔记数据</summary>
                    <div class="data-wrap" style="border:none;border-top:1px solid var(--border);border-radius:0"><table class="data-table">
                        <thead><tr><th>标题</th><th>达人</th><th>粉丝</th><th>👍</th><th>互动</th><th>形式</th></tr></thead>
                        <tbody>{rows_html}</tbody>
                    </table></div>
                </details>''')
        except: pass

    # ═══ Assemble HTML ═══
    content = "\n".join(sections)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    if TEMPLATE_PATH.exists():
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
    else:
        template = '<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body><div class="dash">{{CONTENT}}<div class="footer">{{TIMESTAMP}}</div></div></body></html>'

    html = template.replace("{{CONTENT}}", content).replace("{{TIMESTAMP}}", timestamp).replace("{{DATE}}", date_str)

    output_dir = Path.home() / "clawd" / "xhs_hot_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"qiangua_dashboard_{date_str}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)
