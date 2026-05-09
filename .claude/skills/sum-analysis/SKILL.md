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
| `completion=0` AND any of `ease`, `satisfaction`, or `perception` ≥ 4 | "Did not complete but rated [dimension] [score] — possible data entry error. Rewatch the video to confirm the completion coding." |
| Two of the three Likert scores ≥ 4 but the third ≤ 2 | "Score inconsistency — [high_col]=[X] and [high_col2]=[Y] but [low_col]=[Z]. Possible typo — rewatch the video to verify the score." |
| `ease` and `satisfaction` differ by ≥ 3 | "Large gap between ease ([X]) and satisfaction ([Y]) — rewatch the video to confirm both scores are correct." |
| `completion=1` AND all three Likert scores ≤ 2 | "Completed but rated everything ≤ 2 — could be a genuine negative experience or a completion coding error. Rewatch the video to confirm." |
| `completion=1` AND `time_s` < 30% of the median time for that version/task | "Unusually fast ([X]s vs. median [Y]s) — rewatch the video to verify the participant actually completed the task." |
| `completion=1` AND `time_s` > 3× the median time for that version/task | "Unusually long ([X]s vs. median [Y]s) — rewatch the video to check for distraction, abandonment, or a restart." |
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

| Participant | Timestamp | Path Taken | Outcome | Quote | Quote Explanation |
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

> Please fill in a row for every participant. A few rules for the Quote column:
>
> - **Write the quote verbatim** — copy the participant's exact words from the video. Do not paraphrase, summarize, or clean up their language.
> - **Start where the thought begins** and continue until it's fully expressed — include the reasoning, not just the conclusion ("I wasn't sure where to look because..." not just "I wasn't sure").
> - **Keep hedges and qualifiers** — "I think maybe..." signals uncertainty and matters for analysis.
> - **Include emotional language** when present ("this is so frustrating" is data).
> - **Do not combine statements** from different moments in the session into a single quote.
> - **If a quote is longer than 3 sentences**, split it into two separate rows.
> - **Timestamp** — record the approximate video timestamp where the quote occurs (e.g. ~14:30).
>
> For **Quote Explanation**: note which screen or feature the quote refers to and any design implication.
>
> Return the completed notes document when you're done and we'll proceed to analysis.

Wait for the researcher to return the completed notes before proceeding to Phase 4. If they want to skip notes, proceed without them — the Phase 6 qualitative sections will be omitted.

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
> A **time spec** is the maximum time a user should reasonably take to complete this task satisfactorily — it's the benchmark the Time score is measured against. Normally it's derived automatically from participants who both finished the task and rated the experience positively, but none of your participants for this task did both.
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
