#!/usr/bin/env python3
"""
aggregate.py — Pull fresh job postings from OFFICIAL public APIs and filter them.

Sources are the companies' own public job-board APIs (Greenhouse, Lever, Ashby, Recruitee,
SmartRecruiters, Workable) plus RemoteOK's public API. No scraping of LinkedIn/Indeed/Workday
— those prohibit it and shadow-filter bots anyway. Add target companies to the slug lists below
(find the slug in their careers URL, e.g. boards.greenhouse.io/<slug>, jobs.lever.co/<slug>,
<slug>.recruitee.com, careers.smartrecruiters.com/<Slug>, apply.workable.com/<slug>).

Usage:
    python3 tools/aggregate.py                          # default keywords, prints table
    python3 tools/aggregate.py --keywords react node typescript
    python3 tools/aggregate.py --location "new york" --csv tracker/leads.csv
    python3 tools/aggregate.py --remote

No third-party packages required (uses urllib).
"""
import argparse
import csv
import json
import re
import sys
import urllib.request
import urllib.error

# --- Target companies (these are examples — edit freely) ---
# The slug is the name in the careers URL (boards.greenhouse.io/<slug>, jobs.lever.co/<slug>).
# Companies move ATS providers and open/close boards, so validate against the live API.
GREENHOUSE = [
    "stripe", "databricks", "airbnb", "figma", "gitlab", "dropbox", "robinhood",
    "instacart", "brex", "discord", "reddit", "datadog", "cloudflare", "anthropic",
    "asana", "lyft", "pinterest", "gusto", "affirm", "chime", "faire",
    "vercel", "postman", "flexport", "mongodb", "elastic", "twitch", "webflow",
    "airtable", "grafanalabs", "sofi",
]
LEVER = ["spotify", "kavak", "ro", "gopuff"]
ASHBY = []  # jobs.ashbyhq.com/<slug>
# --- Extra ATS providers (all official public JSON/feed APIs). ---
# Recruitee: <slug>.recruitee.com/api/offers/  (the slug is the careers subdomain).
RECRUITEE = ["channable", "hygraph"]
# SmartRecruiters: careers.smartrecruiters.com/<Slug>  — slugs are CASE-SENSITIVE PascalCase.
SMARTRECRUITERS = ["Visa"]
# Workable: apply.workable.com/<slug>  — public markdown feed (jobs.md). Add live slugs.
WORKABLE = []
# -----------------------------------------------------------------------------

UA = {"User-Agent": "job-search-aggregator/1.0 (personal job search)"}
# Default search terms — full-stack / React / TS / Node + AI integration. Override with --keywords.
DEFAULT_KEYWORDS = ["software engineer", "full stack", "full-stack", "react",
                    "frontend", "front end", "front-end", "backend", "node",
                    "typescript", "ai engineer"]
# Titles to filter out (above an IC/mid-level target). Edit to match the level you're targeting.
EXCLUDE_TITLE = ["staff", "principal", "director", "vp ", "vice president",
                 "head of", "manager", " lead", "lead ", "architect", "intern"]
# Optional company blocklist — any posting whose company matches is dropped, even if a slug
# for it is added to the lists above. Put companies you won't work for here (empty by default).
EXCLUDE_COMPANY = set()


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"  (skip {url}: {e})", file=sys.stderr)
        return None


