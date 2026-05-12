"""
build_dashboard.py
Reads data/state.json produced by scraper.py and generates index.html —
the live dashboard for Chico City Council meeting tracking.
"""

import json
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).parent / "data" / "state.json"
OUTPUT     = Path(__file__).parent / "index.html"

STATUS_COLOR = {
    "active":    ("badge-red",   "Active"),
    "passed":    ("badge-green", "Passed"),
    "tabled":    ("badge-amber", "Tabled / Continued"),
    "scheduled": ("badge-blue",  "Scheduled"),
    "unknown":   ("badge-gray",  "Ongoing"),
}


def fmt_date(d: str) -> str:
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%b %-d, %Y")
    except Exception:
        return d


def badge(cls: str, text: str) -> str:
    return f'<span class="badge {cls}">{text}</span>'


def render_bill_card(bill: dict, idx: int) -> str:
    color_cls, label = STATUS_COLOR.get(bill["status"], ("badge-gray", "Ongoing"))
    appearances = bill["appearances"]
    count = bill["meeting_count"]

    # Build mini timeline
    timeline_html = ""
    for i, ap in enumerate(sorted(appearances, key=lambda x: x["date"])):
        is_last = (i == len(appearances) - 1)
        dot_cls = "current" if is_last else "past"
        timeline_html += f"""
        <div class="tl-item">
          <div class="tl-dot {dot_cls}"></div>
          <div class="tl-date">{fmt_date(ap['date'])}</div>
          <div class="tl-event">{ap.get('title_seen', bill['canonical_title'])}</div>
          {'<div class="tl-sub">' + ap.get("meeting_title","") + '</div>' if ap.get("meeting_title") else ""}
        </div>"""

    expand_id = f"bill-{idx}"
    return f"""
    <div class="card">
      <div class="card-header">
        <span class="card-num">#{count} mtgs</span>
        <span class="card-title">{bill['canonical_title']}</span>
      </div>
      <div class="badges">
        {badge(color_cls, label)}
        {badge("badge-gray", f"First: {fmt_date(bill['first_seen'])}")}
        {badge("badge-gray", f"Last: {fmt_date(bill['last_seen'])}")}
      </div>
      <button class="expand-btn" onclick="toggle('{expand_id}', this)">
        Show timeline ({count} appearances) <span class="chevron">▾</span>
      </button>
      <div class="detail" id="{expand_id}">
        <div class="timeline">{timeline_html}</div>
      </div>
    </div>"""


def render_meeting_card(meeting: dict, idx: int) -> str:
    has_min = meeting.get("has_minutes") or meeting.get("type") == "minutes"
    date_str = fmt_date(meeting["date"])
    title = meeting.get("title", f"Meeting {date_str}")
    link  = meeting.get("link", "#")

    items = meeting.get("items") or meeting.get("agenda_items", [])
    items_html = ""
    if items:
        for item in items[:12]:
            num_part = f'<span class="card-num">{item["num"]}</span>' if item.get("num") else ""
            items_html += f'<div class="card-header">{num_part}<span class="card-title" style="font-size:13px;font-weight:400">{item["title"]}</span></div>'
        if len(items) > 12:
            items_html += f'<div class="card-desc" style="margin-top:.4rem">…and {len(items)-12} more items</div>'

    expand_id = f"mtg-{idx}"
    minutes_badge = badge("badge-green", "Minutes available") if has_min else badge("badge-amber", "Agenda only")

    return f"""
    <div class="card">
      <div class="card-header">
        <span class="card-num">{date_str}</span>
        <span class="card-title"><a href="{link}" target="_blank" style="color:inherit;text-decoration:none">{title} ↗</a></span>
      </div>
      <div class="badges">{minutes_badge}</div>
      {'<button class="expand-btn" onclick="toggle(\'' + expand_id + '\', this)">Show items (' + str(len(items)) + ') <span class="chevron">▾</span></button><div class="detail" id="' + expand_id + '">' + items_html + '</div>' if items else ""}
    </div>"""


