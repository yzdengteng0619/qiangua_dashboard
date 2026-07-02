from html import escape


BASE_CSS = """
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;background:#f7f8fb;color:#111827}
a{color:inherit;text-decoration:none}
.app{display:grid;grid-template-columns:220px 1fr;min-height:100vh}
.side{border-right:1px solid #e5e7eb;background:#fff;padding:18px;position:sticky;top:0;height:100vh}
.brand{font-weight:800;margin-bottom:22px}
.nav a{display:block;padding:9px 10px;border-radius:6px;color:#4b5563;margin-bottom:4px}
.nav a.active{background:#111827;color:#fff}
.main{padding:24px 32px}
.toolbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;gap:18px}
.muted{color:#6b7280}
.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-bottom:18px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:14px}
.num{font-size:26px;font-weight:800}
.label{font-size:12px;color:#6b7280}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden}
th,td{padding:10px;border-bottom:1px solid #edf0f5;text-align:left;font-size:13px}
th{color:#6b7280;background:#fafafa}
.reader{display:grid;grid-template-columns:280px minmax(0,780px);gap:28px}
.history{background:#fff;border-right:1px solid #e5e7eb;padding:20px;min-height:100vh}
.history a{display:block;padding:10px 0;border-bottom:1px solid #f0f2f5}
.daily{padding:30px 0}
.vol{font-size:12px;letter-spacing:.12em;color:#6b7280;text-transform:uppercase}
.daily h1{font-size:44px;line-height:1;margin:8px 0 10px}
.lead{font-size:18px;line-height:1.7;color:#374151}
.section{margin-top:34px}
.section-head{display:flex;align-items:end;gap:12px;border-top:1px solid #d1d5db;padding-top:18px}
.section-num{font-size:32px;font-weight:800;color:#d1d5db}
.section h2{margin:0;font-size:24px}
.kicker{color:#6b7280;font-size:12px}
.article{padding:18px 0;border-bottom:1px solid #e5e7eb}
.article h3{margin:0 0 6px;font-size:19px}
.source{font-size:12px;color:#6b7280;margin-bottom:8px}
.article p{line-height:1.7;color:#374151}
@media(max-width:800px){
  .app,.reader{display:block}
  .side,.history{position:static;height:auto;min-height:0;border-right:0;border-bottom:1px solid #e5e7eb}
  .main{padding:18px}
  .cards{grid-template-columns:1fr}
  .daily{padding:20px}
  .daily h1{font-size:34px}
}
"""


def page(title, body):
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<style>{BASE_CSS}</style>
</head>
<body>{body}</body>
</html>"""


def nav(active):
    items = [
        ("上传数据", "/upload"),
        ("数据看板", "/dashboard"),
        ("洞察日报", "/insights"),
        ("历史记录", "/history"),
    ]
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
        "<tr>"
        f"<td>{escape(str(n.get('title', '')))}</td>"
        f"<td>{escape(str(n.get('author', '')))}</td>"
        f"<td>{escape(str(n.get('interactions', 0)))}</td>"
        "</tr>"
        for n in top_notes
    ) or '<tr><td colspan="3" class="muted">暂无笔记数据</td></tr>'
    body = f"""
    <div class="app">{nav("数据看板")}<main class="main">
      <div class="toolbar">
        <div><h1>数据看板</h1><p class="muted">{escape(date_str)} · 原始数据、排行和筛选</p></div>
        <a href="/insights?date={escape(date_str)}">打开洞察日报</a>
      </div>
      <section class="cards">{stat_cards}</section>
      <h2>爆款笔记</h2>
      <table><thead><tr><th>标题</th><th>作者</th><th>互动</th></tr></thead><tbody>{note_rows}</tbody></table>
    </main></div>
    """
    return page("数据看板", body)


def render_insights_page(date_str, history, report):
    history_html = "".join(
        f'<a href="/insights/{escape(h["date"])}"><strong>{escape(h["date"])}</strong><br><span class="muted">{escape(h.get("headline", ""))}</span></a>'
        for h in history
    )
    points = "".join(f"<li>{escape(p)}</li>" for p in report.get("key_points", []))
    sections = []
    for idx, section in enumerate(report.get("sections", []), 1):
        articles = "".join(
            f"""<article class="article">
              <h3>{escape(item.get("title", ""))}</h3>
              <div class="source">{escape(item.get("source", ""))}</div>
              <p>{escape(item.get("summary", ""))}</p>
            </article>"""
            for item in section.get("items", [])
        )
        sections.append(
            f"""<section class="section">
              <div class="section-head"><div class="section-num">{idx:02d}</div><div><h2>{escape(section.get("title", ""))}</h2><div class="kicker">{escape(section.get("kicker", ""))}</div></div></div>
              {articles}
            </section>"""
        )
    body = f"""
    <div class="reader">
      <aside class="history"><div class="brand">千瓜 Intel</div><h2>日报历史</h2>{history_html}<p><a href="/dashboard?date={escape(date_str)}">打开数据看板</a></p></aside>
      <main class="daily"><div class="vol">VOL.{escape(date_str)} · QIANGUA DAILY</div><h1>洞察日报</h1><p class="lead">{escape(report.get("headline", "暂无日报"))}</p><ul>{points}</ul>{''.join(sections)}</main>
    </div>
    """
    return page("洞察日报", body)
