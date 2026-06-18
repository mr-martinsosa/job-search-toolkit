# Offer-Scoring & Ghost-Job Rubric

A 1–5 fit score + a separate ghost-job/legitimacy flag you apply by hand (no API call):
read a lead's JD next to your resume and produce a Global score and a legitimacy tier.
It exists to answer the only question that matters with a big lead pile — *which ones get
your referral + tailoring effort first.* You score from the JD text + the ATS JSON
`aggregate.py` already pulls; no scraping needed.

---

## Part 1 — The 1–5 Fit Score

Score each dimension 1–5 (5 = excellent/exact, 3 = partial/adjacent, 1 = poor/absent).
**Global = weighted average**, then subtract for red flags.

| Dimension | Weight | What it measures |
|---|---|---|
| **Match to resume** | 35% | Skills/experience/proof-points the JD asks for vs. what you can defend. Cite the exact resume line per requirement. |
| **Goal alignment** | 25% | Fit to your target: location/remote eligibility, level, and the role family you're aiming for. |
| **Comp** | 20% | 5 = top quartile for the level, 3 = at market, 1 = well below. Use levels.fyi / the posted band. |
| **Culture / remote** | 20% | Remote policy, stability, growth, team signals. |
| **Red flags** | − | Blockers (return-to-office, Staff-level reqs on a mid title, churn). Applied as a negative adjustment, not a positive weight. |

### Action thresholds (this is the prioritization knife)
- **4.5+** → strong match — apply now; worth a referral push and full tailoring.
- **4.0–4.4** → good match — apply.
- **3.5–3.9** → decent but not ideal — apply only if there's a specific reason (e.g. a warm contact).
- **< 3.5** → recommend against applying. Don't spend tailoring time here.

---

## Part 2 — Archetype detection (run FIRST; it changes *what* you weight in "Match")

Classify the JD into the closest archetype (or a hybrid of the two closest). It shifts which
proof points carry the Match dimension:

| Archetype | JD keyword signals | What to weight in Match |
|---|---|---|
| AI Platform / LLMOps | observability, evals, pipelines, monitoring, reliability | evals/observability, data-quality, reliability work |
| Agentic / Automation | agent, HITL, orchestration, workflow, multi-agent | multi-agent / human-in-the-loop / orchestration experience |
| AI Forward-Deployed (FDE) | client-facing, deploy, prototype, fast delivery | shipping speed + full-stack breadth |
| AI Solutions Architect | architecture, enterprise, integration, systems | system design + integration experience |
| Technical AI PM | PRD, roadmap, discovery, stakeholder | product discovery + metrics |
| Full-stack + AI (generalist) | React, Node, TypeScript, + LLM | core full-stack shipping + a real LLM-integration project |

---

## Part 3 — Posting Legitimacy / Ghost-Job tier (SEPARATE from the 1–5 score)

A standalone judgment of whether the posting is a real, active opening — so effort goes to
genuine opportunities. It does **not** change the fit score.

**Three tiers:** `High Confidence` (real/active) · `Proceed with Caution` (mixed signals) ·
`Suspicious` (multiple ghost indicators — investigate before investing time).

| Signal | Reliability | Read |
|---|---|---|
| Posting age / freshness | HIGH | <30d good · 30–60d mixed · 60d+ concerning (adjust per role type) |
| Apply button active | HIGH | Active = good; closed / redirects to a generic careers page = concerning |
| Tech specificity in JD | MEDIUM | Names specific tech/tools = good; generic boilerplate correlates with ghosts |
| Requirements realism | MEDIUM | Internal contradictions (mid title + Staff reqs, YOE > the tech's age) = strong negative |
| Recent layoff / freeze news | MEDIUM | Search `"{company}" layoffs` / `hiring freeze`; weigh more if the *same* department |
| Reposting pattern | MEDIUM | Same role reposted 2+ times in 90d = concerning |
| Salary transparency | LOW | Jurisdiction-dependent; many legit reasons to omit |
| Role–company fit | LOW | Does the role make sense for the business? Subjective, supporting signal only |

### Edge cases — don't over-flag
- **Gov / academic:** 60–90 days is normal.
- **"Evergreen" / "rolling" postings:** NOT a ghost — it's a pipeline role; note as context.
- **Niche / Staff+ roles:** legitimately stay open for months — relax age thresholds.
- **Startup / pre-revenue:** a vague JD may mean the role is genuinely still being defined.
- **No date available + no other concerns:** default to **Proceed with Caution**, never "Suspicious".
- **Recruiter-sourced (no public posting):** an active recruiter is itself a *positive* signal.

**Ethical framing (mandatory):** present *signals*, never accusations. Every concerning signal
has innocent explanations — note them. You decide how to weigh.

---

## Part 4 — Wiring scores into the dashboard (zero code change)

`tracker/dashboard.py` already renders a **Score** column and a "scored 4.0+" quick-view — it
just needs data. It reads a score from a `score` CSV column **or** from a `score: 4.5` token in
the **notes** field. Since `leads.csv` rows end in a notes cell, the no-code path is:

```
# in tracker/leads.csv, write the score into the trailing notes cell:
...,lead,,greenhouse,score: 4.2
# combine with a referral note — both markers light up in one write:
...,lead,,ashby,score: 4.6 | referral: ask Dana
# flag a ghost for the eye (only the number is parsed; the rest is for you):
...,lead,,greenhouse,score: 3.1 | ghost? reposted 3x
```

Color buckets render automatically (≥4.0 green, ≥3.5 amber, <3.5 grey), and the referral
marker (`referr/referral/intro/warm` in notes) lights up too. Then: **sort by score desc, work
the ≥4.5 / High-Confidence rows first.**