def build(state: dict) -> str:
    meetings = state.get("meetings", [])
    bills    = state.get("bills", [])
    updated  = state.get("last_updated", "")
    try:
        updated_fmt = datetime.fromisoformat(updated).strftime("%b %-d, %Y at %-I:%M %p UTC")
    except Exception:
        updated_fmt = updated

    recent_meeting = meetings[0] if meetings else {}
    recent_date    = fmt_date(recent_meeting.get("date", "")) if recent_meeting else "—"
    recent_title   = recent_meeting.get("title", "—")
    next_meeting   = next((m for m in reversed(meetings) if m.get("date", "") > datetime.now().strftime("%Y-%m-%d")), None)
    next_date_fmt  = fmt_date(next_meeting["date"]) if next_meeting else "TBD"

    tracked_active = sum(1 for b in bills if b["status"] == "active")

    # Meeting cards (all)
    meeting_cards_html = "\n".join(render_meeting_card(m, i) for i, m in enumerate(meetings))

    # Bill cards
    if bills:
        bill_cards_html = "\n".join(render_bill_card(b, i) for i, b in enumerate(bills))
    else:
        bill_cards_html = '<div class="lead">No recurring agenda items detected across meetings yet. Check back after more meetings are scraped.</div>'

    recent_items = recent_meeting.get("items") or recent_meeting.get("agenda_items", [])
    def _recent_card(it):
        num_html = f'<span class="card-num">{it["num"]}</span>' if it.get("num") else ""
        return (
            f'<div class="card"><div class="card-header">'
            f'{num_html}'
            f'<span class="card-title">{it["title"]}</span></div></div>'
        )
    recent_cards_html = "\n".join(_recent_card(it) for it in recent_items[:20]) \
        or '<div class="lead">No agenda items found for most recent meeting.</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chico City Council — Live Tracker</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500&display=swap');

:root {{
  --bg: #f5f2ec;
  --surface: #ffffff;
  --surface2: #f0ede6;
  --border: rgba(0,0,0,0.09);
  --border2: rgba(0,0,0,0.15);
  --text: #1a1814;
  --text2: #6b6660;
  --text3: #9c9691;
  --accent: #2d5a3d;
  --accent-light: #e8f0eb;
  --red: #8b2020;
  --red-light: #f5e8e8;
  --amber: #7a4f00;
  --amber-light: #fdf3e0;
  --blue: #1a3d6b;
  --blue-light: #e8eef7;
  --tag-h: 22px;
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: 'DM Sans', sans-serif;
  background: var(--bg);
  color: var(--text);
  font-size: 15px;
  line-height: 1.65;
  min-height: 100vh;
}}

.site-header {{
  background: var(--text);
  color: var(--bg);
  padding: 3rem 2rem 2.5rem;
  position: relative;
  overflow: hidden;
}}
.site-header::after {{
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent), #5a9e70, var(--accent));
}}
.header-inner {{ max-width: 900px; margin: 0 auto; }}
.header-eyebrow {{
  font-size: 11px; font-weight: 500; letter-spacing: .12em;
  text-transform: uppercase; color: rgba(245,242,236,.5); margin-bottom: .75rem;
}}
.header-title {{
  font-family: 'Instrument Serif', serif;
  font-size: clamp(2rem, 5vw, 3rem);
  font-weight: 400; line-height: 1.1; color: var(--bg); margin-bottom: .5rem;
}}
.header-title em {{ font-style: italic; color: rgba(245,242,236,.65); }}
.header-meta {{
  font-size: 12px; color: rgba(245,242,236,.45);
  display: flex; flex-wrap: wrap; gap: .25rem 1.25rem; margin-top: 1rem;
}}
.update-pill {{
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 11px; font-weight: 500; letter-spacing: .04em;
  background: rgba(255,255,255,.07); color: rgba(245,242,236,.6);
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 20px; padding: 3px 12px; margin-top: 1rem;
}}
.live-dot {{
  width: 7px; height: 7px; border-radius: 50%;
  background: #5a9e70;
  animation: pulse 2s ease-in-out infinite;
}}
@keyframes pulse {{
  0%,100% {{ opacity:1; }} 50% {{ opacity:.35; }}
}}

.container {{ max-width: 900px; margin: 0 auto; padding: 2rem 2rem 4rem; }}

.stats-row {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px; margin-bottom: 2.5rem;
}}
.stat {{
  background: var(--surface);
  border: 0.5px solid var(--border);
  border-radius: 10px; padding: 1rem 1.1rem;
}}
.stat-label {{ font-size: 11px; color: var(--text3); letter-spacing: .04em; text-transform: uppercase; margin-bottom: .3rem; }}
.stat-val {{ font-family: 'Instrument Serif', serif; font-size: 2rem; color: var(--text); line-height: 1; }}
.stat-sub {{ font-size: 12px; color: var(--text2); margin-top: .3rem; }}

