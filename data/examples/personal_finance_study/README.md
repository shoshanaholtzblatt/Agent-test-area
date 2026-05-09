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
| `expected_spec.json` | Hand-crafted reconciled spec representing the output Claude should produce after Phase 4 reconciliation. Feeds `concept_aggregator.py render-html`. **Reference output** — not a strict regression target for LLM judgments. |

## Edge cases this study seeds

| Edge case | Where | What to look for |
|---|---|---|
| All 5 verdicts | findings | `addresses`, `partial`, `doesn't_address`, `creates_new_problem`, `insufficient_evidence` all present |
| Designed-but-missed | C1 → N2, C2 → N1 | targeted needs the concept failed to deliver on |
| Good surprise | C3 → N1 | a need addressed by a concept not designed for it |
| Sticky `creates_new_problem` | C2 × N2 | rating majority was `not_at_all`, escalated by P03's anxiety language |
| `insufficient_evidence` | C3 × N3 | n=1, no evidence to act on |
| Halo flag | P05 across C1 | uniform `completely` with vague generic explanations |
| Empty-explanation flag | P03 × C2 × N1 | rating present, explanation cell blank |
| Rating-vs-explanation contradiction | P02 × C3 × N2 | rated `completely` but expressed distrust |
| Emergent need | spontaneous mentions in P02 and P04 stories | "splitting bills with roommates" — absent from plan |

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
4. Claude proposes Findings (per-cell verdicts); researcher iterates with Claude until the markdown review is approved
5. Claude generates the final HTML report

`expected_spec.json` here represents what step 4's output should converge to for this dataset. It's a worked example, not a contract — different runs may produce slightly different evidence quotes or aspect labels.
