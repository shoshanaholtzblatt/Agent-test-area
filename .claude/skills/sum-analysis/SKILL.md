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

Then ask:

> Before we begin, I'd like some context so I can write sharper findings and recommendations.
>
> 1. **Project name** — a short label for this study (e.g. "Mobile Banking App — Checkout Redesign")
> 2. **Research question** — what the team most wanted to learn (e.g. "Can users complete transfers without calling support?")
> 3. **Background** — anything helpful: what product or feature was tested, what the team already knows or suspects, what design decisions are under evaluation, or concerns going in
>
> You can answer all three, just the ones you have, or skip this — the calculations run regardless. The more context you provide, the more specific the insights and recommendations in the final report will be.

Wait for a response (or explicit skip) before proceeding to Phase 3.

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

### Insights

Produce **3–5 prioritized insights** based on the SUM scores, path analysis, background context, and notes. Structure each insight as:

**Finding** — a clear statement of what was observed: what happened, who was affected, and how often.

**So what** — why this matters. Address two audiences:
- *For customers:* experience impact (frustration, failure, wasted time, confusion, eroded trust)
- *For the business:* outcome impact (support costs, abandonment, churn, missed transactions, competitive risk)

**Recommendation** — one specific, actionable directive. Name what to change, not just that something should improve.

Tag each insight: `Task: [task name]`. Assign a confidence level (High / Medium / Low):

| Level | Criteria |
|-------|----------|
| **High** | 3+ participants with consistent evidence pointing the same direction |
| **Medium** | 2 participants with consistent evidence, or 3+ with mixed signals |
| **Low** | 1 participant, or evidence conflicts; directional only — do not recommend action on Low alone |

Rank insights by business impact — lead with the finding most likely to cause failure, abandonment, or measurable cost.

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

### Task-level findings *(include only if notes were collected)*

For each task, write:
- **Headline finding** — one sentence capturing the most important thing about this task's usability
- **What's working well** — one or more findings with supporting evidence and confidence level
- **Issues** — one or more findings with supporting evidence and confidence level

**Accuracy flags** *(for researcher review only — do not include in HTML output):* List any data anomalies (non-completers with high scores, speed outliers, ease/satisfaction gaps) so the researcher can verify before approving the report.

---

### Save option

Ask:
> Would you like me to save this report to `reports/sum_report_YYYY-MM-DD.md`?

If yes, write the full report (table + narrative + insights + path analysis + task findings + accuracy flags) to that path with today's date. Accuracy flags are included in the saved markdown but will not appear in the HTML report.

---

## Phase 6a — Approval gate

After presenting the full Phase 6 report, ask the researcher:

> Please review the results and findings above. Flag anything you'd like me to adjust — score interpretations, insight wording, path outcomes, task findings, or recommendations. Once you approve, I'll generate the HTML report. (Note: accuracy flags are for your video review only and will not appear in the HTML.)

**Wait for explicit approval.** Make any requested corrections and re-present the affected sections before proceeding. Do not generate HTML before approval.

If the researcher declines the HTML or wants to stop here, end the session after the markdown save.

---

## Phase 6b — Generate HTML report

Build a spec JSON from the approved report content and the Phase 5 JSON output. Write it to `/tmp/sum_html_spec.json`, then write the HTML file directly to `reports/sum_report_YYYY-MM-DD.html`.

### Spec JSON structure