.tabs-wrap {{ margin-bottom: 1.75rem; }}
.tabs {{
  display: flex; flex-wrap: wrap; gap: 6px;
  border-bottom: 0.5px solid var(--border); padding-bottom: 0;
}}
.tab-btn {{
  font-family: 'DM Sans', sans-serif; font-size: 13px; font-weight: 400;
  padding: 7px 16px; border: none; background: none; color: var(--text2);
  cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -0.5px;
  transition: color .15s, border-color .15s; white-space: nowrap;
}}
.tab-btn:hover {{ color: var(--text); }}
.tab-btn.active {{ color: var(--text); border-bottom-color: var(--accent); font-weight: 500; }}
.panel {{ display: none; }}
.panel.active {{ display: block; }}

.card {{
  background: var(--surface); border: 0.5px solid var(--border);
  border-radius: 10px; padding: 1.1rem 1.25rem; margin-bottom: .875rem;
  transition: border-color .15s;
}}
.card:hover {{ border-color: var(--border2); }}
.card-header {{ display: flex; align-items: flex-start; gap: 10px; margin-bottom: .5rem; }}
.card-num {{ font-size: 11px; color: var(--text3); min-width: 56px; padding-top: 3px; font-weight: 500; white-space: nowrap; }}
.card-title {{ font-size: 15px; font-weight: 500; color: var(--text); line-height: 1.35; flex: 1; }}
.card-desc {{ font-size: 13px; color: var(--text2); line-height: 1.65; margin-bottom: .5rem; }}

.badges {{ display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: .6rem; }}
.badge {{
  font-size: 11px; font-weight: 500; padding: 2px 9px;
  border-radius: 20px; height: var(--tag-h);
  display: inline-flex; align-items: center; letter-spacing: .01em;
}}
.badge-green {{ background: var(--accent-light); color: var(--accent); }}
.badge-red   {{ background: var(--red-light);    color: var(--red);    }}
.badge-amber {{ background: var(--amber-light);  color: var(--amber);  }}
.badge-blue  {{ background: var(--blue-light);   color: var(--blue);   }}
.badge-gray  {{ background: var(--surface2);     color: var(--text2);  }}

.expand-btn {{
  font-size: 12px; color: var(--accent); background: none; border: none;
  cursor: pointer; padding: 0; margin-top: .5rem;
  display: inline-flex; align-items: center; gap: 4px;
  font-family: 'DM Sans', sans-serif; transition: opacity .15s;
}}
.expand-btn:hover {{ opacity: .75; }}
.expand-btn .chevron {{ display: inline-block; transition: transform .2s; }}
.expand-btn.open .chevron {{ transform: rotate(180deg); }}
.detail {{ display: none; margin-top: .875rem; padding-top: .875rem; border-top: 0.5px solid var(--border); }}
.detail.open {{ display: block; }}

.lead {{
  font-size: 13px; color: var(--text2); line-height: 1.7;
  margin-bottom: 1.5rem; padding: 1rem 1.25rem;
  background: var(--surface); border: 0.5px solid var(--border);
  border-radius: 10px; border-left: 3px solid var(--accent);
}}
.lead strong {{ color: var(--text); font-weight: 500; }}

.timeline {{ position: relative; padding-left: 24px; margin-top: .5rem; }}
.timeline::before {{
  content: ''; position: absolute; left: 5px; top: 6px; bottom: 6px;
  width: 1px; background: var(--border2);
}}
.tl-item {{ position: relative; margin-bottom: 1.1rem; }}
.tl-dot {{
  position: absolute; left: -21px; top: 5px;
  width: 9px; height: 9px; border-radius: 50%;
  border: 1.5px solid var(--border2); background: var(--surface);
}}
.tl-dot.past    {{ background: var(--text2); border-color: var(--text2); }}
.tl-dot.current {{ background: var(--amber); border-color: var(--amber); box-shadow: 0 0 0 3px var(--amber-light); }}
.tl-date  {{ font-size: 11px; color: var(--text3); margin-bottom: 2px; }}
.tl-event {{ font-size: 14px; color: var(--text); font-weight: 500; line-height: 1.4; }}
.tl-sub   {{ font-size: 12px; color: var(--text2); margin-top: 3px; line-height: 1.5; }}

.section-label {{
  font-size: 10px; font-weight: 500; letter-spacing: .1em;
  text-transform: uppercase; color: var(--text3);
  margin-bottom: 1rem; margin-top: .25rem;
}}

