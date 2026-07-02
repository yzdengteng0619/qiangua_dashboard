from html import escape


BASE_CSS = """
*{box-sizing:border-box}
:root{
  --page:#f4f6f9;
  --ink:#111827;
  --sub:#5b6472;
  --muted:#8a94a6;
  --line:#dde3ec;
  --panel:#ffffff;
  --panel2:#f9fbfd;
  --blue:#0068b5;
  --cyan:#00a3b5;
  --green:#0f8f61;
  --red:#c2414b;
  --amber:#b7791f;
  --radius:8px;
}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--page);color:var(--ink);font-size:14px}
a{color:inherit;text-decoration:none}
.app{display:grid;grid-template-columns:236px minmax(0,1fr);min-height:100vh}
.side{background:#fbfcfe;border-right:1px solid var(--line);padding:18px 14px;position:sticky;top:0;height:100vh}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;margin:2px 6px 24px}
.brand-mark{width:30px;height:30px;border-radius:7px;background:var(--blue);color:#fff;display:grid;place-items:center;font-size:13px}
.brand-sub{display:block;color:var(--muted);font-size:11px;font-weight:600;margin-top:1px}
.nav-label{font-size:11px;color:var(--muted);margin:18px 8px 8px}
.nav a{display:flex;align-items:center;gap:9px;padding:10px 11px;border-radius:7px;color:#394252;margin-bottom:3px;font-weight:650}
.nav a.active{background:#111827;color:#fff}
.nav a:hover{background:#eef3f8}
.nav a.active:hover{background:#111827}
.nav-ico{width:18px;text-align:center;color:var(--blue)}
.nav a.active .nav-ico{color:#fff}
.main{padding:26px 34px 44px;max-width:1320px;width:100%}
.hero-panel{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(280px,.9fr);gap:18px;margin-bottom:18px}
.hero-copy{background:linear-gradient(135deg,#ffffff 0%,#eef7fb 100%);border:1px solid var(--line);border-radius:var(--radius);padding:22px;position:relative;overflow:hidden}
.hero-copy:after{content:"";position:absolute;right:18px;top:18px;width:84px;height:84px;background:repeating-linear-gradient(90deg,rgba(0,104,181,.14) 0 8px,transparent 8px 14px);border-radius:8px}
.eyebrow{font-size:12px;color:var(--blue);font-weight:800;margin-bottom:8px}
h1{font-size:30px;margin:0 0 8px;line-height:1.15}
.hero-copy p{margin:0;color:var(--sub);line-height:1.7;max-width:620px}
.hero-action{display:flex;align-items:center;justify-content:space-between;background:#111827;color:#fff;border-radius:var(--radius);padding:18px;border:1px solid #111827}
.hero-action span{display:block;color:#b8c2d2;font-size:12px;margin-top:5px}
.action-link{background:#fff;color:#111827;border-radius:7px;padding:9px 12px;font-weight:800;white-space:nowrap}
.metric-strip{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-bottom:18px}
.metric{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:15px}
.metric .num{font-size:28px;font-weight:850;line-height:1}
.metric .label{color:var(--sub);font-size:12px;margin-top:6px}
.metric .bar{height:4px;background:#edf1f7;border-radius:99px;margin-top:13px;overflow:hidden}
.metric .bar i{display:block;height:100%;background:var(--blue);border-radius:99px}
.metric:nth-child(2) .bar i{background:var(--cyan)}
.metric:nth-child(3) .bar i{background:var(--green)}
.mini-board{display:grid;grid-template-columns:1.2fr .9fr .9fr;gap:14px;align-items:start}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}
.panel-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px;border-bottom:1px solid var(--line);background:var(--panel2)}
.panel-head h2{font-size:15px;margin:0}
.panel-head .count{font-size:12px;color:var(--muted)}
table{width:100%;border-collapse:collapse;background:#fff}
th,td{padding:11px 12px;border-bottom:1px solid #edf1f5;text-align:left;font-size:13px;vertical-align:top}
th{color:var(--sub);background:#fbfcfe;font-size:12px;font-weight:800}
tr:last-child td{border-bottom:none}
.visual-rank{display:flex;flex-direction:column}
.rank-row{display:grid;grid-template-columns:26px minmax(0,1fr) auto;gap:10px;align-items:center;padding:12px 14px;border-bottom:1px solid #edf1f5}
.rank-row:last-child{border-bottom:none}
.rank-no{width:24px;height:24px;border-radius:6px;background:#eef5fb;color:var(--blue);display:grid;place-items:center;font-weight:850;font-size:12px}
.rank-title{font-weight:750;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rank-meta{color:var(--muted);font-size:12px}
.empty{color:var(--muted);padding:18px 14px}
.reader{display:grid;grid-template-columns:290px minmax(0,820px);gap:34px;min-height:100vh}
.history{background:#fbfcfe;border-right:1px solid var(--line);padding:20px;min-height:100vh}
.history h2{font-size:15px;margin:18px 0 10px}
.history a{display:block;padding:11px 0;border-bottom:1px solid #edf1f5}
.history strong{font-size:13px}
.daily{padding:30px 0 60px}
.daily-cover{border:1px solid var(--line);background:#fff;border-radius:var(--radius);padding:28px;margin-bottom:22px;position:relative;overflow:hidden}
.daily-cover:before{content:"";position:absolute;left:0;top:0;bottom:0;width:7px;background:linear-gradient(180deg,var(--blue),var(--cyan),var(--red))}
.vol{font-size:12px;color:var(--muted);font-weight:800;text-transform:uppercase}
.daily h1{font-size:46px;line-height:1;margin:10px 0}
.lead{font-size:18px;line-height:1.75;color:#2f3948;margin:0;max-width:720px}
.signal-list{display:grid;gap:8px;margin-top:18px}
.signal{display:flex;gap:10px;align-items:flex-start;background:#f7fafc;border:1px solid #e7edf5;border-radius:7px;padding:10px 12px;color:#2f3948}
.signal b{color:var(--blue)}
.section{margin-top:28px}
.section-head{display:flex;align-items:end;gap:13px;border-top:1px solid #cfd8e5;padding-top:17px;margin-bottom:4px}
.section-num{font-size:34px;font-weight:900;color:#c9d3df;line-height:1}
.section h2{margin:0;font-size:24px}
.kicker{color:var(--muted);font-size:12px;font-weight:800;margin-top:2px}
.insight-card{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:17px 18px;margin-top:12px}
.insight-card h3{margin:0 0 8px;font-size:18px;line-height:1.35}
.source{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--blue);font-weight:800;margin-bottom:8px}
.insight-card p{line-height:1.75;color:#374151;margin:0}
.upload-command-center{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(320px,.8fr);gap:18px;margin-bottom:18px}
.upload-panel{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:22px}
.drop-zone{border:1px dashed #9bb8d2;background:#f6fbff;border-radius:var(--radius);padding:26px;text-align:center;cursor:pointer;transition:border-color .15s,background .15s}
.drop-zone:hover,.drop-zone.drag{border-color:var(--blue);background:#eef7fb}
.drop-zone h2{margin:0 0 6px;font-size:22px}
.drop-zone p{margin:0;color:var(--sub)}
.drop-zone input{display:none}
.upload-button{margin-top:16px;border:0;background:var(--blue);color:#fff;border-radius:7px;padding:10px 15px;font-weight:850;cursor:pointer}
.upload-button:disabled{background:#b9c3d1;cursor:not-allowed}
.pipeline-steps{display:grid;gap:8px;margin-top:18px}
.step{display:grid;grid-template-columns:28px minmax(0,1fr) auto;gap:10px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:7px;padding:10px 12px}
.step.active{border-color:var(--blue);background:#f4f9fd}
.step.done{border-color:#b8e0cb;background:#f4fbf7}
.step-dot{width:22px;height:22px;border-radius:6px;background:#edf2f7;display:grid;place-items:center;color:var(--sub);font-size:12px;font-weight:850}
.step.done .step-dot{background:var(--green);color:#fff}
.step.active .step-dot{background:var(--blue);color:#fff}
.progress-bar{height:5px;background:#e8edf4;border-radius:999px;overflow:hidden;margin-top:14px}
.progress-fill{height:100%;width:0;background:linear-gradient(90deg,var(--blue),var(--cyan));border-radius:999px;transition:width .3s}
.file-list{display:grid;gap:8px;margin-top:12px}
.file-item{display:flex;justify-content:space-between;gap:10px;border:1px solid var(--line);background:#fff;border-radius:7px;padding:8px 10px;color:var(--sub);font-size:12px}
.quick-links,.recent-runs{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:18px;margin-bottom:14px}
.quick-links h2,.recent-runs h2{margin:0 0 12px;font-size:15px}
.quick-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.quick-card{border:1px solid var(--line);border-radius:7px;padding:11px;background:#fbfcfe}
.quick-card strong{display:block;margin-bottom:4px}
.run-item{display:flex;justify-content:space-between;gap:12px;border-top:1px solid #edf1f5;padding:11px 0;color:var(--sub)}
.run-item:first-of-type{border-top:0;padding-top:0}
.result-link{display:none;margin-top:14px;background:#0f8f61;color:#fff;border-radius:7px;padding:10px 12px;font-weight:850;text-align:center}
@media(max-width:920px){
  .app,.reader{display:block}
  .side,.history{position:static;height:auto;min-height:0;border-right:0;border-bottom:1px solid var(--line)}
  .main{padding:18px}
  .hero-panel,.mini-board,.upload-command-center{grid-template-columns:1fr}
  .metric-strip{grid-template-columns:1fr}
  .daily{padding:18px}
  .daily h1{font-size:34px}
  .quick-grid{grid-template-columns:1fr}
}
"""


