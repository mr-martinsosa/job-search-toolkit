# job-search-toolkit

A small, dependency-free, ToS-respecting toolkit for running a job search that gets
*callbacks* — not a mass-apply bot. Every tool is **pure-Python standard library**: no
`pip install`, no Node, no build step, no account, no scraping. Clone it and run.

It does four things, in order of impact:

1. **Tailor** your resume to a posting — ethically (`tools/tailor.py`)
2. **Aggregate** fresh postings from official ATS APIs (`tools/aggregate.py`)
3. **Export** a clean, ATS-readable PDF from a Markdown resume (`tools/md_to_pdf.py`)
4. **Track** the whole pipeline in a self-contained HTML dashboard (`tracker/dashboard.py`)

![The pipeline dashboard — status badges, fit scores, follow-up highlighting, and referral markers, generated from your tracker CSVs](docs/dashboard.png)

<sub>The dashboard above is generated from the fictional sample data in `tracker/` — run `python3 tracker/dashboard.py --leads --serve` to see it.</sub>

> Why "no scraping"? LinkedIn / Indeed / Workday prohibit it in their ToS and shadow-filter
> bots anyway. Every source here is a company's own public job-board API. The whole toolkit
> is built on the premise that the bottleneck in a job search is **resume credibility +
> referrals**, not application volume.

---

## Quick start

```bash
git clone <this-repo> && cd job-search-toolkit
python3 --version   # 3.9+; that's the only requirement

# 1. Find fresh postings (official APIs only)
python3 tools/aggregate.py --keywords react node typescript --remote

# 2. Export your Markdown resume to an ATS-clean PDF
python3 tools/md_to_pdf.py examples/resume.md /tmp/resume.pdf

# 3. Tailor your resume to a specific posting (needs an Anthropic API key)
export ANTHROPIC_API_KEY=sk-ant-...
python3 tools/tailor.py examples/job_description.txt --resume examples/resume.md

# 4. Build the pipeline dashboard from your tracker CSVs
python3 tracker/dashboard.py --leads --serve
```

Replace `examples/resume.md` with your own resume and edit the company slug lists at the
top of `tools/aggregate.py` to target the companies you care about.

---

## The four tools

### `tools/tailor.py` — ethical ATS optimization
Scores how well your real resume matches a posting, surfaces the keywords the posting wants
that you *already* support (but don't emphasize), rewrites **your own** bullets to mirror the
posting's language, and lists honest gaps. **It will not invent experience** — when the
posting wants something your resume lacks, it flags it as a gap instead of fabricating it.
The only tool that calls an API (Anthropic); the static system prompt + resume are
prompt-cached so repeat runs are cheap.

### `tools/aggregate.py` — official-API job aggregator
Pulls postings from **Greenhouse, Lever, Ashby, Recruitee, SmartRecruiters, Workable**, and
RemoteOK — each a company's own public API or feed. Filters by keyword, location, remote, and
a seniority/title exclusion list; de-dupes by URL; optionally appends matches to a tracker
CSV. Add target companies by dropping their careers-URL slug into the lists at the top.

### `tools/md_to_pdf.py` — Markdown → ATS-clean PDF
Writes a valid PDF **by hand** (raw PDF objects + xref table, no library) using the base-14
Helvetica fonts so the text layer is fully selectable/extractable — `pdftotext out.pdf -`
returns clean keywords, which is exactly what an ATS parser does. Supports headings, bullets,
bold/italic, wrapping, and auto page breaks, and normalizes smart-quotes/em-dashes that
otherwise mangle ATS extraction.

### `tracker/dashboard.py` — self-contained pipeline dashboard
Reads your tracker CSVs and emits a single `dashboard.html` with the data inlined as JSON —
no server, no dependencies, no network. Status badges, a sortable/filterable table, a
follow-up-cadence highlighter (overdue rows turn red), per-row fit scores, and a referral
marker. `--serve` opens it on localhost; otherwise just double-click the file.

---

## Playbooks (`playbooks/`)
The toolkit's opinion, in three short docs you apply by hand (no API calls):
- **`scoring_rubric.md`** — a 1–5 fit score + a ghost-job legitimacy tier, so you spend
  tailoring/referral effort on the right leads. Scores wire straight into the dashboard.
- **`outreach_templates.md`** — four referral-outreach archetypes (a referral converts ~10×
  a cold apply) under LinkedIn's 300-char cap.
- **`followup_playbook.md`** — what to actually send when the dashboard flags a row overdue,
  including a banned-phrase list and a stop-after-2 rule.

---

## The honest priority order
1. **Resume fixes** (title framing, gaps, typos) — biggest lever, free, today.
2. **Referrals / networking** per target company — biggest conversion multiplier.
3. **Tailoring** per application — beats ATS keyword filters.
4. **Volume** — last, and only once the above are working.

A resume that triggers rejections will trigger them *faster* if you automate. Fix, then scale.

## Requirements
Python 3.9+. That's it. `tools/tailor.py` additionally needs an `ANTHROPIC_API_KEY`.

## License
MIT — see [LICENSE](LICENSE).
