# job-search-toolkit

A set of small Python scripts I use to run my own job search. They help with the parts that
actually move the needle (tailoring a resume, finding real openings, tracking follow-ups)
rather than blasting out applications. There are no dependencies to install and nothing here
scrapes a job board.

The four scripts:

1. `tools/tailor.py` — tailor your resume to a specific posting
2. `tools/aggregate.py` — pull fresh openings from official ATS APIs
3. `tools/md_to_pdf.py` — turn a Markdown resume into an ATS-readable PDF
4. `tracker/dashboard.py` — build an HTML dashboard of your pipeline

![Pipeline dashboard showing status badges, fit scores, follow-up highlighting and referral markers](docs/dashboard.png)

<sub>That screenshot is generated from the fictional sample data in `tracker/`. Run `python3 tracker/dashboard.py --leads --serve` to see it yourself.</sub>

A note on the "no scraping" choice: LinkedIn, Indeed, and Workday all prohibit it and
shadow-filter bots anyway, so every source here is a company's own public job-board API. I
wrote these because the thing holding up a job search is usually the resume and referrals, not
how many applications you can fire off.

## Prerequisites

You need Python 3.9 or newer. Check with `python3 --version`. There's nothing to `pip install`
and no virtualenv to set up.

`tools/tailor.py` is the one exception: it calls the Anthropic API, so it needs an
`ANTHROPIC_API_KEY` (grab one from the [Anthropic Console](https://console.anthropic.com/)).
The other three scripts don't touch any API.

## Clone & run

```bash
git clone https://github.com/<your-username>/job-search-toolkit.git
cd job-search-toolkit
python3 --version          # confirm 3.9+

# 1. Find fresh postings (official APIs only)
python3 tools/aggregate.py --keywords react node typescript --remote

# 2. Export your Markdown resume to an ATS-clean PDF
python3 tools/md_to_pdf.py examples/resume.md /tmp/resume.pdf

# 3. Tailor your resume to a specific posting (needs an Anthropic API key)
export ANTHROPIC_API_KEY=sk-ant-...
python3 tools/tailor.py examples/job_description.txt --resume examples/resume.md

# 4. Build the pipeline dashboard from the included sample data
python3 tracker/dashboard.py --leads --serve
```

Everything runs against the bundled sample data, so you can try each script before adding any
of your own. Once you've had a look, swap `examples/resume.md` for your real resume, edit the
company slug lists at the top of `tools/aggregate.py`, and start logging applications in
`tracker/applications.csv`.

## The four scripts

### `tools/tailor.py`
Reads your resume and a job description and tells you how well they match. It pulls out the
keywords the posting cares about that your resume already supports but doesn't emphasize,
rewrites your own bullets to use the posting's wording, and lists the genuine gaps. It won't
make anything up: if the posting wants something your resume doesn't have, it reports that as a
gap instead of inventing experience. This is the only script that calls an API; the system
prompt and resume are cached so repeated runs stay cheap.

### `tools/aggregate.py`
Pulls openings from Greenhouse, Lever, Ashby, Recruitee, SmartRecruiters, Workable, and
RemoteOK, all through each company's own public API or feed. You can filter by keyword,
location, and remote, and it drops anything above the seniority level you set. Results are
de-duplicated by URL and can be appended straight to a tracker CSV. To follow a company, add
its careers-URL slug to the lists at the top of the file.

### `tools/md_to_pdf.py`
Builds a PDF from Markdown without any library. It writes the raw PDF objects and cross-
reference table directly, using the standard Helvetica fonts so the text stays selectable.
That matters because applicant tracking systems read the text layer, so running
`pdftotext out.pdf -` should give back clean, parseable text. It handles headings, bullets,
bold and italic, wrapping, and page breaks, and it normalizes smart quotes and em dashes that
otherwise break text extraction.

### `tracker/dashboard.py`
Reads your tracker CSVs and writes a single `dashboard.html` with the data baked in as JSON, so
there's no server or network involved. You get status badges, a sortable and filterable table,
overdue follow-ups highlighted in red, per-row fit scores, and a marker on rows that have a
referral.

```bash
# Build the HTML (writes tracker/dashboard.html); --leads adds a Leads tab
python3 tracker/dashboard.py --leads

# ...or build and open it on a local server that picks up CSV edits on refresh
python3 tracker/dashboard.py --leads --serve     # http://127.0.0.1:8765  (Ctrl-C to stop)
```

Since `dashboard.html` is self-contained, you can also just open the built file:

```bash
xdg-open tracker/dashboard.html        # Linux
open tracker/dashboard.html            # macOS
explorer.exe "$(wslpath -w tracker/dashboard.html)"   # Windows (WSL)
```

Once it's open, click the `score` or `follow-up` headers to sort, use the quick-views dropdown
(`follow-up due`, `has referral / intro`, `scored 4.0+`), and type in the filter box to search
company, role, or notes. The generated `dashboard.html` is gitignored, since it's rebuilt from
your CSVs whenever you want.

## Playbooks (`playbooks/`)

Three short reference docs you apply by hand, no API involved:

- `scoring_rubric.md` — a 1–5 fit score plus a ghost-job legitimacy check, to help decide which
  leads are worth your tailoring and referral effort. The scores feed straight into the dashboard.
- `outreach_templates.md` — four templates for referral outreach, kept under LinkedIn's
  300-character connection-request limit.
- `followup_playbook.md` — what to send when the dashboard flags a follow-up as overdue,
  including phrases to avoid and when to stop.

## How I prioritize

Roughly in this order: fix the resume first, then chase referrals, then tailor each
application, and only worry about volume once the rest is working. Automating a resume that's
getting rejected just produces rejections faster, so it's worth getting that right before
scaling anything up.

## License

MIT, see [LICENSE](LICENSE).