def fmt(value):
    try:
        n = int(value or 0)
    except (TypeError, ValueError):
        return escape(str(value or "0"))
    if n >= 10000:
        return f"{n / 10000:.1f}w"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


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
        ("上传数据", "/upload", "↑"),
        ("数据看板", "/dashboard", "▦"),
        ("洞察日报", "/insights", "◫"),
        ("历史记录", "/history", "⌕"),
    ]
    links = "".join(
        f'<a class="{"active" if name == active else ""}" href="{href}"><span class="nav-ico">{icon}</span>{name}</a>'
        for name, href, icon in items
    )
    return (
        '<aside class="side"><div class="brand"><div class="brand-mark">IQ</div>'
        '<div>千瓜 Intel<span class="brand-sub">XHS intelligence</span></div></div>'
        f'<div class="nav-label">工作区</div><nav class="nav">{links}</nav></aside>'
    )


def render_upload_page(date_str, recent_runs=None):
    recent_runs = recent_runs or []
    steps = [
        "上传文件",
        "解析入库",
        "L1 趋势聚类",
        "L2 深度机会",
        "L3 爆款拆解",
        "L4 选题推荐",
        "生成页面",
    ]
    step_html = "".join(
        f'<div class="step wait" id="s{idx}"><div class="step-dot">{idx}</div><div>{label}</div><span class="muted">等待</span></div>'
        for idx, label in enumerate(steps, 1)
    )
    if recent_runs:
        recent_html = "".join(
            '<div class="run-item">'
            f'<span>{escape(str(run.get("analysis_date", "")))} · {escape(str(run.get("current_stage", "")))} · {fmt(run.get("total_rows", 0))} 行</span>'
            f'<strong>{escape(str(run.get("status", "")))}</strong>'
            '</div>'
            for run in recent_runs[:5]
        )
    else:
        recent_html = (
            '<div class="run-item"><span>今日批次</span><strong>等待上传</strong></div>'
            '<div class="run-item"><span>分析管线</span><strong>L1-L4</strong></div>'
            '<div class="run-item"><span>输出页面</span><strong>看板 / 日报</strong></div>'
        )
    body = f"""
    <div class="app">{nav("上传数据")}<main class="main">
      <section class="hero-panel">
        <div class="hero-copy">
          <div class="eyebrow">DAILY INGESTION</div>
          <h1>上传任务中心</h1>
          <p>{escape(date_str)} · 上传千瓜 Excel 或压缩包后，系统会自动入库、运行 4 层分析，并生成数据看板与洞察日报。</p>
        </div>
        <div class="hero-action">
          <div><strong>上传后不用刷新</strong><span>进度会在当前页面实时更新，完成后直接打开结果。</span></div>
          <a class="action-link" href="/dashboard?date={escape(date_str)}">看今日看板</a>
        </div>
      </section>
      <section class="upload-command-center">
        <div class="upload-panel">
          <div class="drop-zone" id="dz">
            <h2>拖拽千瓜文件到这里</h2>
            <p>支持 xls / xlsx / zip / tar / gz，多文件一次上传。</p>
            <input type="file" id="fi" multiple>
            <button class="upload-button" id="ub" disabled>选择文件</button>
          </div>
          <div class="file-list" id="fl"></div>
          <div class="progress-bar"><div class="progress-fill" id="pf"></div></div>
          <div class="pipeline-steps" id="pipeline">{step_html}</div>
          <a class="result-link" id="dl" href="/dashboard?date={escape(date_str)}">打开生成结果</a>
        </div>
        <aside>
          <div class="quick-links">
            <h2>快捷入口</h2>
            <div class="quick-grid">
              <a class="quick-card" href="/dashboard?date={escape(date_str)}"><strong>数据看板</strong><span class="muted">排行、热词、话题</span></a>
              <a class="quick-card" href="/insights?date={escape(date_str)}"><strong>洞察日报</strong><span class="muted">趋势、选题、建议</span></a>
            </div>
          </div>
          <div class="recent-runs">
            <h2>最近任务</h2>
            {recent_html}
          </div>
        </aside>
      </section>
    </main></div>
    <script>
const dz=document.getElementById('dz'),fi=document.getElementById('fi'),ub=document.getElementById('ub');
const pf=document.getElementById('pf'),fl=document.getElementById('fl'),dl=document.getElementById('dl');
let sel=[];
dz.addEventListener('click',e=>{{if(e.target!==ub)fi.click();}});
ub.addEventListener('click',e=>{{e.stopPropagation(); if(sel.length) doUpload(); else fi.click();}});
dz.addEventListener('dragover',e=>{{e.preventDefault();dz.classList.add('drag');}});
dz.addEventListener('dragleave',()=>dz.classList.remove('drag'));
dz.addEventListener('drop',e=>{{e.preventDefault();dz.classList.remove('drag');handleFiles(e.dataTransfer.files);}});
fi.addEventListener('change',e=>handleFiles(e.target.files));
function validFile(f){{const n=f.name.toLowerCase();return ['.xls','.xlsx','.tar','.tar.gz','.tgz','.zip','.gz'].some(x=>n.endsWith(x));}}
function handleFiles(files){{
  sel=Array.from(files).filter(validFile);
  if(!sel.length){{alert('请选择千瓜 Excel 或压缩包文件');return;}}
  fl.innerHTML=sel.map(f=>'<div class="file-item"><span>'+f.name+'</span><span>'+Math.max(1,Math.round(f.size/1024))+'KB</span></div>').join('');
  ub.disabled=false;ub.textContent='上传并分析 '+sel.length+' 个文件';
}}
async function doUpload(){{
  if(!sel.length)return;
  ub.disabled=true;setStage(1,'active');pf.style.width='8%';
  const fd=new FormData();sel.forEach(f=>fd.append('files',f));
  try{{
    const r=await fetch('/upload',{{method:'POST',body:fd}});
    const d=await r.json();
    if(d.ok){{setStage(1,'done');setStage(2,'active');listenSSE(d.task_id);}}
    else{{alert('上传失败: '+d.message);ub.disabled=false;}}
  }}catch(e){{alert('上传失败: '+e.message);ub.disabled=false;}}
}}
function listenSSE(taskId){{
  const es=new EventSource('/progress/'+taskId);
  es.onmessage=function(e){{
    const d=JSON.parse(e.data), stage=d.stage||'';
    if(stage.includes('解析')||stage.includes('入库')){{setStage(2,'active');}}
    if(stage.includes('Layer 1')){{setStage(2,'done');setStage(3,'active');}}
    if(stage.includes('Layer 2')){{setStage(3,'done');setStage(4,'active');}}
    if(stage.includes('Layer 3')){{setStage(4,'done');setStage(5,'active');}}
    if(stage.includes('Layer 4')){{setStage(5,'done');setStage(6,'active');}}
    if(stage.includes('分析完成')){{setStage(6,'done');setStage(7,'active');}}
    if(stage.includes('看板就绪')){{
      setStage(7,'done');pf.style.width='100%';es.close();
      if(d.data&&d.data.url)dl.href=d.data.url;dl.style.display='block';
      ub.disabled=false;ub.textContent='继续上传';
    }}
  }};
  es.onerror=function(){{es.close();ub.disabled=false;}};
}}
function setStage(n,state){{
  const el=document.getElementById('s'+n);if(!el)return;
  el.className='step '+state;
  const label=el.querySelector('span'); if(label) label.textContent=state==='done'?'完成':(state==='active'?'进行中':'等待');
  const pct={{1:8,2:18,3:32,4:46,5:60,6:76,7:92}}[n]||0;
  if(state==='done'||state==='active')pf.style.width=pct+'%';
}}
    </script>
    """
    return page("上传任务中心", body)


