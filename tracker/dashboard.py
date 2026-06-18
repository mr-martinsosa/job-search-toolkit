#!/usr/bin/env python3
"""Generate a self-contained job-search dashboard from the tracker CSVs.

Reads tracker/applications.csv (and optionally the leads.csv files) and writes a
single dashboard.html with the data inlined as JSON — no build step, no server,
no dependencies, no network. Double-click the HTML, or use --serve for a tab
that picks up edits on refresh.

Local-first by design: your data lives in your repo, scoring is yours to fill
in, and nothing here scrapes a job board or auto-submits anything.

Usage:
    python3 tracker/dashboard.py                 # write tracker/dashboard.html
    python3 tracker/dashboard.py --leads         # also include a Leads tab
    python3 tracker/dashboard.py --serve         # build + serve on localhost:8765
    python3 tracker/dashboard.py --open OUT.html # custom output path

Optional per-row score: add a `score` column to the CSV, or write `score: 4.5`
(or a leading `[4.5]`) in the notes — it shows up in the Score column. No score
is fine; the column just stays blank.
"""
import argparse
import csv
import json
import os
import re
import sys
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
APPLICATIONS = os.path.join(HERE, "applications.csv")
LEADS_FILES = ["leads.csv"]

# Status pipeline (matches README): lead -> applied -> referred -> screen -> onsite -> offer / rejected
STATUS_ORDER = ["lead", "applied", "referred", "screen", "onsite", "offer", "rejected"]
# Days after the relevant date that a follow-up becomes due, by status.
FOLLOWUP_CADENCE = {"applied": 7, "referred": 5, "screen": 2, "onsite": 2}

SCORE_RE = re.compile(r"(?:\bscore\s*[:=]\s*|^\s*\[)\s*([0-5](?:\.\d)?)", re.IGNORECASE)
FOLLOWUP_NOTE_RE = re.compile(r"follow[\s-]*up\s+(\d{1,2})[/-](\d{1,2})", re.IGNORECASE)
REFERRAL_RE = re.compile(r"referr|referral|intro|warm", re.IGNORECASE)


def parse_score(row):
    if row.get("score"):
        m = re.search(r"[0-5](?:\.\d)?", row["score"])
        if m:
            return float(m.group(0))
    m = SCORE_RE.search(row.get("notes", "") or "")
    return float(m.group(1)) if m else None


def parse_followup_note(notes):
    """Return an explicit 'follow up MM-DD' date from notes as MM-DD, if present."""
    m = FOLLOWUP_NOTE_RE.search(notes or "")
    if not m:
        return None
    mm, dd = int(m.group(1)), int(m.group(2))
    if 1 <= mm <= 12 and 1 <= dd <= 31:
        return f"{mm:02d}-{dd:02d}"
    return None


CSV_FIELDS = ["company", "role", "location", "url", "status", "applied_date", "source", "notes"]


def load_csv(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, newline="", encoding="utf-8") as f:
        first = f.readline()
        f.seek(0)
        # leads*.csv ship without a header row; applications.csv has one.
        has_header = first.lower().startswith("company,role")
        reader = csv.DictReader(f) if has_header else csv.DictReader(f, fieldnames=CSV_FIELDS)
        for row in reader:
            company = (row.get("company") or "").strip()
            if not company or company.upper().startswith("EXAMPLE"):
                continue  # skip the template placeholder row
            rows.append({
                "company": company,
                "role": (row.get("role") or "").strip(),
                "location": (row.get("location") or "").strip(),
                "url": (row.get("url") or "").strip(),
                "status": (row.get("status") or "lead").strip().lower(),
                "applied_date": (row.get("applied_date") or "").strip(),
                "source": (row.get("source") or "").strip(),
                "notes": (row.get("notes") or "").strip(),
                "score": parse_score(row),
                "followup_note": parse_followup_note(row.get("notes")),
                "referral": bool(REFERRAL_RE.search(row.get("notes") or "")),
            })
    return rows


def summarize(rows):
    counts = {s: 0 for s in STATUS_ORDER}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return counts


def build(applications, leads, out_path, include_leads):
    payload = {
        "applications": applications,
        "leads": leads if include_leads else [],
        "summary": summarize(applications),
        "statusOrder": STATUS_ORDER,
        "cadence": FOLLOWUP_CADENCE,
        "includeLeads": include_leads,
    }
    html = HTML_TEMPLATE.replace("/*__DATA__*/", json.dumps(payload))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


