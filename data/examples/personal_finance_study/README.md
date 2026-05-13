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
| `expected_spec.json` | Hand-crafted reconciled spec representing the output Claude should produce after Phase 4 reconciliation. Feeds `concept_aggregator.py render-html`. v4 shape: `project_name` h1, `single_sentence_takeaway`, `research_question`, `usage_guidance`, `poc`, a single ordered `insights[]` (7–10 entries replacing v3's `top_findings + top_recommendations + key_insights`), per-concept `top_finding` (renamed from `high_level_finding`) + `recommendation` ({statement, confidence} — no enum) + `recommended_refinements[]` (2–5 actionable items). **Reference output** — not a strict regression target for LLM judgments. |
| `example_report.html` | **Reference rendered HTML** — produced by `render-html` against `expected_spec.json`. Overview tab order: takeaway → 3-column research/method/use strip → Concept × Need matrix (no designed-for accent dot) → Key Insights section (first 5 insights, compact, no evidence) → `View all insights →` link → View all concepts preview grid → POC card. Renamed **Insights** tab — vertical stack of slide-like cards (finding + evidence + so-what + accent-boxed recommendation), one per `insights[]` entry. Per-concept tabs show a compact hero (visual + name + description only), a headline section (top finding + overall recommendation with pip dots AND text confidence), Needs deep dive cards, an emergent-need card if applicable, and a Recommended refinements list. Regenerate after any change to `concept_aggregator.py` rendering or to `expected_spec.json`. |

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
| Designed-but-missed (in finding notes) | Weekly auto-digest → Catch fraud quickly; Manual transaction tagger → Track recurring expenses | targeted needs the concept failed to deliver on; surfaces in the finding card's qualitative notes |
| Good surprise (in finding notes) | Smart spend alerts → Track recurring expenses | a need addressed by a concept not designed for it |
| Sticky `creates_new_problem` | Manual transaction tagger × Catch fraud quickly | rating majority was `not_at_all`, escalated by P03's anxiety language |
| `insufficient_evidence` | Smart spend alerts × Share with partner | n=1, no evidence to act on |
| Halo participant (lifted) | P05 across Weekly auto-digest | uniform `completely` with vague language; surfaced once in `study_observations.halo_participants`, referenced from per-cell notes |
| Sparse-coverage concept (lifted) | Smart spend alerts (n=3 of 5) | surfaced once in `study_observations.sparse_coverage` |
| Cross-concept contradiction (lifted) | P02 × Smart spend alerts × Catch fraud quickly | logged once in `study_observations.contradictions` |
| Emergent need (on concept tab) | spontaneous mentions in P02 and P04 stories during the Weekly auto-digest sessions | "splitting bills with roommates" — absent from plan; renders as an Emergent need card on the Weekly auto-digest tab |
| Recommendation confidence variety | per concept | Weekly auto-digest = high, Manual transaction tagger = medium, Smart spend alerts = medium (with a different rationale) |
| Refinement count variety | per concept | each concept has exactly 4 `recommended_refinements`; ranges 2–5 are valid |
| Insights consolidation | `insights[]` (9 entries) | seeds the Overview's compact Key Insights section (first 5) and the Insights tab (all entries as slide-like cards) |

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
4. Claude proposes Findings (per-cell verdicts), Phase 4c study observations (halo / sparse / contradictions, lifted once), Phase 4d insights synthesis (single ordered `insights[]`, 7–10 entries; human language only, no drivers vocabulary), Phase 4e per-concept top_finding + recommendation ({statement, confidence} — no enum), and Phase 4f per-concept `recommended_refinements` (2–5 each) + single-sentence takeaway
5. Researcher iterates with Claude until the markdown review is approved
6. Claude generates the final HTML report (tabbed: Overview, Insights, per-concept tabs, Methodology)

`expected_spec.json` here represents what step 4's output should converge to for this dataset. It's a worked example, not a contract — different runs may produce slightly different evidence quotes or aspect labels.
