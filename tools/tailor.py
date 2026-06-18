#!/usr/bin/env python3
"""
tailor.py — Tailor your resume to a specific job description, ethically.

This does NOT fabricate experience. It (1) scores how well your real resume matches a
posting, (2) surfaces the keywords/skills the posting wants that your resume already
supports but doesn't emphasize, and (3) rewrites YOUR existing bullets to mirror the
posting's language so they survive ATS keyword filters. It flags genuine gaps instead
of inventing experience to fill them.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 tools/tailor.py path/to/job_description.txt
    python3 tools/tailor.py --jd-stdin < job.txt
    python3 tools/tailor.py job.txt --resume examples/resume.md

No third-party packages required (uses urllib).
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

MODEL = os.environ.get("TAILOR_MODEL", "claude-opus-4-8")
API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_RESUME = os.path.join(
    os.path.dirname(__file__), "..", "examples", "resume.md"
)

SYSTEM = """You are a precise resume-tailoring assistant. Hard rules:
- NEVER invent jobs, titles, dates, metrics, or skills the candidate does not already have.
- Only rephrase, reorder, and re-emphasize the candidate's EXISTING resume content.
- When the posting wants something the resume genuinely lacks, list it as a GAP, do not fabricate it.
- Keep rewritten bullets truthful to the original meaning; you may mirror the posting's terminology only where it accurately describes existing work.
Output strict JSON matching the requested schema. No prose outside the JSON."""

USER_TEMPLATE = """Here is the candidate's resume:
<resume>
{resume}
</resume>

Here is the job description:
<job_description>
{jd}
</job_description>

Return JSON with exactly these keys:
{{
  "match_score": <int 0-100, honest fit estimate>,
  "verdict": "<one sentence: is this worth applying to and why>",
  "matched_keywords": ["keywords from the posting the resume already supports"],
  "missing_keywords": ["keywords from the posting the resume does NOT support"],
  "tailored_bullets": [
    {{"original": "<existing resume bullet>", "tailored": "<rewritten to mirror posting, still truthful>"}}
  ],
  "honest_gaps": ["real gaps the candidate should be ready to address in a screen"],
  "cover_note": "<3-4 sentence outreach note referencing the specific role, no fluff>"
}}"""


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def call_api(api_key, resume, jd):
    body = {
        "model": MODEL,
        "max_tokens": 2000,
        "system": [
            # Cache the static instructions + resume so repeated runs are cheap/fast.
            {"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}},
        ],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Candidate resume (stable across runs):\n" + resume,
                        "cache_control": {"type": "ephemeral"},
                    },
                    {"type": "text", "text": USER_TEMPLATE.format(resume="(above)", jd=jd)},
                ],
            }
        ],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"API error {e.code}: {e.read().decode('utf-8', 'replace')}")
    except urllib.error.URLError as e:
        sys.exit(f"Network error: {e.reason}")
    text = "".join(b.get("text", "") for b in data.get("content", []))
    # Strip accidental code fences.
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        sys.exit("Model did not return valid JSON:\n" + text)


def render(r):
    out = []
    out.append(f"\n=== MATCH: {r['match_score']}/100 ===")
    out.append(r["verdict"])
    out.append("\n-- Keywords you already cover --")
    out.append(", ".join(r["matched_keywords"]) or "(none)")
    out.append("\n-- Keywords the posting wants that you're missing --")
    out.append(", ".join(r["missing_keywords"]) or "(none)")
    out.append("\n-- Tailored bullets (paste into a per-role resume copy) --")
    for b in r["tailored_bullets"]:
        out.append(f"  • {b['tailored']}")
    out.append("\n-- Honest gaps to be ready for in a screen --")
    for g in r["honest_gaps"]:
        out.append(f"  ! {g}")
    out.append("\n-- Outreach note --")
    out.append(r["cover_note"])
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("jd_file", nargs="?", help="path to job description text file")
    ap.add_argument("--jd-stdin", action="store_true", help="read job description from stdin")
    ap.add_argument("--resume", default=DEFAULT_RESUME, help="path to resume file")
    ap.add_argument("--json", action="store_true", help="emit raw JSON")
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Set ANTHROPIC_API_KEY first:  export ANTHROPIC_API_KEY=sk-ant-...")

    if args.jd_stdin:
        jd = sys.stdin.read()
    elif args.jd_file:
        jd = read_text(args.jd_file)
    else:
        sys.exit("Provide a job description file or --jd-stdin")

    resume = read_text(args.resume)
    result = call_api(api_key, resume, jd)
    print(json.dumps(result, indent=2) if args.json else render(result))


if __name__ == "__main__":
    main()