def stat_card(label, value, width):
    return (
        f'<div class="metric"><div class="num">{fmt(value)}</div>'
        f'<div class="label">{label}</div><div class="bar"><i style="width:{width}%"></i></div></div>'
    )


def rank_rows(items, title_key, meta_key, value_key, empty_text):
    if not items:
        return f'<div class="empty">{empty_text}</div>'
    rows = []
    for idx, item in enumerate(items[:8], 1):
        title = escape(str(item.get(title_key, "")))
        meta = escape(str(item.get(meta_key, ""))) if meta_key else ""
        value = fmt(item.get(value_key, 0)) if value_key else ""
        rows.append(
            '<div class="rank-row">'
            f'<div class="rank-no">{idx}</div>'
            f'<div><div class="rank-title">{title}</div><div class="rank-meta">{meta}</div></div>'
            f'<div class="rank-meta">{value}</div>'
            '</div>'
        )
    return "".join(rows)


def render_dashboard_page(date_str, summary, top_notes, hotwords, topics):
    note_count = summary.get("note_count", 0)
    hotword_count = summary.get("hotword_count", 0)
    topic_count = summary.get("topic_count", 0)
    stat_cards = "".join([
        stat_card("笔记", note_count, 86),
        stat_card("热词", hotword_count, 62),
        stat_card("话题", topic_count, 48),
    ])
    note_rows = "".join(
        "<tr>"
        f"<td>{escape(str(n.get('title', '')))}</td>"
        f"<td>{escape(str(n.get('author', '')))}</td>"
        f"<td>{fmt(n.get('interactions', 0))}</td>"
        "</tr>"
        for n in top_notes[:12]
    ) or '<tr><td colspan="3" class="empty">暂无笔记数据</td></tr>'
    hotword_rows = rank_rows(hotwords, "word", "category", "note_delta", "暂无热词数据")
    topic_rows = rank_rows(topics, "topic", None, "view_delta", "暂无话题数据")
    body = f"""
    <div class="app">{nav("数据看板")}<main class="main">
      <section class="hero-panel">
        <div class="hero-copy">
          <div class="eyebrow">QIANGUA OPERATIONS</div>
          <h1>数据看板</h1>
          <p>{escape(date_str)} · 将千瓜上传数据整理成可筛选、可排序、可追踪的运营分析台。</p>
        </div>
        <div class="hero-action">
          <div><strong>今日洞察已分离</strong><span>长文判断、选题建议和内容拆解在日报页阅读。</span></div>
          <a class="action-link" href="/insights?date={escape(date_str)}">打开日报</a>
        </div>
      </section>
      <section class="metric-strip">{stat_cards}</section>
      <section class="mini-board">
        <div class="panel">
          <div class="panel-head"><h2>爆款笔记</h2><span class="count">TOP {min(len(top_notes), 12)}</span></div>
          <table><thead><tr><th>标题</th><th>作者</th><th>互动</th></tr></thead><tbody>{note_rows}</tbody></table>
        </div>
        <div class="panel visual-rank">
          <div class="panel-head"><h2>热词增长</h2><span class="count">Hotwords</span></div>
          {hotword_rows}
        </div>
        <div class="panel visual-rank">
          <div class="panel-head"><h2>话题热度</h2><span class="count">Topics</span></div>
          {topic_rows}
        </div>
      </section>
    </main></div>
    """
    return page("数据看板", body)


