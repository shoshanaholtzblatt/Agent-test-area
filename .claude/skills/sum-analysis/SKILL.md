# /sum-analysis — Single Usability Metric Analysis

Compute SUM scores from raw usability test data using the Jeff Sauro / MeasuringUsability.com methodology. Produces per-task SUM scores with 90% confidence intervals across three dimensions (Completion, Satisfaction, Time) and synthesizes UX recommendations.

---

## What this skill does

1. Guides the researcher through providing data in a standard CSV format
2. Validates the data (column names, value ranges, minimum sample size)
3. Runs `sum_calculator.py` to compute all statistics
4. Returns a formatted results table and prioritized UX recommendations

---

## Requirements before starting

- **Minimum 15 participants per version per task** (the skill will reject smaller samples)
- **3 separate Likert ratings** per participant per task (ease, satisfaction, perception) on a **1–5 scale**
- **Task completion** recorded as `1` (completed) or `0` (did not complete)
- **Time in seconds** for every participant, including those who did not complete the task
- **Version label** for every row — use the same label if only one version; use distinct labels (e.g. V1, V2) to compare versions side-by-side
- Errors/mistakes are **not** part of the SUM calculation in this version

---

## Phase 1 — Announce

When the user invokes `/sum-analysis`, say:

> I'll help you analyze your usability test data using the Single Usability Metric (SUM) methodology.
>
> I need one row per participant per task with these eight columns:
> - **version** — version label (e.g. "V1", "V2") — use the same label for all rows if comparing only one version
> - **task** — task name (e.g. "Search", "Checkout")
> - **participant** — participant ID (e.g. P01)
> - **completion** — `1` if they completed the task, `0` if not
> - **ease** — "How difficult or easy was this task?" (1–5)
> - **satisfaction** — "How dissatisfied or satisfied are you with this task?" (1–5)
> - **perception** — "Did it take more or less time than you were expecting?" (1–5)
> - **time_s** — time in seconds (record for ALL participants, even non-completers)
>
> **Minimum 15 participants per version per task.** Time benchmarks are derived automatically from your data — no spec needed. Multiple versions in the same CSV are compared side-by-side.
>
> You can paste CSV rows directly, share a file path, or use the template at `data/sum_template.csv`.

---

<!-- ## Phase 2 — Session config (commented out — always uses 90% CI)

Ask the researcher:

> What confidence level would you like for the intervals?
> - **90% CI** (alpha = 0.10, recommended — matches the original SUM methodology)
> - **95% CI** (alpha = 0.05)
> - **99% CI** (alpha = 0.01)

Default to 90% CI (alpha = 0.10) if they do not specify. Note that the satisfaction threshold is fixed at **4.0** (mid-point of "good" on the 1–5 scale).

-->

---

## Phase 3 — Data collection

Ask the researcher to provide their data. Accept any of:
- Pasted CSV text (with or without header row)
- A file path to a `.csv` file

If they paste CSV text without a header, prepend:
```
version,task,participant,completion,ease,satisfaction,perception,time_s
```

All tasks and versions can be in a single CSV — each row is identified by its `version` and `task` values. Multiple versions will be shown side-by-side in the results table.

After receiving data, confirm how many versions, tasks, and participants were provided before proceeding.

---

## Phase 3b — Accuracy checks

Before writing the CSV or running the calculator, review the raw data and flag every suspicious row. Present flags grouped by participant ID and version/task. If no flags are found, say so briefly and continue.

Apply these checks (compute per-task medians from the submitted data for the time-based checks):