```json
{
  "project_name": "Mobile Banking App",
  "study_name": "Mobile Banking App — V1",
  "takeaway": "Both tasks fall in the poor or critical range — Transfer Funds is the priority due to near-zero satisfaction and a broken Quick Actions shortcut causing one-in-three failures.",
  "research_question": "Can users check their balance and initiate transfers independently, without guidance, in a single session?",
  "method_description": "Moderated 1:1 usability sessions, 15 participants per task, scored using SUM at 90% confidence.",
  "how_to_use": "Scores below 60% indicate tasks requiring redesign. Use the Insights tab for prioritized recommendations. Task tabs show where users succeed and where they break down.",
  "date": "YYYY-MM-DD",
  "alpha": 0.10,
  "versions": ["V1"],
  "participants_per_task": 15,
  "has_notes": true,
  "tasks": [
    {
      "id": "find-balance",
      "name": "Find Balance",
      "headline_finding": "Users can find their balance but over half take a wrong path first, relying on Search or Settings before discovering the Accounts tab.",
      "sum_by_version": {
        "V1": {
          "sum": 0.535, "ci_low": 0.36, "ci_high": 0.676,
          "completion": {"pct": 0.737, "ci_low": 0.509, "ci_high": 0.964},
          "satisfaction": {"displayed_pct": 0.356, "ci_low": 0.218, "ci_high": 0.484},
          "time": {"displayed_pct": 0.468, "ci_low": 0.351, "ci_high": 0.581,
                   "time_spec": 60.25, "time_spec_source": "derived"}
        }
      },
      "path_analysis": {
        "first_click_accuracy_n": 8, "first_click_accuracy_total": 15,
        "outcomes": {"DS": 8, "IS": 4, "DF": 2, "IF": 1},
        "correct_paths": [
          "Home → Accounts tab → Checking account → Balance overview",
          "Home → Summary widget → Account details"
        ],
        "path_distribution": [
          {"label": "Path A — Accounts tab", "pct": 0.83},
          {"label": "Path B — Summary widget", "pct": 0.17}
        ],
        "narrative": "All failures were direct — participants who failed never found the Accounts tab. The entry-point on the home screen is the problem, not the flow once entered."
      },
      "working_well": [
        {
          "finding": "Once users reach the Accounts tab, the balance is immediately visible and clearly formatted.",
          "supporting_evidence": "All 12 completers read the balance with no hesitation after reaching the tab. P03 completed in 12 seconds via the Summary widget path.",
          "confidence": "high"
        }
      ],
      "issues": [
        {
          "finding": "The Accounts tab is not discovered first — most users try Search, Settings, or Quick Actions instead.",
          "supporting_evidence": "7 of 15 participants took an incorrect first step; P07 and P15 failed the task entirely without ever finding the Accounts tab.",
          "confidence": "high"
        },
        {
          "finding": "Search is used as a navigation fallback, suggesting the home screen hierarchy doesn't match users' mental model.",
          "supporting_evidence": "P06 and P09 both typed into the search bar before discovering the Accounts tab organically.",
          "confidence": "medium"
        }
      ],
      "task_recommendations": [
        {
          "headline": "Add a home screen balance summary widget linking directly to the Accounts tab.",
          "body": "A persistent balance widget reduces wrong-turn navigation and increases first-click accuracy without requiring navigation restructuring.",
          "confidence": "high"
        },
        {
          "headline": "Increase visual prominence of the Accounts tab label or icon.",
          "body": "Test a more descriptive label or a visible balance teaser — the current tab doesn't signal 'account information lives here.'",
          "confidence": "medium"
        }
      ]
    }
  ],
  "overall_by_version": {
    "V1": {"sum": 0.443, "ci_low": 0.299, "ci_high": 0.558}
  },
  "insights": [
    {
      "rank": 1,
      "finding": "The Quick Actions transfer shortcut routes users to a different screen or triggers re-authentication, causing abandonment.",
      "so_what": "For customers: a broken shortcut on a primary financial action creates distrust in the app. For the business: failed transfers mean lost transactions and elevated churn risk.",
      "recommendation": "Fix or remove the Quick Actions transfer shortcut — align both transfer paths to the same destination or remove the shortcut until it is consistent.",
      "task": "Transfer Funds",
      "supporting_evidence": "8 of 15 participants tried the shortcut; 3 gave up entirely (DF/IF). All 4 IS recoveries required restarting through the Accounts tab.",
      "confidence": "high"
    }
  ],
  "methodology": {
    "format": "Moderated 1:1 usability sessions with think-aloud protocol.",
    "participants": "15 participants per task (same pool). Recruited for regular mobile banking use.",
    "tasks_tested": "Find Balance, Transfer Funds",
    "confidence_level": "90% CI (alpha = 0.10). Satisfaction spec: 4.0 / 5.0.",
    "time_spec_notes": [
      "Find Balance — derived automatically (60.25s, 95th percentile of satisfied completers)",
      "Transfer Funds — manual (120s; no participant both completed and rated composite satisfaction ≥ 4.0)"
    ]
  }
}
```