def render_insights_page(date_str, history, report):
    history_html = "".join(
        f'<a href="/insights/{escape(h["date"])}"><strong>{escape(h["date"])}</strong><br><span class="muted">{escape(h.get("headline", ""))}</span></a>'
        for h in history
    ) or '<div class="empty">暂无历史日报</div>'
    points = "".join(
        f'<div class="signal"><b>{idx:02d}</b><span>{escape(point)}</span></div>'
        for idx, point in enumerate(report.get("key_points", []), 1)
    ) or '<div class="signal"><b>00</b><span>暂无重点机会</span></div>'
    sections = []
    for idx, section in enumerate(report.get("sections", []), 1):
        articles = "".join(
            f"""<article class="insight-card">
              <h3>{escape(item.get("title", ""))}</h3>
              <div class="source">来源 · {escape(item.get("source", ""))}</div>
              <p>{escape(item.get("summary", ""))}</p>
            </article>"""
            for item in section.get("items", [])
        ) or '<div class="empty">暂无条目</div>'
        sections.append(
            f"""<section class="section">
              <div class="section-head"><div class="section-num">{idx:02d}</div><div><h2>{escape(section.get("title", ""))}</h2><div class="kicker">{escape(section.get("kicker", ""))}</div></div></div>
              {articles}
            </section>"""
        )
    body = f"""
    <div class="reader">
      <aside class="history"><div class="brand"><div class="brand-mark">IQ</div><div>千瓜 Intel<span class="brand-sub">Daily archive</span></div></div><h2>日报历史</h2>{history_html}<p><a href="/dashboard?date={escape(date_str)}">打开数据看板</a></p></aside>
      <main class="daily">
        <section class="daily-cover">
          <div class="vol">VOL.{escape(date_str)} · QIANGUA DAILY</div>
          <h1>洞察日报</h1>
          <p class="lead">{escape(report.get("headline", "暂无洞察日报"))}</p>
          <div class="signal-list">{points}</div>
        </section>
        {''.join(sections)}
      </main>
    </div>
    """
    return page("洞察日报", body)