| Check | Flag message |
|---|---|
| `completion=0` AND any of `ease`, `satisfaction`, or `perception` ≥ 4 | "Did not complete but rated [dimension] [score] — possible data entry error. Rewatch the video to confirm the completion coding and scores." |
| Two of the three Likert scores ≥ 4 but the third ≤ 2 | "Score inconsistency — [high_col]=[X] and [high_col2]=[Y] but [low_col]=[Z]. Possible typo — rewatch the video to verify the score." |
| `ease` and `satisfaction` differ by ≥ 3 | "Large gap between ease ([X]) and satisfaction ([Y]) — rewatch the video to confirm both scores are correct." |
| `completion=1` AND all three Likert scores ≤ 2 | "Completed but rated everything ≤ 2 — could be a genuine negative experience or a completion coding error. Rewatch the video to confirm." |
| `completion=1` AND `time_s` < 30% of the median time for that version/task | "Unusually fast ([X]s vs. median [Y]s) — rewatch the video to verify the participant actually completed the task." |
| `completion=1` AND `time_s` > 3× the median time for that version/task | "Unusually long ([X]s vs. median [Y]s) — rewatch the video to check for distraction or genuine usability issues. Adjust task time, if needed." |
| `satisfaction=5` AND `ease=1` (or `ease=5` AND `satisfaction=1`) | "Extreme opposite scores on satisfaction and ease — likely a scale confusion or typo. Rewatch the video to verify both scores." |

Flags are informational — do not block progress. Ask the researcher to rewatch the flagged participant's video to verify before returning the notes.

---

## Phase 3c — Correct paths, watch list, and notes setup

### Step 1 — Collect correct path(s) per task

**Check for a saved research plan first.** Before asking the researcher for correct paths, look for any file matching `reports/research_plan_*.md` in the project directory.

If a plan file is found:
1. Read the section between `<!-- sum-analysis: task-context-start -->` and `<!-- sum-analysis: task-context-end -->`.
2. Extract the task names and correct paths.
3. Present them to the researcher for confirmation:

> I found a research plan from [date] (`reports/research_plan_YYYY-MM-DD.md`). Here are the tasks and correct paths it defined:
>
> **Task: [Task Name]**
> 1. [Path from plan]
> 2. [Alternate path, if present]
>
> [Repeat for each task]
>
> Are these still accurate, or would you like to make any changes before I create the notes document?

If the researcher confirms, use the paths as-is and skip the manual path-entry prompt below. If they want to edit, accept their changes before proceeding. If no plan file is found, proceed with the manual prompt.

**Manual path entry (only if no plan file found):**

Ask the researcher:

> For each task, what is the correct path (or paths) a participant should take?
>
> Use a step-by-step navigation format. Example:
> `Scroll home → Quick actions → Checking account → View transactions → Transaction detail`
>
> List alternate correct paths on separate lines if more than one exists.

### Step 2 — Generate the watch list

Present all participants sorted into three priority tiers. All participants should be watched; tiers indicate where to pay closest attention.

**Priority 1 — Watch carefully:**
Every participant who triggered at least one Phase 3b accuracy flag, plus all non-completers (completion=0).

**Priority 2 — Watch for path deviations:**
Completers where any two of `ease`, `satisfaction`, `perception` differ by ≥ 2, or whose `time_s` exceeds 1.5× the per-task median.

**Priority 3 — Standard watch:**
All remaining participants.

### Step 3 — Create the notes document