def serve(out_path, port=8765):
    import http.server
    import socketserver
    os.chdir(os.path.dirname(out_path))
    name = os.path.basename(out_path)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        url = f"http://127.0.0.1:{port}/{name}"
        print(f"Serving {name} at {url}  (Ctrl-C to stop)")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped.")


def main():
    ap = argparse.ArgumentParser(description="Build the job-search tracker dashboard.")
    ap.add_argument("--leads", action="store_true", help="include a Leads tab from the leads*.csv files")
    ap.add_argument("--serve", action="store_true", help="build then serve on localhost and open a browser")
    ap.add_argument("--open", dest="out", default=os.path.join(HERE, "dashboard.html"), help="output HTML path")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()

    applications = load_csv(APPLICATIONS)
    leads = []
    if args.leads:
        seen = set()
        for name in LEADS_FILES:
            for r in load_csv(os.path.join(HERE, name)):
                key = (r["company"], r["role"])
                if key not in seen:
                    seen.add(key)
                    leads.append(r)

    out = build(applications, leads, args.out, args.leads)
    print(f"wrote {out}  ({len(applications)} applications"
          + (f", {len(leads)} leads" if args.leads else "") + ")")
    if args.serve:
        serve(out, args.port)
    else:
        print(f"open it:  xdg-open {out}    (or: python3 {os.path.relpath(__file__, os.getcwd())} --serve)")


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>job pipeline</title>
<style>
  :root{
    --bg:#0b0e14; --panel:#11151f; --panel2:#161b27; --line:#222a39;
    --fg:#e6e9f0; --muted:#8b95a7; --accent:#7cc4ff; --accent2:#9d7cff;
    --good:#5ad19a; --warn:#f0c674; --bad:#ff7a85; --pill:#1d2433;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);
    font:14px/1.45 ui-monospace,SFMono-Regular,"JetBrains Mono",Menlo,Consolas,monospace}
  header{padding:18px 22px 6px;border-bottom:1px solid var(--line);
    position:sticky;top:0;background:linear-gradient(180deg,#0b0e14,#0b0e14ee);backdrop-filter:blur(6px);z-index:5}
  h1{margin:0;font-size:18px;letter-spacing:.02em}
  h1 .dot{color:var(--accent)}
  .tag{color:var(--muted);font-size:12px;margin-top:3px}
  nav{display:flex;gap:6px;margin-top:12px}
  nav button{background:transparent;border:1px solid var(--line);color:var(--muted);
    padding:6px 14px;border-radius:7px;cursor:pointer;font:inherit;font-size:13px}
  nav button.active{color:var(--fg);border-color:var(--accent);background:var(--panel2)}
  .wrap{padding:16px 22px 60px}
  .badges{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 16px}
  .badge{background:var(--panel);border:1px solid var(--line);border-radius:8px;
    padding:8px 12px;min-width:96px}
  .badge .n{font-size:20px;font-weight:600}
  .badge .l{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}
  .badge[data-s="offer"] .n{color:var(--good)} .badge[data-s="rejected"] .n{color:var(--bad)}
  .badge[data-s="onsite"] .n,.badge[data-s="screen"] .n{color:var(--accent)}
  .badge[data-s="referred"] .n{color:var(--accent2)}
  .controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
  input[type=search],select{background:var(--panel);border:1px solid var(--line);color:var(--fg);
    padding:8px 11px;border-radius:7px;font:inherit;font-size:13px}
  input[type=search]{min-width:240px}
  .hint{color:var(--muted);font-size:12px;margin-left:auto}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
  th{color:var(--muted);font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.05em;
    cursor:pointer;user-select:none;white-space:nowrap;position:sticky;top:118px;background:var(--bg)}
  th.sorted::after{content:" \25B4";color:var(--accent)} th.sorted.desc::after{content:" \25BE"}
  tr:hover td{background:var(--panel)}
  td.num{color:var(--muted);font-variant-numeric:tabular-nums}
  .co{font-weight:600}
  .role{color:var(--fg)} .loc{color:var(--muted);font-size:12px}
  a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
  .pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;
    background:var(--pill);border:1px solid var(--line);white-space:nowrap}
  .st-lead{color:var(--muted)} .st-applied{color:var(--accent)}
  .st-referred{color:var(--accent2);border-color:#3a2f5e}
  .st-screen,.st-onsite{color:var(--accent);border-color:#27425e}
  .st-offer{color:var(--good);border-color:#235} .st-rejected{color:var(--bad);opacity:.8}
  .score{font-weight:600;font-variant-numeric:tabular-nums}
  .score.hi{color:var(--good)} .score.mid{color:var(--warn)} .score.lo{color:var(--muted)}
  .ref{margin-left:6px;color:var(--accent2);font-size:11px}
  .fu{font-size:11px;white-space:nowrap}
  .fu.over{color:var(--bad);font-weight:600} .fu.soon{color:var(--warn)} .fu.ok{color:var(--muted)}
  .notes{color:var(--muted);font-size:12px;max-width:380px}
  .empty{color:var(--muted);padding:40px;text-align:center}
  footer{color:var(--muted);font-size:11px;padding:16px 22px;border-top:1px solid var(--line)}
  .star{color:var(--warn)}
</style>
</head>
<body>
<header>
  <h1><span class="dot">&#9679;</span> job pipeline</h1>
  <div class="tag">git-backed &middot; data lives in your repo &middot; official APIs only, no scraping &middot; nothing auto-submits</div>
  <nav id="nav"></nav>
</header>
<div class="wrap">
  <div class="badges" id="badges"></div>
  <div class="controls">
    <input type="search" id="q" placeholder="filter company / role / notes&hellip;">
    <select id="statusFilter"><option value="">all statuses</option></select>
    <select id="extra">
      <option value="">&mdash; quick views &mdash;</option>
      <option value="referral">has referral / intro</option>
      <option value="followup">follow-up due</option>
      <option value="scored">scored 4.0+</option>
    </select>
    <span class="hint" id="count"></span>
  </div>
  <table id="tbl">
    <thead><tr id="head"></tr></thead>
    <tbody id="body"></tbody>
  </table>
  <div class="empty" id="empty" style="display:none">no rows match.</div>
</div>
<footer id="foot"></footer>
<script>
const DATA = /*__DATA__*/;
const COLS = [
  {k:"i",      t:"#",        cls:"num", get:(r,i)=>i+1},
  {k:"applied_date", t:"date", get:r=>r.applied_date||"—"},
  {k:"company",t:"company",   html:r=>`<span class="co">${esc(r.company)}</span>`+(r.referral?`<span class="ref" title="referral / intro">◈</span>`:"")},
  {k:"role",   t:"role",      html:r=>`<span class="role">${r.url?`<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.role||"(role)")}</a>`:esc(r.role||"")}</span>`},
  {k:"location",t:"location", cls:"loc", get:r=>r.location||""},
  {k:"score",  t:"score",     html:r=>scoreCell(r.score)},
  {k:"status", t:"status",    html:r=>`<span class="pill st-${esc(r.status)}">${esc(r.status)}</span>`},
  {k:"source", t:"source",    cls:"loc", get:r=>r.source||""},
  {k:"followup",t:"follow-up",html:r=>fuCell(r)},
  {k:"notes",  t:"notes",     cls:"notes", get:r=>r.notes||""},
];
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function scoreCell(s){ if(s==null) return `<span class="score lo">—</span>`;
  const c = s>=4? "hi": s>=3.5? "mid":"lo"; return `<span class="score ${c}">${s.toFixed(1)}</span>`; }

function followup(r){ // returns {label, state, days} or null
  if(["lead","offer","rejected"].includes(r.status)) return null;
  const today = new Date(); today.setHours(0,0,0,0);
  let due = null;
  if(r.followup_note){ const [mm,dd]=r.followup_note.split("-").map(Number);
    due = new Date(today.getFullYear(), mm-1, dd); }
  else if(r.applied_date){ const d=new Date(r.applied_date+"T00:00:00");
    if(!isNaN(d)){ const add=DATA.cadence[r.status]||7; due=new Date(d); due.setDate(due.getDate()+add); } }
  if(!due||isNaN(due)) return null;
  const days = Math.round((due-today)/864e5);
  const state = days<0? "over": days<=2? "soon":"ok";
  const label = days<0? `${-days}d overdue`: days===0? "due today": `in ${days}d`;
  return {label,state,days};
}
function fuCell(r){ const f=followup(r); if(!f) return `<span class="fu ok">—</span>`;
  return `<span class="fu ${f.state}">${f.label}</span>`; }

let view = "applications", sortKey="i", sortDesc=false, rowsCache=[];

function setView(v){ view=v; sortKey = v==="leads"?"company":"i"; sortDesc=false;
  document.querySelectorAll("#nav button").forEach(b=>b.classList.toggle("active",b.dataset.v===v));
  render(); }

function buildNav(){
  const nav=document.getElementById("nav");
  const tabs=[["applications",`pipeline (${DATA.applications.length})`]];
  if(DATA.includeLeads && DATA.leads.length) tabs.push(["leads",`leads (${DATA.leads.length})`]);
  nav.innerHTML="";
  tabs.forEach(([v,label])=>{ const b=document.createElement("button");
    b.dataset.v=v; b.textContent=label; b.onclick=()=>setView(v); nav.appendChild(b); });
  nav.firstChild.classList.add("active");
}
function buildBadges(){
  const wrap=document.getElementById("badges"); wrap.innerHTML="";
  const total=DATA.applications.length;
  const all=document.createElement("div"); all.className="badge";
  all.innerHTML=`<div class="n">${total}</div><div class="l">in pipeline</div>`; wrap.appendChild(all);
  DATA.statusOrder.forEach(s=>{ const n=DATA.summary[s]||0; if(!n && s!=="applied"&&s!=="rejected") return;
    const d=document.createElement("div"); d.className="badge"; d.dataset.s=s;
    d.innerHTML=`<div class="n">${n}</div><div class="l">${s}</div>`; wrap.appendChild(d); });
  const sf=document.getElementById("statusFilter");
  sf.innerHTML='<option value="">all statuses</option>'+DATA.statusOrder.map(s=>`<option>${s}</option>`).join("");
}
function buildHead(){
  const h=document.getElementById("head"); h.innerHTML="";
  COLS.forEach(c=>{ const th=document.createElement("th"); th.textContent=c.t;
    if(sortKey===c.k){ th.classList.add("sorted"); if(sortDesc) th.classList.add("desc"); }
    th.onclick=()=>{ if(sortKey===c.k) sortDesc=!sortDesc; else {sortKey=c.k;sortDesc=false;} render(); };
    h.appendChild(th); });
}
function sortVal(r,k){
  if(k==="score") return r.score==null?-1:r.score;
  if(k==="followup"){ const f=followup(r); return f?f.days:9999; }
  if(k==="i") return 0;
  return (r[k]||"").toString().toLowerCase();
}
function currentRows(){ return view==="leads"?DATA.leads:DATA.applications; }
function render(){
  buildHead();
  let rows=currentRows().slice();
  const q=document.getElementById("q").value.trim().toLowerCase();
  const sfv=document.getElementById("statusFilter").value;
  const xv=document.getElementById("extra").value;
  if(q) rows=rows.filter(r=>[r.company,r.role,r.location,r.notes,r.source].join(" ").toLowerCase().includes(q));
  if(sfv) rows=rows.filter(r=>r.status===sfv);
  if(xv==="referral") rows=rows.filter(r=>r.referral);
  if(xv==="followup") rows=rows.filter(r=>{const f=followup(r);return f&&f.days<=2;});
  if(xv==="scored") rows=rows.filter(r=>r.score!=null&&r.score>=4);
  if(sortKey!=="i") rows.sort((a,b)=>{const x=sortVal(a,sortKey),y=sortVal(b,sortKey);
    return (x<y?-1:x>y?1:0)*(sortDesc?-1:1);});
  rowsCache=rows;
  const body=document.getElementById("body"); body.innerHTML="";
  rows.forEach((r,i)=>{ const tr=document.createElement("tr");
    COLS.forEach(c=>{ const td=document.createElement("td"); if(c.cls) td.className=c.cls;
      td.innerHTML = c.html? c.html(r,i): esc(c.get?c.get(r,i):r[c.k]); tr.appendChild(td); });
    body.appendChild(tr); });
  document.getElementById("empty").style.display=rows.length?"none":"block";
  document.getElementById("count").textContent=`${rows.length} / ${currentRows().length} shown`;
}
function buildFooter(){
  const over=DATA.applications.filter(r=>{const f=followup(r);return f&&f.days<0;}).length;
  const refs=DATA.applications.filter(r=>r.referral).length;
  document.getElementById("foot").innerHTML =
    `${over?`<span class="star">★</span> ${over} follow-up${over>1?"s":""} overdue &middot; `:""}`+
    `${refs} with a referral lead &middot; built by tracker/dashboard.py from your CSVs &middot; `+
    `a referral converts ~10× a cold application — work those first.`;
}
buildNav(); buildBadges(); buildFooter();
["q","statusFilter","extra"].forEach(id=>document.getElementById(id).addEventListener("input",render));
render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(main())