**Multi-version note:** When `versions` has 2–3 entries, show bars grouped by task in the Overview chart. For each task, if one version's `ci_high < other_version's ci_low`, mark with a `.sig-badge` "Sig." — non-overlapping CIs at the chosen alpha indicate a statistically significant difference.

---

### CSS additions

Reuse the concept-testing CSS verbatim (design tokens, fonts, tab system, card patterns) from `data/examples/personal_finance_study/example_report.html`. Append:

```css
/* === SUM bar chart (Overview) === */
.sum-chart { margin: 24px 0 32px; }
.chart-grid-wrap { position: relative; padding-left: 160px; margin-right: 60px; }
.chart-task-row { display: flex; align-items: center; margin-bottom: 28px; position: relative; }
.chart-task-label { position: absolute; left: -160px; width: 148px; text-align: right;
  font-size: 13px; font-weight: 500; color: var(--ink); padding-right: 12px; line-height: 1.3; }
.chart-version-bars { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.bar-row { display: flex; align-items: center; gap: 10px; }
.bar-version-tag { font-family: var(--mono); font-size: 10px; color: var(--ink-mute);
  width: 22px; flex-shrink: 0; }
.bar-track { flex: 1; height: 28px; background: var(--rule-soft); border-radius: 3px;
  position: relative; overflow: visible; }
.bar-fill { position: absolute; left: 0; top: 0; height: 100%; border-radius: 3px; min-width: 2px; }
.bar-fill.good { background: var(--pos); }
.bar-fill.moderate { background: var(--mixed); }
.bar-fill.poor { background: var(--neg); }
.error-bar-line { position: absolute; top: 50%; transform: translateY(-50%);
  height: 2px; background: var(--ink); opacity: 0.5; border-radius: 1px; pointer-events: none; }
.error-bar-line::before, .error-bar-line::after { content: ''; position: absolute;
  top: -4px; width: 0; height: 10px; border-left: 2px solid var(--ink); opacity: 0.7; }
.error-bar-line::before { left: 0; }
.error-bar-line::after { right: -2px; }
.bar-score-label { position: absolute; left: calc(100% + 8px); top: 50%;
  transform: translateY(-50%); font-family: var(--mono); font-size: 12px;
  font-weight: 600; color: var(--ink); white-space: nowrap; }
.baseline-line { position: absolute; top: 0; bottom: 0; left: 80%;
  border-left: 2px dashed var(--mixed); opacity: 0.55; pointer-events: none; }
.baseline-label { position: absolute; top: -22px; left: 80%; transform: translateX(-50%);
  font-family: var(--mono); font-size: 10px; color: var(--mixed);
  white-space: nowrap; letter-spacing: 0.05em; }
.chart-axis-labels { display: flex; justify-content: space-between; padding: 6px 0 0;
  font-family: var(--mono); font-size: 10px; color: var(--ink-mute); }
.sig-badge { font-family: var(--mono); font-size: 9px; letter-spacing: 0.1em;
  text-transform: uppercase; padding: 2px 6px; border-radius: 2px; margin-left: 6px;
  background: rgba(47,95,58,0.12); color: var(--pos); white-space: nowrap; }
.chart-info-note { font-family: var(--mono); font-size: 11px; color: var(--ink-mute);
  margin-top: 8px; }

/* === Dimension blocks (task hero) === */
.task-hero { display: grid; grid-template-columns: 1fr 2fr; gap: 32px;
  align-items: start; margin-bottom: 40px; padding-bottom: 32px;
  border-bottom: 1px solid var(--rule); }
.dim-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.dim-block { background: var(--bg); border: 1px solid var(--rule-soft);
  border-radius: 4px; padding: 14px 18px; }
.dim-label { font-family: var(--mono); font-size: 10px; text-transform: uppercase;
  letter-spacing: 0.12em; color: var(--ink-mute); margin-bottom: 6px; }
.dim-score { font-family: var(--serif); font-size: 30px; font-weight: 500;
  line-height: 1; letter-spacing: -0.02em; }
.dim-score.good { color: var(--pos); }
.dim-score.moderate { color: var(--mixed); }
.dim-score.poor { color: var(--neg); }
.dim-ci { font-family: var(--mono); font-size: 11px; color: var(--ink-mute); margin-top: 4px; }
.dim-note { font-size: 11px; color: var(--ink-mute); font-style: italic; margin-top: 5px; }
.ci-bar-wrap { position: relative; height: 4px; background: var(--rule-soft);
  border-radius: 2px; margin: 8px 0 4px; }
.ci-bar-fill { position: absolute; height: 100%; background: var(--ink-mute);
  border-radius: 2px; opacity: 0.35; }
.ci-bar-point { position: absolute; top: -4px; width: 2px; height: 12px;
  background: var(--ink); border-radius: 1px; transform: translateX(-50%); }
.interp-badge { display: inline-block; font-family: var(--mono); font-size: 10px;
  letter-spacing: 0.1em; text-transform: uppercase; padding: 4px 10px;
  border-radius: 2px; margin-top: 10px; }
.interp-badge.good { background: rgba(47,95,58,0.12); color: var(--pos); }
.interp-badge.moderate { background: rgba(138,110,26,0.12); color: var(--mixed); }
.interp-badge.poor { background: rgba(155,42,42,0.10); color: var(--neg); }
.interp-badge.critical { background: var(--neg); color: white; }

/* === Outcome bar === */
.outcome-bar { display: flex; height: 20px; border-radius: 2px; overflow: hidden;
  background: var(--rule-soft); margin: 14px 0 8px; }
.outcome-bar .seg { height: 100%; display: flex; align-items: center;
  justify-content: center; font-size: 10px; color: white;
  font-weight: 700; font-family: var(--mono); }
.outcome-bar .seg.DS { background: var(--pos); }
.outcome-bar .seg.IS { background: var(--mixed); }
.outcome-bar .seg.DF { background: var(--neg); }
.outcome-bar .seg.IF { background: #6b1c1c; }
.outcome-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.outcome-table th { font-family: var(--mono); font-size: 10px; text-transform: uppercase;
  letter-spacing: 0.1em; color: var(--ink-mute); padding: 6px 8px;
  border-bottom: 1px solid var(--rule-soft); text-align: left; }
.outcome-table td { padding: 8px 8px; border-bottom: 1px solid var(--rule-soft);
  color: var(--ink-soft); }
.outcome-table td:first-child { font-weight: 500; color: var(--ink); }
.path-dist-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 14px; }
.path-dist-table th { font-family: var(--mono); font-size: 10px; text-transform: uppercase;
  letter-spacing: 0.1em; color: var(--ink-mute); padding: 6px 8px;
  border-bottom: 1px solid var(--rule-soft); text-align: left; }
.path-dist-table td { padding: 8px 8px; border-bottom: 1px solid var(--rule-soft);
  color: var(--ink-soft); font-size: 13px; }
.path-dist-table td:last-child { font-family: var(--mono); font-weight: 500; color: var(--ink); }
.first-click-stat { font-family: var(--mono); font-size: 28px; font-weight: 500;
  color: var(--ink); line-height: 1; }
.first-click-label { font-size: 13px; color: var(--ink-soft); margin-top: 4px; }

/* === Insight cards (Insights tab — full with evidence) === */
.insight-full-card { background: var(--paper); border: 1px solid var(--rule);
  border-radius: 4px; padding: 26px 30px; margin-bottom: 20px; box-shadow: var(--shadow); }
.insight-rank { font-family: var(--mono); font-size: 22px; font-weight: 500;
  color: var(--accent); line-height: 1; margin-bottom: 12px; }
.insight-finding { font-family: var(--serif); font-size: 18px; font-weight: 500;
  line-height: 1.35; margin: 0 0 14px; color: var(--ink); }
.insight-section-label { font-family: var(--mono); font-size: 10px; text-transform: uppercase;
  letter-spacing: 0.12em; color: var(--ink-mute); margin: 16px 0 6px; }
.insight-body { font-size: 14.5px; color: var(--ink-soft); margin: 0 0 8px; line-height: 1.6; }
.insight-evidence { font-size: 13px; color: var(--ink-soft); font-style: italic;
  border-left: 3px solid var(--rule); padding-left: 12px; margin: 10px 0 6px;
  line-height: 1.55; }
.insight-tag-row { display: flex; align-items: center; gap: 8px; margin-top: 14px;
  flex-wrap: wrap; }
.tag-task { font-family: var(--mono); font-size: 10px; letter-spacing: 0.08em;
  text-transform: uppercase; padding: 3px 10px; border-radius: 2px;
  background: var(--bg); border: 1px solid var(--rule); color: var(--ink-soft); }
.conf-badge { font-family: var(--mono); font-size: 10px; letter-spacing: 0.08em;
  text-transform: uppercase; padding: 3px 8px; border-radius: 2px; }
.conf-badge.high { background: rgba(47,95,58,0.12); color: var(--pos); }
.conf-badge.medium { background: rgba(138,110,26,0.10); color: var(--mixed); }
.conf-badge.low { background: rgba(28,26,23,0.06); color: var(--ink-mute); }

/* === Insight preview cards (Overview) === */
.insight-preview-card { background: var(--paper); border: 1px solid var(--rule);
  border-radius: 4px; padding: 20px 24px; margin-bottom: 12px; box-shadow: var(--shadow); }
.insight-preview-num { font-family: var(--mono); font-size: 10px; color: var(--accent);
  letter-spacing: 0.1em; margin-bottom: 8px; }
.insight-preview-finding { font-family: var(--serif); font-size: 16px; font-weight: 500;
  line-height: 1.35; margin: 0 0 8px; color: var(--ink); }
.insight-preview-rec { font-size: 13.5px; color: var(--ink-soft); margin: 0 0 10px;
  line-height: 1.55; }
.view-all-link { display: inline-flex; align-items: center; gap: 6px;
  font-family: var(--mono); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--accent); text-decoration: none; margin-top: 16px; border-bottom: 1px solid transparent; }