Write `reports/sum_notes_YYYY-MM-DD.md` (use today's date) with this structure, repeated for each task:

```markdown
# Usability Test Notes — [date]

## Task: [Task Name]

### Correct Path(s)
1. [Primary path — e.g. Scroll home → Quick actions → Checking account → View transactions → Transaction detail]
2. [Alternate path, if applicable]

### Participant Notes

| Participant | Path Taken | Outcome | Quote | Quote Timestamp | Quote Explanation |
|-------------|-----------|------------|---------|-------|-------------------|
| P01 | | | | | |
| P02 | | | | | |
...

**Outcome key:** DS = Direct Success · IS = Indirect Success · DF = Direct Failure · IF = Indirect Failure
```

**Outcome definitions:**
- **DS — Direct Success:** First click on the correct path element AND task completed without backtracking
- **IS — Indirect Success:** Task completed, but participant deviated from the correct path before finishing
- **DF — Direct Failure:** First click on the wrong element AND task not completed
- **IF — Indirect Failure:** Participant tried multiple paths but ultimately did not complete the task

Tell the researcher:

> Please fill in a row for every participant:
> - **Path Taken** — same step-by-step format as the correct path above
> - **Outcome** — code each participant's task performance: DS/IS/DF/IF (see key below)
> - **Quote** — the single best quote capturing confusion, delight, or an unexpected moment
> - **Quote Timestamp** — record the approximate video timestamp where the quote occurs (e.g. ~14:30)
> - **Quote Explanation** — which screen or feature the quote refers to, and any design implications
>
> Return the completed notes document when you're done, and we'll proceed to analysis.

Wait for the researcher to return the completed notes before proceeding to Phase 4. If they don't have video access or want to skip notes, proceed without them — the Phase 6 qualitative sections will be omitted.

---

## Phase 4 — Validation

Write the data to `/tmp/sum_analysis_data.csv`, then run:

```bash
python3 /path/to/sum_calculator.py --csv /tmp/sum_analysis_data.csv --alpha 0.10
```

Use the **absolute path** to `sum_calculator.py` in the project (resolve it with `find` if needed).

If the script exits with an error (non-zero exit code or JSON with `"error"` key), show the researcher the error message and ask them to fix it. Common issues:
- Fewer than 15 participants for a task → ask for more data or to proceed with a note about limited statistical power
- Missing columns → show which columns are absent
- Values out of range → show which rows have invalid data

Do not proceed past validation until the data is clean.

---

## Phase 4b — Time spec fallback (only if needed)

**Trigger:** the calculator exits with code `2`, or the JSON contains `"error": "time_spec_required"`.

This means one or more (version, task) pairs had fewer than 2 participants who both completed the task and rated composite satisfaction ≥ 4.0, so no time benchmark could be derived automatically.

For **each task key** listed in `tasks`, say to the researcher (substituting the actual version and task name):

> **[Version] / [Task]** needs a time specification.
>
> A **time spec** is the maximum time a user should reasonably take to complete this task satisfactorily — it's the benchmark the Time score is measured against. Normally, it's derived automatically from participants who both finished the task and rated the experience positively, but none of your participants for this task did both.
>
> **How to find one:** Ask someone who is not on your team and is not familiar with this feature to complete the task while you time them. That time is a practical gauge for what a reasonable completion looks like. Aim for someone who represents your target user — they should be able to complete the task, just without inside knowledge of the design.
>
> What time (in seconds) would you like to use as the spec for **[Task]** ([Version])?

Once you have a value for every affected task, re-run with `--time-spec` flags (one per task):

```bash
python3 /path/to/sum_calculator.py \
  --csv /tmp/sum_analysis_data.csv \
  --alpha 0.10 \
  --time-spec "V1/Task 1=90"
```

In the Phase 6 report, note any tasks that used a manual time spec — visible as `"time_spec_source": "manual"` in the JSON output.

---

## Phase 5 — Compute

Run the calculator (as above). Parse the output: everything before `---JSON-END---` is JSON; everything after is the markdown table.

The JSON structure is:
```json
{
  "alpha": 0.10,
  "z_crit": 1.645,
  "versions": {
    "V1": {
      "tasks": {
        "Task Name": {
          "n": 15,
          "completion": {"observed": 0.93, "pct": 0.88, "ci_low": 0.71, "ci_high": 0.96},
          "satisfaction": {"displayed_pct": 0.64, "pct": 0.65, "ci_low": 0.53, "ci_high": 0.77, "mean": 4.3, "spec": 4.0},
          "time": {"displayed_pct": 0.86, "pct": 0.89, "ci_low": 0.83, "ci_high": 0.93, "time_spec": 143.5},
          "sum": 0.85,
          "ci_low": 0.70,
          "ci_high": 0.92
        }
      },
      "overall": {"sum": 0.85, "ci_low": 0.70, "ci_high": 0.92}
    }
  }
}
```

Use `displayed_pct` (not `pct`) for the satisfaction and time dimension scores shown in the table and narrative. `pct` is used internally to compute the SUM score.

---

## Phase 6 — Report

Present the markdown table produced by the script, then provide:

### Narrative summary

Write 2–4 sentences interpreting the overall SUM score(s):
- SUM ≥ 80%: generally good usability, minor improvements needed
- SUM 60–79%: moderate usability, significant improvements warranted
- SUM 40–59%: poor usability, redesign recommended for weak areas
- SUM < 40%: critical usability failures

If multiple versions are present, highlight the direction and magnitude of change between versions (e.g. "V2 improved overall SUM by X points"). Highlight which task(s) scored lowest and which dimension(s) drove the low score.

### Prioritized UX recommendations

Provide **3–5 specific, actionable recommendations** ranked by impact, based on the dimension scores:

- **Low Completion** (< 70%): Users are failing the task — investigate where they get stuck. Recommend task flow analysis, error recovery improvements, or clearer affordances.
- **Low Satisfaction** (< 60%): Users find the experience frustrating or confusing. Recommend UI clarity improvements, reduced cognitive load, or onboarding changes.
- **Low Time score** (< 60%): Users are taking much longer than efficient users. Recommend streamlining steps, improving discoverability, or reducing navigation depth.

Frame each recommendation around the specific task(s) and dimension(s) affected.

### Path and first-click analysis *(include only if notes were collected in Phase 3c)*

For each task, analyze the Path Taken and Outcome columns from the notes document.

**First-click accuracy:** Count how many participants' first path step matches the first step of any correct path. Report as a percentage.

**Outcome breakdown:**

| Outcome | Count | % of participants |
|---------|-------|-------------------|
| Direct Success (DS) | | |
| Indirect Success (IS) | | |
| Direct Failure (DF) | | |
| Indirect Failure (IF) | | |

**Path distribution (completers only):** If multiple correct paths exist, show what % of completers used each path.

**Narrative (1–2 sentences):** Interpret the pattern. Examples: "All failures were direct — participants never found the entry point — suggesting a discoverability problem rather than a flow problem." Or: "High indirect success rate means participants recovered from wrong turns, so the error recovery is working but the initial affordance needs improvement."

---

### Quote presentation and data accuracy check *(include only if notes were collected)*

Present each quote exactly as it appears in the notes — never paraphrase, condense, or rephrase. Format each as:

> "[verbatim quote]" — [P-ID, ~timestamp]

For every quote, cross-check its sentiment against that participant's actual Likert scores and path outcome. Flag any mismatch:

- **Sentiment vs. scores:** Positive quote (e.g., "That was really easy to find!") paired with `ease ≤ 2`, or negative quote paired with `ease ≥ 4` → "Quote sentiment conflicts with [dimension] score of [X] — rewatch the video to verify the score before including this in the report."
- **Quote vs. path:** Quote describes confusion or searching but outcome is DS (Direct Success) → "Quote suggests struggle but outcome is Direct Success — rewatch the video to confirm the outcome coding."

Researchers should go back to the **video** (not their notes) to resolve any flag. Do not remove flagged quotes from the report — present them with the flag attached so the researcher can decide.

Group quotes by theme where 2+ participants reference the same screen or moment — these are the strongest signals in the data.

---

### Insight contradiction checks *(include only if notes were collected)*

Cross-reference the path and quote findings against the SUM dimension scores and flag any of the following:

- **High Time score + many Indirect Successes (IS):** Participants were fast but got lost along the way. The Time score flatters the experience — efficiency is masking navigational confusion.
- **High Completion + many IS:** People finished, but not cleanly. The completion rate overstates how intuitive the path is.
- **Low Satisfaction + predominantly positive quotes:** Possible Likert scale confusion — participants may have inverted the scale. Recommend a follow-up probe.
- **Direct Failures (DF) clustered at the same path step:** The failure is localized. Name the specific step (e.g., "all DF participants stopped at 'Quick actions' — the entry point is the problem, not the downstream flow").
- **Accuracy flags confirmed by notes:** If a flagged participant's quote or path explains the anomaly (e.g., P07's quote mentions a phone call mid-task), resolve the flag and note it.

