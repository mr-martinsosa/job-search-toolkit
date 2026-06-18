# job-search-toolkit

A set of dependency-free Python scripts for running a job search: tailoring a resume to a
posting, finding openings through official ATS APIs, exporting an ATS-readable PDF, and tracking
the application pipeline. No third-party packages, no scraping.

## Features

| Script | Purpose |
|---|---|
| `tools/tailor.py` | Tailor a resume to a specific posting (Anthropic API). |
| `tools/aggregate.py` | Pull openings from official ATS APIs. |
| `tools/md_to_pdf.py` | Convert a Markdown resume to an ATS-readable PDF. |
| `tracker/dashboard.py` | Generate an HTML dashboard of the application pipeline. |

![Pipeline dashboard showing status badges, fit scores, follow-up highlighting and referral markers](docs/dashboard.png)

The dashboard above is generated from the fictional sample data in `tracker/`. Every source in
`aggregate.py` is a company's own public job-board API; LinkedIn, Indeed, and Workday are not
used, as they prohibit scraping.

## Requirements

- Python 3.9 or newer (`python3 --version`). No `pip install` or virtualenv required.
- `tools/tailor.py` additionally requires an `ANTHROPIC_API_KEY` from the
  [Anthropic Console](https://console.anthropic.com/). The other three scripts do not call any API.

## Installation

```bash
git clone https://github.com/mr-martinsosa/job-search-toolkit.git
cd job-search-toolkit
python3 --version          # confirm 3.9+
```

## Usage

The scripts run against the bundled sample data out of the box.

```bash
# 1. Find fresh postings (official APIs only)
python3 tools/aggregate.py --keywords react node typescript --remote

# 2. Export a Markdown resume to an ATS-clean PDF
python3 tools/md_to_pdf.py examples/resume.md /tmp/resume.pdf

# 3. Tailor a resume to a specific posting (requires an Anthropic API key)
export ANTHROPIC_API_KEY=sk-ant-...
python3 tools/tailor.py examples/job_description.txt --resume examples/resume.md

# 4. Build the pipeline dashboard from the included sample data
python3 tracker/dashboard.py --leads --serve
```

To use real data, replace `examples/resume.md` with an actual resume, edit the company slug
lists at the top of `tools/aggregate.py`, and record applications in `tracker/applications.csv`.

## Scripts

### `tools/tailor.py`

Compares a resume to a job description and reports the match. It surfaces the posting's keywords
that the resume already supports but does not emphasize, rewrites existing bullets to use the
posting's wording, and lists genuine gaps. It does not invent experience: when the posting
requires something the resume lacks, it reports a gap rather than fabricating content. This is
the only script that calls an API. The system prompt and resume are cached so repeated runs stay
cheap.

### `tools/aggregate.py`

Pulls openings from Greenhouse, Lever, Ashby, Recruitee, SmartRecruiters, Workable, and RemoteOK,
each through that company's own public API or feed. Results can be filtered by keyword, location,
and remote status, and titles above a configured seniority level are dropped. Matches are
de-duplicated by URL and can be appended to a tracker CSV. To follow a company, add its
careers-URL slug to the lists at the top of the file.

### `tools/md_to_pdf.py`

Builds a PDF from Markdown with no third-party library, writing the raw PDF objects and
cross-reference table directly. It uses the standard Helvetica fonts so the text layer stays
selectable, which keeps the output parseable by applicant tracking systems
(`pdftotext out.pdf -` returns clean text). It supports headings, bullets, bold and italic,
wrapping, and page breaks, and it normalizes smart quotes and em dashes that otherwise break
text extraction.

### `tracker/dashboard.py`

Reads the tracker CSVs and writes a single `dashboard.html` with the data inlined as JSON, so it
runs with no server and no network. The dashboard includes status badges, a sortable and
filterable table, overdue follow-ups highlighted in red, per-row fit scores, and a referral
marker.

```bash
# Build the HTML (writes tracker/dashboard.html); --leads adds a Leads tab
python3 tracker/dashboard.py --leads

# Build and serve on localhost, picking up CSV edits on refresh
python3 tracker/dashboard.py --leads --serve     # http://127.0.0.1:8765  (Ctrl-C to stop)
```

`dashboard.html` is self-contained and can also be opened directly:

```bash
xdg-open tracker/dashboard.html        # Linux
open tracker/dashboard.html            # macOS
explorer.exe "$(wslpath -w tracker/dashboard.html)"   # Windows (WSL)
```

Click the `score` or `follow-up` headers to sort, use the quick-views dropdown
(`follow-up due`, `has referral / intro`, `scored 4.0+`), and use the filter box to search
company, role, or notes. The generated `dashboard.html` is gitignored.

## Playbooks

Reference documents in `playbooks/`, applied by hand with no API calls:

- `scoring_rubric.md`: a 1-5 fit score plus a ghost-job legitimacy check, with results that feed
  into the dashboard's score column.
- `outreach_templates.md`: four referral-outreach templates, within LinkedIn's 300-character
  connection-request limit.
- `followup_playbook.md`: follow-up message guidance, including phrases to avoid and when to stop.

## License

MIT. See [LICENSE](LICENSE).