.empty-state {{
  text-align: center; padding: 3rem 1rem; color: var(--text3); font-size: 14px;
}}

.site-footer {{
  border-top: 0.5px solid var(--border); padding: 1.5rem 2rem;
  text-align: center; font-size: 12px; color: var(--text3);
}}
.site-footer a {{ color: var(--text2); }}

@media (max-width: 600px) {{
  .site-header {{ padding: 2rem 1.25rem 2rem; }}
  .container {{ padding: 1.5rem 1.25rem 3rem; }}
  .stats-row {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
</head>
<body>

<header class="site-header">
  <div class="header-inner">
    <div class="header-eyebrow">City of Chico · Automated Tracker</div>
    <h1 class="header-title">Council Watch<br><em>Live Dashboard</em></h1>
    <div class="header-meta">
      <span>📍 421 Main Street, Chico, CA</span>
      <span>🔄 Updates twice daily via GitHub Actions</span>
    </div>
    <div class="update-pill">
      <span class="live-dot"></span>
      Last updated {updated_fmt}
    </div>
  </div>
</header>

<div class="container">

  <div class="stats-row">
    <div class="stat">
      <div class="stat-label">Meetings tracked</div>
      <div class="stat-val">{len(meetings)}</div>
      <div class="stat-sub">Agendas + minutes</div>
    </div>
    <div class="stat">
      <div class="stat-label">Recurring items</div>
      <div class="stat-val">{len(bills)}</div>
      <div class="stat-sub">{tracked_active} currently active</div>
    </div>
    <div class="stat">
      <div class="stat-label">Most recent</div>
      <div class="stat-val" style="font-size:1.4rem">{recent_date}</div>
      <div class="stat-sub">{recent_title[:40]}{"…" if len(recent_title)>40 else ""}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Next meeting</div>
      <div class="stat-val" style="font-size:1.4rem">{next_date_fmt}</div>
      <div class="stat-sub">Per published agenda</div>
    </div>
  </div>

  <div class="tabs-wrap">
    <div class="tabs" role="tablist">
      <button class="tab-btn active" onclick="showTab('latest', this)">Latest Meeting</button>
      <button class="tab-btn" onclick="showTab('bills', this)">Bill Tracker</button>
      <button class="tab-btn" onclick="showTab('history', this)">All Meetings</button>
    </div>
  </div>

  <!-- ════ LATEST MEETING ════ -->
  <div id="latest" class="panel active">
    <div class="lead">
      <strong>{recent_title}</strong><br>
      Showing agenda items from the most recently published meeting ({recent_date}).
      {"Minutes are available." if recent_meeting.get("has_minutes") else "Minutes not yet published."}
    </div>
    <div class="section-label">Agenda items</div>
    {recent_cards_html}
  </div>

  <!-- ════ BILL TRACKER ════ -->
  <div id="bills" class="panel">
    <div class="lead">
      Items that appear on <strong>multiple meeting agendas</strong> are tracked here as recurring bills.
      The tracker detects them by comparing agenda item titles across meetings using fuzzy matching.
      <strong>{len(bills)} recurring items</strong> detected so far.
    </div>
    <div class="section-label">Tracked items — sorted by most recent appearance</div>
    {bill_cards_html}
  </div>

  <!-- ════ ALL MEETINGS ════ -->
  <div id="history" class="panel">
    <div class="lead">
      All meetings scraped from the Granicus RSS feed, newest first.
      <strong>{len(meetings)} total</strong>.
    </div>
    <div class="section-label">Meeting history</div>
    {meeting_cards_html}
  </div>

</div>

<footer class="site-footer">
  Source: <a href="https://chico-ca.granicus.com/ViewPublisher.php?view_id=2" target="_blank">Chico Granicus</a>
  · Data updated automatically twice daily
  · <a href="https://github.com/eliassantiagomyers-glitch/Chico-scraper" target="_blank">GitHub</a>
</footer>

<script>
function showTab(id, btn) {{
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}}
function toggle(id, btn) {{
  const el = document.getElementById(id);
  const isOpen = el.classList.toggle('open');
  btn.classList.toggle('open', isOpen);
}}
</script>
</body>
</html>"""


def main():
    if not STATE_FILE.exists():
        print(f"ERROR: {STATE_FILE} not found. Run scraper.py first.")
        return
    state = json.loads(STATE_FILE.read_text())
    html  = build(state)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Dashboard written → {OUTPUT}")


if __name__ == "__main__":
    main()