---

### Finding confidence levels *(apply to all qualitative findings — themes, insight contradictions, and path patterns)*

For every finding that uses qualitative evidence, assign a confidence level:

| Level | Criteria |
|-------|----------|
| **High** | 3+ participants with consistent evidence (quotes and data point the same direction) |
| **Medium** | 2 participants, or 3+ with mixed or partial signals |
| **Low** | 1 participant, or quotes and data conflict; present as directional only — do not recommend action on Low confidence alone |

Display confidence inline with each finding, e.g.:
> "Participants struggled to locate the entry point for Task 1." *(Confidence: High — 4 of 5 DF participants stopped at the home screen)*

---

### Save option

Ask:
> Would you like me to save this report to `reports/sum_report_YYYY-MM-DD.md`?

If yes, write the full report (table + narrative + recommendations + all qualitative sections if present) to that path with today's date.

---

## Phase 6a — Approval gate

After presenting the full Phase 6 report, ask the researcher:

> Please review the results and findings above. Flag any cells where you'd like me to adjust a score interpretation, swap a quote, correct a path outcome, or revise a recommendation. Once you approve, I'll generate the HTML report.

**Wait for explicit approval.** Make any requested corrections and re-present the affected sections before proceeding. Do not generate HTML before approval.

If the researcher declines the HTML or wants to stop here, end the session after the markdown save.