.view-all-link:hover { border-bottom-color: var(--accent); }

/* === Finding cards (task tabs) === */
.finding-card { background: var(--paper); border: 1px solid var(--rule-soft);
  border-radius: 4px; padding: 16px 20px; margin-bottom: 12px; }
.finding-card.working { border-left: 3px solid var(--pos); }
.finding-card.issue { border-left: 3px solid var(--neg); }
.finding-text { font-size: 14.5px; font-weight: 500; color: var(--ink); margin: 0 0 8px; }
.finding-evidence { font-size: 13px; color: var(--ink-soft); border-left: 2px solid var(--rule);
  padding-left: 10px; margin: 6px 0 10px; line-height: 1.55; }
.finding-meta { display: flex; align-items: center; gap: 8px; }

@media (max-width: 880px) {
  .task-hero { grid-template-columns: 1fr; }
  .dim-grid { grid-template-columns: 1fr; }
  .chart-grid-wrap { padding-left: 0; margin-right: 0; }
  .chart-task-label { position: static; width: auto; text-align: left;
    padding: 0 0 6px; font-size: 13px; }
  .chart-task-row { flex-direction: column; align-items: stretch; }
}
```

---

### Tab and section structure

**Tabs:** `01 Overview` · `02 Insights` · `03–12 [Task Name]` (one per task, up to 10) · `N Methodology`

Use the `.tabnav` / `.tab` / `.panel` system from the concept-testing example. Tab `data-target` values: `overview`, `insights`, `task-[id]` (hyphenated task name), `method`.

---

**Masthead:**
```html
<p class="eyebrow">Usability Testing Report · [study_name]</p>
<h1>[project_name]</h1>
<div class="meta">
  <span>Date <strong>[date]</strong></span>
  <span>Participants <strong>[N] per task</strong></span>
  <span>Tasks <strong>[N]</strong></span>
  <span>Version(s) <strong>[V1] [/ V2]</strong></span>
  <span>Method <strong>SUM · 90% CI</strong></span>