def from_greenhouse(slug):
    data = fetch(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    if not data:
        return []
    return [
        {"company": slug, "title": j.get("title", ""),
         "location": (j.get("location") or {}).get("name", ""),
         "url": j.get("absolute_url", ""), "source": "greenhouse"}
        for j in data.get("jobs", [])
    ]


def from_lever(slug):
    data = fetch(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    if not data:
        return []
    return [
        {"company": slug, "title": j.get("text", ""),
         "location": (j.get("categories") or {}).get("location", ""),
         "url": j.get("hostedUrl", ""), "source": "lever"}
        for j in data
    ]


def from_ashby(slug):
    data = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
    if not data:
        return []
    rows = []
    for j in data.get("jobs", []):
        locs = [j.get("location") or ""] + [
            (s.get("location") if isinstance(s, dict) else str(s))
            for s in (j.get("secondaryLocations") or [])
        ]
        loc = " / ".join(x for x in locs if x)
        if j.get("isRemote"):
            loc = (loc + " (Remote)") if loc else "Remote"
        rows.append({"company": slug, "title": j.get("title", ""), "location": loc,
                     "url": j.get("jobUrl") or j.get("applyUrl", ""), "source": "ashby"})
    return rows


def fetch_text(url):
    """Like fetch() but returns raw text (for non-JSON feeds, e.g. Workable's jobs.md)."""
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", "replace")
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"  (skip {url}: {e})", file=sys.stderr)
        return None


def from_recruitee(slug):
    data = fetch(f"https://{slug}.recruitee.com/api/offers/")
    if not data:
        return []
    rows = []
    for j in data.get("offers", []):
        loc = j.get("location") or ", ".join(
            x for x in (j.get("city"), j.get("country")) if x)
        if j.get("remote"):
            loc = (loc + " (Remote)") if loc else "Remote"
        url = j.get("careers_url") or j.get("careers_apply_url") or j.get("url") or ""
        rows.append({"company": slug, "title": j.get("title", ""), "location": loc,
                     "url": url, "source": "recruitee"})
    return rows


def from_smartrecruiters(slug):
    # Public Posting API, paginated (limit=100). Slugs are case-sensitive PascalCase.
    rows, offset, page_size, max_pages = [], 0, 100, 50
    api_prefix = "https://api.smartrecruiters.com/v1/companies/"
    for _ in range(max_pages):
        data = fetch(f"{api_prefix}{slug}/postings?limit={page_size}&offset={offset}&status=PUBLIC")
        items = (data or {}).get("content") or []
        if not items:
            break
        for j in items:
            loc = j.get("location") or {}
            full = loc.get("fullLocation") or ", ".join(
                x for x in (loc.get("city"), loc.get("region"), loc.get("country")) if x)
            if loc.get("remote"):
                full = (full + ", Remote") if full else "Remote"
            ref = j.get("ref") or ""
            if ref.startswith(api_prefix):  # rewrite API ref -> public posting URL
                url = "https://jobs.smartrecruiters.com/" + ref[len(api_prefix):]
            elif j.get("id"):
                url = f"https://jobs.smartrecruiters.com/{slug}/{j['id']}"
            else:
                url = ""
            rows.append({"company": slug, "title": j.get("name", ""), "location": full,
                         "url": url, "source": "smartrecruiters"})
        if len(items) < page_size:
            break
        offset += page_size
    return rows


def from_workable(slug):
    # Workable's no-auth public surface is a markdown feed, not JSON. Table columns:
    # | Title | Department | Location | Type | Salary | Posted | Details([View](...)) |
    text = fetch_text(f"https://apply.workable.com/{slug}/jobs.md")
    if not text:
        return []
    rows = []
    for line in text.splitlines():
        if not line.startswith("|") or "[View]" not in line:
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) < 8:
            continue
        title = cols[1]
        if not title or title == "Title":  # header / separator row
            continue
        m = re.search(r"\[View\]\(([^)]+)\)", line)
        url = m.group(1) if m else ""
        if url.endswith(".md"):
            url = url[:-3]
        if not url.startswith("https://apply.workable.com/"):
            continue
        rows.append({"company": slug, "title": title, "location": cols[3] or "",
                     "url": url, "source": "workable"})
    return rows


def from_remoteok():
    data = fetch("https://remoteok.com/api")
    if not data or not isinstance(data, list):
        return []
    rows = []
    for j in data:
        if not isinstance(j, dict) or "position" not in j:
            continue  # first element is a legal/notice object
        rows.append({"company": j.get("company", ""), "title": j.get("position", ""),
                     "location": j.get("location", "Remote"),
                     "url": j.get("url", ""), "source": "remoteok"})
    return rows


def matches(job, keywords, location, remote_only, exclude=EXCLUDE_TITLE):
    if job["company"].lower().strip() in EXCLUDE_COMPANY:
        return False  # company blocklist
    title = job["title"].lower()
    if not any(k.lower() in title for k in keywords):
        return False
    if any(x in title for x in exclude):
        return False  # excluded title (seniority / intern)
    loc = job["location"].lower()
    if remote_only and "remote" not in loc and job["source"] != "remoteok":
        return False
    if location and location.lower() not in loc and "remote" not in loc:
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--keywords", nargs="+", default=DEFAULT_KEYWORDS)
    ap.add_argument("--location", default="", help="substring filter, e.g. 'new york'")
    ap.add_argument("--remote", action="store_true", help="remote roles only")
    ap.add_argument("--csv", help="append matches to this CSV (tracker-compatible)")
    ap.add_argument("--no-remoteok", action="store_true", help="skip RemoteOK source")
    args = ap.parse_args()

    jobs = []
    for slug in GREENHOUSE:
        print(f"Greenhouse: {slug}...", file=sys.stderr)
        jobs += from_greenhouse(slug)
    for slug in LEVER:
        print(f"Lever: {slug}...", file=sys.stderr)
        jobs += from_lever(slug)
    for slug in ASHBY:
        print(f"Ashby: {slug}...", file=sys.stderr)
        jobs += from_ashby(slug)
    for slug in RECRUITEE:
        print(f"Recruitee: {slug}...", file=sys.stderr)
        jobs += from_recruitee(slug)
    for slug in SMARTRECRUITERS:
        print(f"SmartRecruiters: {slug}...", file=sys.stderr)
        jobs += from_smartrecruiters(slug)
    for slug in WORKABLE:
        print(f"Workable: {slug}...", file=sys.stderr)
        jobs += from_workable(slug)
    if not args.no_remoteok:
        print("RemoteOK...", file=sys.stderr)
        jobs += from_remoteok()

    hits = [j for j in jobs if matches(j, args.keywords, args.location, args.remote)]
    # De-dup by url.
    seen, deduped = set(), []
    for j in hits:
        if j["url"] and j["url"] not in seen:
            seen.add(j["url"])
            deduped.append(j)

    print(f"\n{len(deduped)} matches (from {len(jobs)} postings scanned):\n")
    for j in deduped:
        print(f"  [{j['company']}] {j['title']}  —  {j['location']}\n      {j['url']}")

    if args.csv:
        # Tracker schema: company,role,location,url,status,applied_date,source,notes
        with open(args.csv, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for j in deduped:
                w.writerow([j["company"], j["title"], j["location"], j["url"],
                            "lead", "", j["source"], ""])
        print(f"\nAppended {len(deduped)} leads to {args.csv}")


if __name__ == "__main__":
    main()