---

## Phase 6b — Generate HTML report

Build a spec JSON from the approved report content and the Phase 5 JSON output. Write it to `/tmp/sum_html_spec.json`, then write the HTML file directly to `reports/sum_report_YYYY-MM-DD.html`.

### Spec JSON structure

```json
{
  "study_name": "...",
  "date": "YYYY-MM-DD",
  "alpha": 0.10,
  "versions": ["V1"],
  "participants_per_task": 15,
  "has_notes": true,
  "tasks": [
    {
      "id": "find-balance",
      "name": "Find Balance",
      "sum_by_version": {
        "V1": {
          "sum": 0.595, "ci_low": 0.423, "ci_high": 0.717,
          "completion": {"pct": 0.789, "ci_low": 0.579, "ci_high": 1.0},
          "satisfaction": {"displayed_pct": 0.48, "ci_low": 0.348, "ci_high": 0.609},
          "time": {"displayed_pct": 0.446, "ci_low": 0.341, "ci_high": 0.543,
                   "time_spec": 90.0, "time_spec_source": "derived"}
        }
      },
      "path_analysis": {
        "first_click_accuracy_n": 10, "first_click_accuracy_total": 15,
        "outcomes": {"DS": 10, "IS": 3, "DF": 2, "IF": 0},
        "correct_paths": ["Home → Accounts tab → Checking account → Balance overview"],
        "path_distribution": [{"label": "Path A (Accounts tab)", "pct": 0.85}],
        "narrative": "All failures were direct — participants never found the entry point..."
      },
      "quotes": [
        {"text": "I kept looking for some kind of overview page...", "participant_id": "P07",
         "timestamp": "~8:40", "polarity": "negative", "flag": null},
        {"text": "I found it but it's pretty buried.", "participant_id": "P12",
         "timestamp": "~4:55", "polarity": "negative",
         "flag": "Quote sentiment conflicts with satisfaction=5 — rewatch the video to verify."}
      ],
      "themes": [
        {"label": "Accounts tab discoverability", "participants": ["P07","P09","P14","P15"],
         "confidence": "high", "representative_quote_idx": 0}
      ],
      "accuracy_flags": [
        {"participant_id": "P09", "flag": "Score inconsistency (ease=2, satisfaction=5, perception=4)"}
      ]
    }
  ],
  "overall_by_version": {
    "V1": {"sum": 0.532, "ci_low": 0.383, "ci_high": 0.643}
  },
  "recommendations": [
    {
      "rank": 1,
      "headline": "Resolve the Quick Actions / Transfer inconsistency",
      "body": "The Quick Actions transfer shortcut sends users to a different screen than the Accounts flow...",
      "tasks": ["Transfer Funds"],
      "dimensions": ["satisfaction", "completion"]
    }
  ],
  "contradiction_checks": [
    {"label": "Find Balance — High Completion + 3 Indirect Successes",
     "explanation": "The completion rate overstates how intuitive the path is..."}
  ],
  "methodology": {
    "format": "Moderated 1:1 usability sessions",
    "participants": "15 per task",
    "tasks_tested": "Find Balance, Transfer Funds",
    "sum_method": "Completion (Wilson CI), Satisfaction (log-normal Z-score vs 4.0/5.0 spec), Time (log-normal Z-score vs data-derived benchmark). 90% CI (alpha = 0.10).",
    "manual_time_specs": ["V1 / Transfer Funds — 120s (no participant met the automatic derivation threshold)"]
  }
}
```