</div>
```

---

**Overview tab (`id="overview"`):**

*§01 — Takeaway and study context:*
```html
<p class="lead">[takeaway]</p>
<div class="card">
  <dl class="def-list">
    <dt>Research question</dt><dd>[research_question]</dd>
    <dt>Method</dt><dd>[method_description]</dd>
    <dt>How to use</dt><dd>[how_to_use]</dd>
  </dl>
</div>
```

*§02 — SUM score chart:*

Pure HTML/CSS horizontal bar chart. One row per task, one bar per version.

```html
<div class="sum-chart">
  <div class="chart-grid-wrap">
    <!-- baseline at 80% -->
    <div class="baseline-line"></div>
    <span class="baseline-label">80% · industry baseline</span>

    <!-- one .chart-task-row per task -->
    <div class="chart-task-row">
      <span class="chart-task-label">[task name]</span>
      <div class="chart-version-bars">
        <!-- one .bar-row per version -->
        <div class="bar-row">
          <span class="bar-version-tag">V1</span>
          <div class="bar-track">
            <div class="bar-fill [good|moderate|poor]" style="width:[sum*100]%"></div>
            <div class="error-bar-line"
                 style="left:[ci_low*100]%;width:calc([ci_high*100]% - [ci_low*100]%)"></div>
            <span class="bar-score-label">[sum_pct]%</span>
          </div>
          <!-- Only if 2+ versions AND this task is statistically significant: -->
          <span class="sig-badge">Sig.</span>
        </div>
      </div>
    </div>

    <div class="chart-axis-labels">
      <span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span>
    </div>
  </div>
  <p class="chart-info-note">Error bars show 90% CI. Dotted line = 80% industry baseline.
    <a href="#" data-target="method" style="color:var(--accent)">Score scale in Methodology →</a></p>
