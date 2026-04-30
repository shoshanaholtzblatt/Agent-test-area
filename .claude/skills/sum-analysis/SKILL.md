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

- **Minimum 15 participants per task** (the skill will reject smaller samples)
- **3 separate Likert ratings** per participant per task (ease, satisfaction, perception) on a **1–5 scale**
- **Task completion** recorded as `1` (completed) or `0` (did not complete)
- **Time in seconds** for every participant, including those who did not complete the task
- Errors/mistakes are **not** part of the SUM calculation in this version

---

## Phase 1 — Announce

When the user invokes `/sum-analysis`, say:

> I'll help you analyze your usability test data using the Single Usability Metric (SUM) methodology.
>
> I need one row per participant per task with these seven columns:
> - **task** — task name (e.g. "Search", "Checkout")
> - **participant** — participant ID (e.g. P01)
> - **completion** — `1` if they completed the task, `0` if not
> - **ease** — "How easy was this?" (1–5 Likert)
> - **satisfaction** — "How satisfied were you?" (1–5 Likert)
> - **perception** — "How well did it meet your needs?" (1–5 Likert)
> - **time_s** — time in seconds (record for ALL participants, even non-completers)
>
> **Minimum 15 participants per task.** Time benchmarks are derived automatically from your data — no spec needed.
>
> You can paste CSV rows directly, share a file path, or use the template at `data/sum_template.csv`.

---

## Phase 2 — Session config

Ask the researcher:

> What confidence level would you like for the intervals?
> - **90% CI** (alpha = 0.10, recommended — matches the original SUM methodology)
> - **95% CI** (alpha = 0.05)
> - **99% CI** (alpha = 0.01)

Default to 90% CI (alpha = 0.10) if they do not specify. Note that the satisfaction threshold is fixed at **4.0** (mid-point of "good" on the 1–5 scale).

---

## Phase 3 — Data collection

Ask the researcher to provide their data. Accept any of:
- Pasted CSV text (with or without header row)
- A file path to a `.csv` file

If they paste CSV text without a header, prepend:
```
task,participant,completion,ease,satisfaction,perception,time_s
```

If they have data for multiple tasks, all tasks can be in a single CSV — each task is identified by the `task` column value.

After receiving data, confirm how many tasks and participants were provided before proceeding.

---

## Phase 4 — Validation

Write the data to `/tmp/sum_analysis_data.csv`, then run:

```bash
python3 /path/to/sum_calculator.py --csv /tmp/sum_analysis_data.csv --alpha <alpha>
```

Use the **absolute path** to `sum_calculator.py` in the project (resolve it with `find` if needed).

If the script exits with an error (non-zero exit code or JSON with `"error"` key), show the researcher the error message and ask them to fix it. Common issues:
- Fewer than 15 participants for a task → ask for more data or to proceed with a note about limited statistical power
- Missing columns → show which columns are absent
- Values out of range → show which rows have invalid data

Do not proceed past validation until the data is clean.

---

## Phase 5 — Compute

Run the calculator (as above). Parse the output: everything before `---JSON-END---` is JSON; everything after is the markdown table.

The JSON structure is:
```json
{
  "alpha": 0.10,
  "z_crit": 1.645,
  "tasks": {
    "Task Name": {
      "n": 15,
      "completion": {"observed": 0.93, "pct": 0.88, "ci_low": 0.71, "ci_high": 0.96},
      "satisfaction": {"pct": 0.73, "ci_low": 0.58, "ci_high": 0.84, "mean": 4.2, "spec": 4.0},
      "time": {"pct": 0.88, "ci_low": 0.74, "ci_high": 0.95, "time_spec": 90.2},
      "sum": 0.83,
      "ci_low": 0.68,
      "ci_high": 0.92
    }
  },
  "overall": {"sum": 0.83, "ci_low": 0.68, "ci_high": 0.92}
}
```

---

## Phase 6 — Report

Present the markdown table produced by the script, then provide:

### Narrative summary

Write 2–4 sentences interpreting the overall SUM score:
- SUM ≥ 80%: generally good usability, minor improvements needed
- SUM 60–79%: moderate usability, significant improvements warranted
- SUM 40–59%: poor usability, redesign recommended for weak areas
- SUM < 40%: critical usability failures

Highlight which task(s) scored lowest and which dimension(s) drove the low score.

### Prioritized UX recommendations

Provide **3–5 specific, actionable recommendations** ranked by impact, based on the dimension scores:

- **Low Completion** (< 70%): Users are failing the task — investigate where they get stuck. Recommend task flow analysis, error recovery improvements, or clearer affordances.
- **Low Satisfaction** (< 60%): Users find the experience frustrating or confusing. Recommend UI clarity improvements, reduced cognitive load, or onboarding changes.
- **Low Time score** (< 60%): Users are taking much longer than efficient users. Recommend streamlining steps, improving discoverability, or reducing navigation depth.

Frame each recommendation around the specific task(s) and dimension(s) affected.

### Save option

Ask:
> Would you like me to save this report to `reports/sum_report_YYYY-MM-DD.md`?

If yes, write the full report (table + narrative + recommendations) to that path with today's date.

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