---

### HTML structure

The report is a self-contained single HTML file. Reuse the concept-testing CSS verbatim (same design tokens, fonts, tab system, card patterns, blockquote styles) from `data/examples/personal_finance_study/example_report.html`. Add the following usability-specific CSS after the shared styles:

```css
/* Dimension score display */
.dim-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 16px; }
.dim-block { background: var(--paper); border: 1px solid var(--rule); border-radius: 4px;
             padding: 16px 20px; }
.dim-label { font-family: var(--mono); font-size: 10px; text-transform: uppercase;
             letter-spacing: 0.12em; color: var(--ink-mute); margin-bottom: 6px; }
.dim-score { font-family: var(--serif); font-size: 32px; font-weight: 500;
             line-height: 1; letter-spacing: -0.02em; }
.dim-score.good { color: var(--pos); }
.dim-score.moderate { color: var(--mixed); }
.dim-score.poor { color: var(--neg); }
.dim-ci { font-family: var(--mono); font-size: 11px; color: var(--ink-mute); margin-top: 4px; }
.dim-note { font-size: 12px; color: var(--ink-mute); font-style: italic; margin-top: 6px; }

/* CI bar */
.ci-bar-wrap { position: relative; height: 4px; background: var(--rule-soft);
               border-radius: 2px; margin: 10px 0 4px; }
.ci-bar-fill { position: absolute; height: 100%; background: var(--ink-mute);
               border-radius: 2px; opacity: 0.4; }
.ci-bar-point { position: absolute; top: -4px; width: 2px; height: 12px;
                background: var(--ink); border-radius: 1px; transform: translateX(-50%); }

/* SUM score card */
.score-card { background: var(--paper); border: 1px solid var(--rule); border-radius: 4px;
              padding: 24px 28px; box-shadow: var(--shadow); }
.score-card-version { font-family: var(--mono); font-size: 10px; letter-spacing: 0.15em;
                      text-transform: uppercase; color: var(--accent); margin-bottom: 8px; }
.score-card-sum { font-family: var(--serif); font-size: 56px; font-weight: 500;
                  line-height: 1; letter-spacing: -0.03em; }
.score-card-ci { font-family: var(--mono); font-size: 12px; color: var(--ink-mute); margin-top: 4px; }
.interp-badge { display: inline-block; font-family: var(--mono); font-size: 10px;
                letter-spacing: 0.1em; text-transform: uppercase; padding: 4px 10px;
                border-radius: 2px; margin-top: 10px; }
.interp-badge.good { background: rgba(47,95,58,0.12); color: var(--pos); }
.interp-badge.moderate { background: rgba(138,110,26,0.12); color: var(--mixed); }
.interp-badge.poor { background: rgba(155,42,42,0.12); color: var(--neg); }
.interp-badge.critical { background: var(--neg); color: white; }
.delta-badge { font-family: var(--mono); font-size: 13px; font-weight: 600; margin-left: 12px; }
.delta-badge.up { color: var(--pos); }
.delta-badge.down { color: var(--neg); }

/* Outcome bar */
.outcome-bar { display: flex; height: 20px; border-radius: 2px; overflow: hidden;
               background: var(--rule-soft); margin: 12px 0 8px; }
.outcome-bar .seg { height: 100%; display: flex; align-items: center; justify-content: center;
                    font-size: 11px; color: white; font-weight: 600; }
.outcome-bar .seg.DS { background: var(--pos); }
.outcome-bar .seg.IS { background: var(--mixed); }
.outcome-bar .seg.DF { background: var(--neg); }
.outcome-bar .seg.IF { background: #6b1c1c; }

/* Recommendation item */
.rec-item { display: flex; gap: 18px; padding: 18px 0;
            border-bottom: 1px solid var(--rule-soft); }
.rec-item:last-child { border-bottom: none; }
.rec-rank { font-family: var(--mono); font-size: 22px; font-weight: 500;
            color: var(--accent); min-width: 32px; line-height: 1; }
.rec-body { flex: 1; }
.rec-headline { font-family: var(--serif); font-size: 18px; font-weight: 500;
                margin: 0 0 6px; line-height: 1.2; }
.rec-text { font-size: 14px; color: var(--ink-soft); margin: 0 0 10px; }
.tag-row { display: flex; flex-wrap: wrap; gap: 6px; }
.tag { font-family: var(--mono); font-size: 10px; letter-spacing: 0.08em;
       text-transform: uppercase; padding: 3px 8px; border-radius: 2px; }
.tag.task { background: var(--bg); border: 1px solid var(--rule); color: var(--ink-soft); }
.tag.completion { background: rgba(155,42,42,0.10); color: var(--neg); }
.tag.satisfaction { background: rgba(138,110,26,0.10); color: var(--mixed); }
.tag.time { background: rgba(28,26,23,0.06); color: var(--ink-mute); }

/* Results table */
.results-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.results-table th { font-family: var(--mono); font-size: 10px; text-transform: uppercase;
                    letter-spacing: 0.1em; color: var(--ink-mute); padding: 8px 10px;
                    border-bottom: 1px solid var(--ink-soft); text-align: right; }
.results-table th:first-child, .results-table th:nth-child(2) { text-align: left; }
.results-table td { padding: 10px 10px; border-bottom: 1px solid var(--rule-soft);
                    text-align: right; color: var(--ink-soft); }
.results-table td:first-child, .results-table td:nth-child(2) { text-align: left; font-weight: 500; color: var(--ink); }
.results-table .score-cell { font-family: var(--mono); font-weight: 600; }
.score-cell.good { color: var(--pos); }
.score-cell.moderate { color: var(--mixed); }
.score-cell.poor { color: var(--neg); }
.score-cell.ci { color: var(--ink-mute); font-weight: 400; }
.results-table tr.overall-row td { border-top: 1px solid var(--ink-soft);
                                    font-weight: 600; color: var(--ink); }
```