</div>
```

Color the bar fill: `good` (≥ 80%), `moderate` (60–79%), `poor` (< 60%).

*§03 — Insights preview:*

Show the top 3 insights (or all if fewer). Each as `.insight-preview-card`:
```html
<div class="insight-preview-card">
  <div class="insight-preview-num">0[n]</div>
  <p class="insight-preview-finding">[finding]</p>
  <p class="insight-preview-rec">→ [recommendation]</p>
  <div style="display:flex;gap:8px;align-items:center;">
    <span class="tag-task">Task: [task]</span>
    <span class="conf-badge [high|medium|low]">[confidence]</span>
  </div>
</div>
```

No supporting evidence in preview cards.

After the last card:
```html
<a href="#" class="view-all-link" data-target="insights">View all insights →</a>
```

---

**Insights tab (`id="insights"`):**

One `.insight-full-card` per insight in `insights[]`:
```html
<div class="insight-full-card">
  <div class="insight-rank">0[rank]</div>
  <p class="insight-finding">[finding]</p>
  <div class="insight-section-label">So what</div>
  <p class="insight-body">[so_what]</p>
  <div class="insight-section-label">Recommendation</div>
  <p class="insight-body">[recommendation]</p>
  <p class="insight-evidence">[supporting_evidence]</p>
  <div class="insight-tag-row">
    <span class="tag-task">Task: [task]</span>
    <span class="conf-badge [high|medium|low]">[confidence]</span>
  </div>
