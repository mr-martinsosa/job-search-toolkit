# Follow-up Playbook

`dashboard.py` tells you *which* applications are overdue (red). This tells you *what to send*.

The principle: **lead with value, not the ask.** A follow-up that re-states a concrete,
relevant proof point reads as "still interested and worth a reply"; a "just checking in" reads
as noise.

---

## First follow-up (4 sentences, < 150 words, with a subject line)
- **S1:** name the company + role + when you applied.
- **S2:** ONE concrete, quantified value-add tied to the JD or a resume proof point.
- **S3:** soft ask + a specific availability window ("this week" / "next Tuesday").
- **S4 (optional):** a brief mention of a relevant recent project.

Professional but warm — **not** desperate. Reference something specific to *that* company.

### 🚫 Banned phrases (never use)
`just checking in` · `just following up` · `touching base` · `circling back`

### Example tone
> **Subject:** Re: {Role} — {Company}
>
> Hi [name or team],
> I submitted my application for the {Role} on {date}. I wanted to share that my
> {specific quantified proof point — e.g. cutting median page load from 3.1s to 0.9s for
> ~40k weekly users} closely mirrors the {specific thing from the JD}.
> I'd love to discuss how my {X yrs / skill} could contribute to {Company}'s {platform/team}.
> Would any time this week work for a brief conversation?
> Best, [Your name]

### LinkedIn variant (if you can't find an email)
3 sentences, 300-char max: hook → proof point → soft ask.

---

## Second follow-up (only if the first got no reply)
- Shorter — 2–3 sentences.
- **New angle:** share an insight, a relevant article, or a project update. Do NOT repeat the first.
- Still name the role.

## Cold (after 2 follow-ups, no reply) — STOP emailing recruiting
Don't draft a third. Instead:
- If the role was filled → mark the row `rejected`/discarded.
- **For a `referred` row that went cold → ask your referrer to nudge internally.** (This is the
  referral-first move — a warm internal ping beats another cold email every time.)
- Otherwise keep the row but deprioritize it.

---

## Cadence (matches `dashboard.py`'s `FOLLOWUP_CADENCE`)
| Stage | First follow-up | Then | Stop after |
|---|---|---|---|
| applied | 7 days | every 7 days | 2 attempts → cold |
| referred | 5 days | (nudge the referrer, don't cold-email) | — |
| screen / onsite | 2 days (thank-you within 1 day) | every 3 days | — |

**Record discipline:** only log a follow-up you *actually sent* — never log a draft as sent.
When you log one, append it to the row's notes (e.g. `followup 06-17 sent`) so you can see how
many attempts a row has had.

---

## Pre-submit ATS check (one habit worth keeping)
When you export a tailored resume to PDF, confirm the text layer is machine-readable so ATS
keyword matching works:
```bash
pdftotext resume.pdf - | head -40   # keywords should be extractable, not mangled
```
Avoid fancy ligatures / em-dash variants / smart quotes that break ATS text extraction.
(`md_to_pdf.py` already normalizes these for you.)