---

### Tab and content structure

**Masthead:**
```html
<p class="eyebrow">Usability Testing Report · [study_name]</p>
<h1>[N] tasks tested. Overall SUM: <em>[X%]</em>.</h1>
<!-- If two versions: <h1>V2 improved overall SUM by <em>+Xpp</em> across [N] tasks.</h1> -->
<div class="meta">
  <span>Date <strong>[date]</strong></span>
  <span>Participants <strong>[N] per task</strong></span>
  <span>Tasks <strong>[N]</strong></span>
  <span>Version(s) <strong>[V1 / V2]</strong></span>
  <span>Method <strong>SUM · 90% CI</strong></span>
</div>
```

**Tabs:** `01 Overview` · `02 Key Insights` · `03 [Task Name]` (one per task) · `N Methodology`

---

**Overview tab (§01–§03):**

*§01 — Score cards:* `.card-grid-2` (or single card if one version). Each `.score-card`:
- Version label (`.score-card-version`, mono, accent)
- Overall SUM % (`.score-card-sum`, colored: `--pos` ≥ 80%, `--mixed` 60–79%, `--neg` < 60%)
- CI range (`.score-card-ci`)
- Interpretation badge (`.interp-badge.good/moderate/poor/critical`)
- If two versions: delta badge (`.delta-badge.up/down`) on the V2 card

*§02 — Results table:* `<table class="results-table">`. Score cells use `.score-cell.good/moderate/poor/ci`. Overall rows use `.overall-row`. CI columns use `.score-cell.ci` (muted).

*§03 — Score interpretation:* `.def-list` with four entries (Good / Moderate / Poor / Critical) and three dimension rows (Completion / Satisfaction / Time).

---

**Key Insights tab (§01–§04):**

*§01 — UX recommendations:* `.card` containing `.rec-item` list. Each item: rank (`.rec-rank`), headline (`.rec-headline`), body (`.rec-text`), tag row (`.tag-row`) with task tags (`.tag.task`) and dimension tags (`.tag.completion/satisfaction/time`).

*§02 — Qualitative themes* *(omit if `has_notes: false`):* One `.insight-card` per theme. Include:
- Theme label (h3, serif)
- Confidence pips (same `.conf-pips` pattern from concept-testing) + level text
- Participant list (mono, small, muted)
- Representative quote from `quotes[representative_quote_idx]` as a blockquote

