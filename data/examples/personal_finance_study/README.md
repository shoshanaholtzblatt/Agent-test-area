# Personal Finance Concept Study — worked example

A complete worked example for `/concept-testing`. Use this folder as a reference for what good inputs look like, what reconciled outputs look like, and to run the verification harness against the helper.

## What's in here

| File | Role |
|---|---|
| `research_plan.md` | Researcher- or orchestrator-authored research plan in the canonical markdown format. **Input** to the skill. |
| `ratings.csv` | Per-(participant × concept × need) ratings. **Input** to the skill. |
| `session_notes.md` | Filled-in session notes — past-use stories, per-need explanations, spontaneous mentions. **Input** to the skill (Phase 3 onwards). |
| `plan.json` | The `ResearchPlan` JSON shape that Claude produces internally after parsing `research_plan.md`. Feeds the helper's `validate` and `aggregate` subcommands. |
| `expected_distributions.json` | Output of `concept_aggregator.py aggregate` against the CSV + plan. Regenerate whenever the inputs change. |
| `expected_spec.json` | Hand-crafted reconciled spec representing the output Claude should produce after Phase 4 reconciliation. Feeds `concept_aggregator.py render-html`. v3 shape: `project_name` h1, `single_sentence_takeaway`, `research_question`, `usage_guidance`, `poc`, `top_findings[]` (3–7), `top_recommendations[]` (3–7), restructured `key_insights` with section-level `so_what` / `now_what`, per-concept `high_level_finding` + `recommendation` (renamed from `disposition`). **Reference output** — not a strict regression target for LLM judgments. |
| `example_report.html` | **Reference rendered HTML** — produced by `render-html` against `expected_spec.json`. Overview tab is a leadership brief (project name h1, takeaway, top findings, top recommendations, Concept × Need matrix, POC card). Renamed **Key Insights** tab (was Cross-Concept Insights). Per-concept tabs show a punchy **Finding** strip and a **Recommendation** badge. Regenerate after any change to `concept_aggregator.py` rendering or to `expected_spec.json`. |

### Viewing `example_report.html`

GitHub doesn't render HTML inline in its file viewer. To see the rendered report:

- **Locally:** clone the repo and open the file in any browser
- **From GitHub:** prefix the raw URL with `https://htmlpreview.github.io/?` — e.g. `https://htmlpreview.github.io/?https://raw.githubusercontent.com/<owner>/<repo>/<branch>/data/examples/personal_finance_study/example_report.html`

### Regenerating the reference HTML

After any change to `concept_aggregator.py` (CSS, SVG layout, HTML structure) or to `expected_spec.json`:

```bash
python3 concept_aggregator.py render-html \
  --spec data/examples/personal_finance_study/expected_spec.json \
  --out  data/examples/personal_finance_study/example_report.html
```

Commit the regenerated HTML alongside whatever change prompted the regeneration — the diff doubles as a visual review aid in PRs.

## Edge cases this study seeds

| Edge case | Where | What to look for |
|---|---|---|
| All 5 verdicts | findings | `addresses`, `partial`, `doesnt_address`, `creates_new_problem`, `insufficient_evidence` all present |
| Designed-but-missed | C1 → N2, C2 → N1 | targeted needs the concept failed to deliver on |
| Good surprise | C3 → N1 | a need addressed by a concept not designed for it |
| Sticky `creates_new_problem` | C2 × N2 | rating majority was `not_at_all`, escalated by P03's anxiety language |
| `insufficient_evidence` | C3 × N3 | n=1, no evidence to act on |
| Halo participant (lifted) | P05 across C1 | uniform `completely` with vague language; surfaced once in `study_observations.halo_participants`, referenced from per-cell notes |
| Sparse-coverage concept (lifted) | C3 (n=3 of 5) | surfaced once in `study_observations.sparse_coverage` |
| Cross-concept contradiction (lifted) | P02 × C3 × N2 | logged once in `study_observations.contradictions` |
| Emergent need | spontaneous mentions in P02 and P04 stories | "splitting bills with roommates" — absent from plan |
| Recommendation variety | per concept | C1 = `advance`, C2 = `iterate`, C3 = `advance_with_followup` |
| Single-point-of-coverage | N2, N3 in `coverage_by_need` | only one concept reaches `addresses` for these needs |

## How to run the verification harness against this study

From the repo root:

```bash
python3 scripts/run_example.py
```

This exercises `concept_aggregator.py` end-to-end (`validate` → `aggregate` → `render-html`) against the committed inputs and asserts the structural invariants. Exit 0 = pass. See the script for what's checked.

## How a researcher would actually use this skill

This study skips the live Claude session. In a real run the researcher would:

1. Hand `research_plan.md` (or a similar plan their orchestrator emits) and `ratings.csv` to Claude via `/concept-testing`
2. Claude generates a blank session-notes scaffold; researcher fills it in while watching session videos (the filled-in version here represents that step)
3. Claude runs Phase 3b accuracy checks, then Phase 3c/3d aspect and emergent-needs extraction
4. Claude proposes Findings (per-cell verdicts), Phase 4c study observations (halo / sparse / contradictions, lifted once), Phase 4d key-insights synthesis (coverage + drivers + additional insights with so-what/now-what), Phase 4e per-concept recommendations (Advance/Iterate/Kill/Park + rationale + high-level finding), and Phase 4f the leadership brief (single-sentence takeaway, 3–7 top findings, 3–7 top recommendations)
5. Researcher iterates with Claude until the markdown review is approved
6. Claude generates the final HTML report (tabbed: Overview as brief, Key Insights, per-concept tabs, Methodology)

`expected_spec.json` here represents what step 4's output should converge to for this dataset. It's a worked example, not a contract — different runs may produce slightly different evidence quotes or aspect labels.