</div>
```

No accuracy flags. No contradiction checks.

---

**Per-task tab (`id="task-[id]"`):**

*Task hero:* Two-column grid:
- Left: task name (serif), SUM % (colored), CI range, interpretation badge
- Right: `.dim-grid` — three `.dim-block` entries (Completion / Satisfaction / Time). Each:
  - `.dim-label`, `.dim-score.[good|moderate|poor]`, `.ci-bar-wrap` → `.ci-bar-fill` + `.ci-bar-point`, `.dim-ci`, `.dim-note` (completers count; time spec for Time)

*Headline finding:* `<p class="lead" style="font-style:italic">[headline_finding]</p>`

*Path analysis* *(omit if `has_notes: false` or `path_analysis: null`):*
```html
<div class="first-click-stat">[n] / [total]</div>
<p class="first-click-label">participants' first click was on a correct path element — [pct]% first-click accuracy.</p>
<div class="outcome-bar">
  <div class="seg DS" style="width:[DS/total*100]%">[DS]</div>
  <div class="seg IS" style="width:[IS/total*100]%">[IS]</div>
  <div class="seg DF" style="width:[DF/total*100]%">[DF]</div>
  <div class="seg IF" style="width:[IF/total*100]%">[IF]</div>
</div>
<!-- outcome table, path distribution table, narrative <p> -->
```

*"What's working well" section* *(omit if `working_well` is empty):*
```html
<h3>What's working well</h3>
<div class="finding-card working">
  <p class="finding-text">[finding]</p>
  <p class="finding-evidence">[supporting_evidence]</p>
  <div class="finding-meta"><span class="conf-badge [level]">[confidence]</span></div>
</div>
```

*"Issues" section* *(omit if `issues` is empty):*
```html
<h3>Issues</h3>
<div class="finding-card issue">
  <p class="finding-text">[finding]</p>
  <p class="finding-evidence">[supporting_evidence]</p>
  <div class="finding-meta"><span class="conf-badge [level]">[confidence]</span></div>
</div>
```

*"Recommendations" section:*
```html
<h3>Recommendations</h3>
<ol style="padding-left:20px;color:var(--ink-soft);font-size:14.5px;line-height:1.7;">
  <li style="margin-bottom:14px;">
    <strong style="color:var(--ink);">[headline]</strong> — [body]
    <span class="conf-badge [level]" style="margin-left:8px;">[confidence]</span>
  </li>
</ol>
```

No quotes section. No accuracy flags.

---

**Methodology tab (`id="method"`):**

`method-grid` layout (two columns, insight cards):

*§01 — Study setup:* Format, participants, tasks tested, confidence level, time spec notes.

*§02 — SUM dimension definitions:* Completion (Wilson CI), Satisfaction (log-normal Z-score vs 4.0/5.0), Time (log-normal Z-score vs benchmark).

*§03 — Score interpretation* `(grid-column: 1/-1)`:
```html
<dl class="def-list">
  <dt>≥ 80%</dt><dd>Good usability — minor improvements needed. This is the industry baseline shown in the Overview chart.</dd>
  <dt>60–79%</dt><dd>Moderate — significant improvements warranted</dd>
  <dt>40–59%</dt><dd>Poor — redesign recommended for weak areas</dd>
  <dt>&lt; 40%</dt><dd>Critical failures — comprehensive redesign required</dd>
</dl>
```

*§04 — Confidence definitions:* High / Medium / Low with criteria (same `.conf-pips` pattern from concept-testing).

*§05 — Statistical significance* *(only if `versions` has 2+ entries):*
> At 90% confidence (alpha = 0.10), two versions are considered statistically significantly different for a given task when their SUM confidence intervals do not overlap. "Sig." badges in the Overview chart mark tasks where this threshold is met.

---

**Footer:**
```html
<footer>
  <span>Generated [date] · /sum-analysis</span>
  <span>Usability Testing Report · [study_name]</span>
</footer>
```

---

**JavaScript:**

Tab switcher (same 14-line script from the concept-testing example), plus a handler for `a[data-target]` links so the "View all insights →" link and the Methodology link in the chart work:

```javascript
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.target;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(target).classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
});
document.querySelectorAll('a[data-target]').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const target = link.dataset.target;
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.target === target));
    document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id === target));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
});
```

---

### After writing the file

Tell the researcher:

> HTML report saved to `reports/sum_report_YYYY-MM-DD.html`. Open in any browser. Tabs: Overview (takeaway, SUM chart, insights preview) · Insights (all findings with supporting evidence) · one tab per task · Methodology.

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
