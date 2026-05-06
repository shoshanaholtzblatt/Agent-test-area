# SUM Analysis Skill

A Claude Code skill for analyzing usability test data using the **Single Usability Metric (SUM)** methodology developed by Jeff Sauro / MeasuringUsability.com.

---

## What it does

Run `/sum-analysis` in a Claude Code session to:

1. **Check your data for accuracy issues** — flags suspicious entries (inconsistent Likert scores, non-completers with high ratings, outlier times) before any calculation runs
2. **Generate a prioritized video watch list** — tells you which participant recordings to review most closely and creates a structured notes document
3. **Compute SUM scores** — per-task scores with 90% confidence intervals across three dimensions: Completion, Satisfaction, and Time
4. **Produce a full report** — results table, narrative summary, UX recommendations, and (if notes are provided) path analysis, quote verification, and finding confidence levels

---

## Requirements

| Requirement | Detail |
|---|---|
| Minimum participants | 15 per version per task |
| Likert ratings | 3 per participant: ease, satisfaction, perception (1–5 scale) |
| Completion | `1` = completed, `0` = did not complete |
| Time | Seconds — record for ALL participants, including non-completers |
| Version label | Use one label if single version; distinct labels (V1, V2) to compare versions side-by-side |

---

## How to invoke

```
/sum-analysis
```

Claude will walk you through each phase. You can provide data by pasting CSV text directly or sharing a file path.

---

## Input format

One row per participant per task:

```csv
version,task,participant,completion,ease,satisfaction,perception,time_s
V1,Task 1,P01,1,5,4,4,62
V1,Task 1,P02,0,2,2,3,145
...
```

A blank template is available at `data/sum_template.csv`.

---

## Skill workflow

### Phase 1 — Announce
Claude describes the data format and requirements.

### Phase 3 — Data collection
Paste or upload your CSV. Claude confirms the number of versions, tasks, and participants.

### Phase 3b — Accuracy checks
Claude scans every row for suspicious patterns before running any calculations:
- Non-completer with high Likert scores
- Inconsistent scores (e.g., ease=1 but satisfaction=5)
- Large gap between ease and satisfaction (≥ 3 points)
- Completed but all scores ≤ 2
- Unusually fast or slow times relative to the task median

Flagged rows are informational — you are asked to rewatch the relevant video to verify before returning notes.

### Phase 3c — Correct paths, watch list, and notes
1. You provide the correct navigation path(s) for each task
2. Claude generates a tiered watch list (Priority 1 / 2 / 3) for all participants
3. Claude creates `reports/sum_notes_YYYY-MM-DD.md` — a structured notes document for you to fill in while watching recordings

The notes document captures per participant:

| Column | What to enter |
|---|---|
| Path Taken | Step-by-step navigation the participant actually took |
| Outcome | DS / IS / DF / IF (see below) |
| Quote | Verbatim — exact words from the video; no paraphrasing |
| Quote Timestamp | Approximate timestamp, e.g. ~14:30 |
| Quote Explanation | Which screen or feature the quote refers to and the design implication |

**Outcome codes:**
- **DS** — Direct Success: first click correct, completed without backtracking
- **IS** — Indirect Success: completed, but deviated from the correct path first
- **DF** — Direct Failure: first click wrong, task not completed
- **IF** — Indirect Failure: tried multiple paths, ultimately did not complete

### Phase 4 — Validation
Claude runs the calculator and checks for structural errors (missing columns, out-of-range values, insufficient participants).

### Phase 4b — Time spec fallback *(if needed)*
If no participant both completed a task and rated composite satisfaction ≥ 4.0, the time benchmark cannot be derived automatically. Claude will explain the situation and ask you to provide a manually measured time in seconds. You can obtain this by timing an external person unfamiliar with the design completing the task.

### Phase 5 — Compute
Claude runs the full SUM calculation and parses the results.

### Phase 6 — Report
Claude presents:
- **Results table** — SUM scores and CI bounds per task and dimension
- **Narrative summary** — interpretation of overall scores
- **Prioritized UX recommendations** — 3–5 actionable items ranked by impact
- **Path and first-click analysis** *(if notes provided)* — DS/IS/DF/IF breakdown, first-click accuracy %, path distribution across correct alternates
- **Quote presentation and data accuracy check** *(if notes provided)* — verbatim quotes with timestamp citations; flags where quote sentiment conflicts with Likert scores; grouped themes
- **Insight contradiction checks** *(if notes provided)* — cross-references path patterns against SUM scores (e.g., high Time score masked by many indirect completions)
- **Finding confidence levels** *(if notes provided)* — High / Medium / Low based on how many participants support each qualitative finding

---

## Output files

| File | Description |
|---|---|
| `reports/sum_notes_YYYY-MM-DD.md` | Blank notes document created in Phase 3c for you to fill in |
| `reports/sum_report_YYYY-MM-DD.md` | Full report saved at the end of Phase 6 (optional) |

---

## Score interpretation

| SUM Score | Usability level |
|---|---|
| ≥ 80% | Good — minor improvements needed |
| 60–79% | Moderate — significant improvements warranted |
| 40–59% | Poor — redesign recommended for weak areas |
| < 40% | Critical failures |

| Dimension | What it measures |
|---|---|
| Completion | Wilson-adjusted rate of task success |
| Satisfaction | How responses compare to the 4.0/5.0 "good" threshold |
| Time | Efficiency relative to a benchmark derived from your best performers |

---

## Dependencies

- Python 3 (standard library only — no installs required)
- `sum_calculator.py` in the project root
- `data/sum_notes_template.md` — standalone reference copy of the notes format
