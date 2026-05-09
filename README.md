# Claude Code Research Skills

A repo of Claude Code skills for UX research methods. Skills will be coordinated by a future research orchestrator that picks the right method for a research question, emits a structured `ResearchPlan`, and routes execution to the right skill.

| Skill | Purpose |
|---|---|
| [`/concept-testing`](#concept-testing-concept-testing) | Early-stage UX concept evaluation — does a concept credibly serve specific user needs? |
| [`/sum-analysis`](#sum-analysis-sum-analysis) | Single Usability Metric scoring — late-stage usability evaluation |

Shared types (`Need`, `Concept`, `ResearchPlan`, `Finding`, `Evidence`) are documented in [`docs/research_skills_schema.md`](docs/research_skills_schema.md). `/concept-testing` conforms to this schema; `/sum-analysis` predates it and will be aligned in a separate PR.

---

## Concept Testing (`/concept-testing`)

Evaluate UX concepts against pre-specified user needs by reconciling 3-point usefulness ratings with qualitative past-use stories and per-need explanations. Produces a concept × need verdict matrix with confidence levels and a self-contained HTML report.

### What it does

1. **Parses a structured research plan** into typed `Need[]` and `Concept[]` objects (orchestrator-emittable; researcher-authorable)
2. **Validates a ratings CSV** against the plan — rating enum, ID consistency, no duplicates
3. **Generates a session-notes scaffold** for the researcher to fill while watching session recordings
4. **Flags rating-vs-explanation contradictions** — missing evidence, sentiment mismatches, story-context gaps
5. **Inductively extracts concept aspects** — themes that drove ratings up, down, or both
6. **Detects emergent needs** — needs surfaced in past-use stories that the plan didn't anticipate
7. **Reconciles each cell into a `Finding`** — verdict (5-value scale) + confidence + structured evidence + reconciliation note
8. **Lifts study-level patterns once** — halo participants, sparse-coverage concepts, notable contradictions (referenced from per-cell reconciliations rather than repeated)
9. **Synthesizes cross-concept insights** — coverage by need, recurring drivers across concepts, strategic implications for the portfolio
10. **Assigns each concept a disposition** — `Advance` / `Iterate` / `Kill` / `Park` / `Advance — with follow-up` with a one-sentence rationale grounded in specific cells
11. **Surfaces designed-vs-actual gap** — concepts that missed targeted needs; concepts that addressed needs they weren't designed for
12. **Markdown review with approval gate**, then **self-contained tabbed HTML report** (Overview · Cross-Concept Insights · per-concept tabs · Methodology) using Harvey-ball verdicts and a CSS-custom-property theme

### Verdict scale

| Verdict | Meaning |
|---|---|
| `addresses` (●) | Credibly serves the need |
| `partial` (◐) | Addresses some aspects with caveats |
| `doesnt_address` (○) | Does not credibly serve the need |
| `creates_new_problem` (⚠) | Actively makes the need harder; sticky — overrides positive ratings on a single strong instance |
| `insufficient_evidence` (◌) | <2 participants with usable evidence, or unresolvable contradiction |

Participant ratings stay 3-point (`completely | partially | not_at_all`); the 5-value verdict is the reconciled judgment the skill produces per cell.

### How to invoke

```
/concept-testing
```

### Inputs

| Input | Format | Template |
|---|---|---|
| Research plan | Markdown with structured headings | `data/concept_research_plan_template.md` |
| Ratings | CSV: `participant,concept_id,need_id,rating` | `data/concept_ratings_template.csv` |
| Session notes | Markdown (auto-scaffolded by the skill) | `data/concept_session_notes_template.md` |
| Concept assets | Image paths or text descriptions | referenced in research plan |

### Output files

| File | Description |
|---|---|
| `reports/concept_session_notes_YYYY-MM-DD.md` | Auto-scaffolded notes doc for researcher to fill while watching sessions |
| `reports/concept_review_YYYY-MM-DD.md` | Markdown analysis review (matrix + per-concept deep dives + emergent needs); requires researcher approval |
| `reports/concept_report_YYYY-MM-DD.html` | Self-contained final HTML report (inline CSS, inline SVG matrix, base64-embedded assets) |

### Dependencies

- Python 3 (standard library only)
- `concept_aggregator.py` in the project root

---

## SUM Analysis (`/sum-analysis`)

A Claude Code skill for analyzing usability test data using the **Single Usability Metric (SUM)** methodology developed by Jeff Sauro / MeasuringUsability.com.

### What it does

Run `/sum-analysis` in a Claude Code session to:

1. **Check your data for accuracy issues** — flags suspicious entries (inconsistent Likert scores, non-completers with high ratings, outlier times) before any calculation runs
2. **Generate a prioritized video watch list** — tells you which participant recordings to review most closely and creates a structured notes document
3. **Compute SUM scores** — per-task scores with 90% confidence intervals across three dimensions: Completion, Satisfaction, and Time
4. **Produce a full report** — results table, narrative summary, UX recommendations, and (if notes are provided) path analysis, quote verification, and finding confidence levels

### Requirements

| Requirement | Detail |
|---|---|
| Minimum participants | 15 per version per task |
| Likert ratings | 3 per participant: ease, satisfaction, perception (1–5 scale) |
| Completion | `1` = completed, `0` = did not complete |
| Time | Seconds — record for ALL participants, including non-completers |
| Version label | Use one label if single version; distinct labels (V1, V2) to compare versions side-by-side |

### How to invoke

```
/sum-analysis
```

Claude will walk you through each phase. You can provide data by pasting CSV text directly or sharing a file path.

### Input format

One row per participant per task:

```csv
version,task,participant,completion,ease,satisfaction,perception,time_s
V1,Task 1,P01,1,5,4,4,62
V1,Task 1,P02,0,2,2,3,145
```

A blank template is available at `data/sum_template.csv`.

### Skill workflow

| Phase | Description |
|---|---|
| 1 — Announce | Claude describes the data format and requirements |
| 3 — Data collection | Paste or upload your CSV; counts confirmed |
| 3b — Accuracy checks | Suspicious-row flags (inconsistent scores, completion-vs-rating mismatches, time outliers) |
| 3c — Watch list & notes | Tiered watch list + auto-scaffolded notes doc for video review |
| 4 — Validation | Structural error checks |
| 4b — Time spec fallback | Manual time benchmark if data-derived spec unavailable |
| 5 — Compute | Full SUM calculation |
| 6 — Report | Results table, narrative, UX recommendations, path/quote/contradiction analysis |

### Output files

| File | Description |
|---|---|
| `reports/sum_notes_YYYY-MM-DD.md` | Blank notes document created in Phase 3c for you to fill in |
| `reports/sum_report_YYYY-MM-DD.md` | Full report saved at the end of Phase 6 (optional) |

### Score interpretation

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

## Worked example & verification harness

[`data/examples/personal_finance_study/`](data/examples/personal_finance_study/) is a complete reference run of `/concept-testing` — full research plan, ratings CSV, filled-in session notes, parsed plan JSON, a hand-crafted reconciled spec, and a committed [`example_report.html`](data/examples/personal_finance_study/example_report.html) showing the actual rendered output. It deliberately seeds every interesting code path: all 5 verdicts, designed-but-missed cells, a good surprise, a sticky `creates_new_problem` escalation, an emergent need, and the halo / empty-explanation / contradiction flags.

To preview the rendered HTML directly from GitHub, prefix the raw URL with `https://htmlpreview.github.io/?` (GitHub's file viewer doesn't render HTML inline).

To verify the helper end-to-end against the committed sample:

```bash
python3 scripts/run_example.py
```

The script runs `validate` → `aggregate` → `render-html` and asserts:
- Aggregator output matches `expected_distributions.json` field-for-field
- Rendered HTML contains all 5 verdict-style classes, a populated "Designed but missed" section, a populated "Good surprises" section, the emergent-need label, the `creates_new_problem` glyph, and the `insufficient_evidence` stripe pattern

The script does not validate Claude's qualitative reconciliation — that's human-in-the-loop. The committed `expected_spec.json` is a reference output, not a regression target for LLM judgment.

---

## Repo layout

```
.claude/skills/
  concept-testing/SKILL.md
  sum-analysis/SKILL.md
data/
  concept_research_plan_template.md
  concept_ratings_template.csv
  concept_session_notes_template.md
  sum_template.csv
  sum_notes_template.md
  examples/
    personal_finance_study/         — worked example for /concept-testing
docs/
  research_skills_schema.md         — canonical types shared across research skills
scripts/
  run_example.py                    — verification harness
concept_aggregator.py               — helper for /concept-testing
sum_calculator.py                   — helper for /sum-analysis
reports/                            — generated outputs (gitignored)
```

## Dependencies

- Python 3 (standard library only — no installs required)