*§03 — Insight contradiction checks* *(omit if `has_notes: false`):* `.card` with bulleted list. Each: `<strong>` label + sentence explanation.

*§04 — Accuracy flags* *(omit if no flags across any task):* Table inside `.card`: Participant | Task | Flag | Status.

---

**Per-task tab (`task-[id]`, one per task):**

*Task hero:* Two-column grid (`grid-template-columns: 1fr 2fr`):
- Left: Task name (h2, serif), SUM score (`.score-card-sum`, colored), CI range (`.score-card-ci`), interpretation badge
- Right: `.dim-grid` with three `.dim-block` entries (Completion / Satisfaction / Time). Each block:
  - Label (`.dim-label`, mono uppercase)
  - Score (`.dim-score.good/moderate/poor`, serif large)
  - CI bar (`.ci-bar-wrap` → `.ci-bar-fill` + `.ci-bar-point` positioned at `pct * 100%`)
  - CI range text (`.dim-ci`)
  - For Time only: `.dim-note` showing "time spec: Xs (derived)" or "(manual)"

*§01 — Path and first-click analysis* *(omit if `has_notes: false` or `path_analysis: null`):*
- First-click accuracy: large mono readout + label ("X of N participants started on a correct path element")
- Outcome bar (`.outcome-bar`): segments sized by count (DS=`--pos`, IS=`--mixed`, DF=`--neg`, IF=`#6b1c1c`), each labeled with count if segment is wide enough
- Outcome table: DS / IS / DF / IF with count and %
- Path distribution table (omit if single path)
- Narrative: `<p class="lead" style="font-style:italic">` (serif, 1–2 sentences)

*§02 — Participant quotes* *(omit if `has_notes: false`):*
Grouped under `<h4>` theme headings where `themes` exist; ungrouped otherwise.
Each quote:
```html
<blockquote class="pos|neg|[none]">
  "[verbatim text]"
  <span class="attr">— P07, ~8:40</span>
</blockquote>
<!-- If quote.flag is non-null: -->
<div class="reconciliation">
  <strong>Flag</strong>[flag text]
</div>
```

*§03 — Accuracy flags for this task* *(omit if `accuracy_flags` is empty):*
`.card` with compact list: each entry as `<span class="concept-meta-id">[P-ID]</span> [flag message]`.

---

**Methodology tab (§01–§03):**

*§01 Study setup:* `.insight-card` with `<p>` blocks for format, participants, tasks, CI level, satisfaction spec.

*§02 SUM dimension definitions:* `.insight-card` with `.def-list`:
- Completion — Wilson score interval; reflects task success rate
- Satisfaction — log-normal Z-score vs 4.0/5.0 fixed spec; reflects perceived ease and satisfaction
- Time — log-normal Z-score vs data-derived benchmark (85th-percentile time of satisfied completers); reflects efficiency. If `manual_time_specs` is non-empty, list affected tasks.

*§03 Confidence definitions:* `.insight-card` with `.def-list`, same 3-pip icons as concept-testing (High / Medium / Low with criteria text).

---

**Footer:**
```html
<footer>
  <span>Generated [date] · /sum-analysis</span>
  <span>Usability Testing Report · [study_name]</span>
</footer>
```

---

**JavaScript:** Copy the tab-switching script from `data/examples/personal_finance_study/example_report.html` verbatim (14 lines).

---

### After writing the file

Tell the researcher:

> HTML report saved to `reports/sum_report_YYYY-MM-DD.html`. Open in any browser. Tabs: Overview, Key Insights, one tab per task, Methodology.

---

## Score interpretation quick reference

| SUM Score | Interpretation |
|-----------|---------------|
| ≥ 80% | Good usability |
| 60–79% | Moderate — improvements warranted |
| 40–59% | Poor — redesign recommended |
| < 40% | Critical failures |

| Dimension | Score | Meaning |
|-----------|-------|---------|
| Completion | Wilson-adjusted % who completed | Reflects task success rate |
| Satisfaction | % below spec (4.0/5.0) threshold | Reflects perceived ease + satisfaction |
| Time | % within data-derived benchmark | Reflects efficiency vs. efficient happy-path users |
