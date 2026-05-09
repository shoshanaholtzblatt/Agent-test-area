# /concept-testing — UX Concept Evaluation

Evaluate early-stage UX concepts against pre-specified user needs by reconciling 3-point usefulness ratings with qualitative past-use stories and per-need explanations. Produces a concept × need verdict matrix with confidence levels, surfaces emergent needs, and outputs a self-contained HTML report.

This skill consumes a structured research plan (typically emitted by the research orchestrator; researchers can also author it by hand) and produces canonical `Finding` objects. See `docs/research_skills_schema.md` for shared types across research skills.

---

## What this skill does

1. Parses a structured research plan (`research_plan.md`) into typed `Need[]` and `Concept[]` objects
2. Validates a ratings CSV against the plan
3. Generates a pre-populated session-notes template for the researcher to fill while watching session videos
4. Flags rating-vs-explanation contradictions, missing evidence, and story-context mismatches
5. Inductively extracts concept aspects and detects emergent needs from past-use stories
6. Reconciles ratings + qualitative evidence into per-cell `Finding` objects (verdict + confidence + structured evidence)
7. Detects study-level patterns once (halo participants, sparse-coverage concepts, notable contradictions) — not repeated per cell
8. Synthesizes cross-concept insights — coverage by need, recurring drivers across concepts, strategic implications for the portfolio
9. Assigns each concept a **disposition** (`Advance` / `Iterate` / `Kill` / `Park` / `Advance — with follow-up`) with a one-sentence rationale grounded in the data
10. Surfaces designed-vs-actual gaps (concepts that missed targeted needs; concepts that addressed needs they weren't designed for)
11. Produces a markdown analysis review for researcher approval, then a self-contained tabbed HTML report

---

## Requirements before starting

- **Research plan** — markdown file with structured headings (template at `data/concept_research_plan_template.md`)
- **Ratings CSV** — one row per (participant × concept × need); rating values `completely | partially | not_at_all` (template at `data/concept_ratings_template.csv`)
- **Session notes** (after Phase 3) — markdown filled in by the researcher while watching session recordings
- **Concept assets** (optional) — image paths or text descriptions referenced in the research plan; embedded base64 in the final HTML

No fixed minimum-N. Confidence levels reflect available evidence (3+ for high, 2 or mixed-3+ for medium, 1 or contradictory for low).

---

## Phase 1 — Announce

When the user invokes `/concept-testing`, say:

> I'll help you evaluate UX concepts against the targeted needs in your research plan, reconciling 3-point ratings with qualitative past-use stories.
>
> I need three inputs:
> 1. **Research plan** (markdown) — listing needs (with definitions and evaluation criteria) and concepts (with descriptions and which needs each was designed to address). Use template at `data/concept_research_plan_template.md`. The research orchestrator emits this; you can also author it by hand.
> 2. **Ratings CSV** — columns `participant,concept_id,need_id,rating`. Rating values: `completely`, `partially`, `not_at_all`. Use template at `data/concept_ratings_template.csv`.
> 3. **Session notes** (markdown) — past-use story + per-need rating explanations for each (participant × concept). I'll generate a pre-populated template after you share the plan and ratings; you fill it in while watching the session videos and return it.
>
> You can paste content directly or share file paths.

---

## Phase 2 — Parse the research plan

Read `research_plan.md`. Extract a JSON object conforming to `ResearchPlan` (see `docs/research_skills_schema.md`):

```json
{
  "study_name": "...",
  "method": "concept_testing",
  "needs": [
    {
      "id": "N1",
      "statement": "...",
      "source": "odi|knowledge_map|manual",
      "source_metadata": {},
      "importance": null,
      "current_satisfaction": null,
      "evaluation_criteria": ["..."]
    }
  ],
  "concepts": [
    {
      "id": "C1",
      "name": "...",
      "description": "...",
      "target_needs": [{"need_id": "N1", "hypothesis": "..."}],
      "assets": ["/path/to/img.png"]
    }
  ],
  "participants": ["P01", "P02"]
}
```

Write this to `/tmp/concept_plan.json`. Confirm with the researcher:
- N needs (list IDs and statements)
- N concepts (list IDs, names, and which needs each is designed for)
- N participants (or "will infer from ratings CSV")

If the plan is malformed (missing required fields, target_needs reference unknown need IDs), report the issues and ask the researcher to fix the plan before continuing.

---

## Phase 3 — Validate ratings and scaffold session notes

### Step 1 — Validate the ratings CSV

Write the CSV to `/tmp/concept_ratings.csv`. Run (use the absolute path to `concept_aggregator.py` — resolve with `find` if needed):

```bash
python3 /absolute/path/to/concept_aggregator.py validate \
  --ratings /tmp/concept_ratings.csv \
  --plan-json /tmp/concept_plan.json
```

If validation fails, report the errors and ask the researcher to fix them. Common issues: invalid rating value, concept_id or need_id absent from the plan, duplicate rows, missing columns.

### Step 2 — Generate the session-notes scaffold

Write `reports/concept_session_notes_YYYY-MM-DD.md` (use today's date) with:
- Top-level HTML-comment block of fill-in instructions (copy from `data/concept_session_notes_template.md`)
- One `## P<id> × C<id>` section per (participant, concept) pair present in the ratings CSV, each pre-populated with a `### Past-use story` block and a `### Per-need ratings + explanations` table whose `need_id` column is filled in from the plan (rating, explanation, timestamp left blank)
- A `### Spontaneous mentions` block per section

Tell the researcher:

> I've created `reports/concept_session_notes_YYYY-MM-DD.md`. Please fill in:
> - **Past-use story** for each (participant × concept) — verbatim
> - **rating + explanation + timestamp** in each per-need table — verbatim explanations, no paraphrasing
> - **Spontaneous mentions** — anything participants said about needs/jobs *not* in the research plan
>
> Return the completed notes when you're done. If you don't have video access or want to skip notes, say so — I'll proceed with ratings only and cap confidence at Medium.

Wait for the completed notes before continuing to Phase 3b. If notes are skipped, jump to Phase 5 with `confidence ≤ medium` for all cells and no aspects/emergent needs sections.

---

## Phase 3b — Accuracy and contradiction checks

After notes return, scan every (participant × concept × need) cell and surface flags. Present grouped by (participant, concept). If no flags, say so briefly. **Flags are informational — do not block.**

| Check | Flag message |
|---|---|
| `rating = completely` AND explanation does not reference the need or any concept feature | "Rated `completely` but explanation is empty/off-topic — verify the explanation captured the rating reason." |
| `rating = not_at_all` AND explanation cites a concept feature that plausibly addresses the need | "Rated `not_at_all` but explanation mentions [feature]; possible scale confusion or mis-coded rating." |
| `rating = completely` AND past-use story does not describe a context where this need would arise | "Rated `completely` but past-use story does not describe a context where this need applies — judgment may be hypothetical, lower confidence." |
| All needs for a concept rated identically by one participant (all `completely` or all `not_at_all`) | "Uniform ratings across all needs — possible halo effect or rating fatigue; review explanations for genuine differentiation." |
| Explanation cell empty | "Missing explanation for [need_id] — cell will be evidence-light, lower confidence." |
| Past-use story missing entirely for a concept | "No past-use story for [concept] — confidence cap = medium for all cells in this concept." |
| Past-use story sentiment positive but all concept-need ratings ≤ `partially` | "Past-use story is positive but ratings are tepid — verify the participant understood the concept matched their story." |
| Explanation describes the concept making the need *worse* | "Possible `creates_new_problem` signal — explanation cites friction/anxiety/error introduced by the concept. Surface in Phase 4." |

---

## Phase 3c — Aspect extraction

For each concept, read every explanation across every participant. Inductively identify **aspects** — short noun-phrase themes that drove ratings.

Method:
- Identify recurring nouns/phrases (3+ mentions) and distinctive phrases (1–2 mentions but specific and quotable)
- Cluster near-synonyms (e.g., "automatic" + "auto-sort" + "does it for me" → "automatic categorization")
- Tag each aspect's `direction`: **up** (cited alongside `completely`/`partially` ratings), **down** (`not_at_all`/`partially`), or **mixed**
- Limit to 3–7 aspects per concept; merge less-frequent ones

Each aspect becomes a JSON object:
```json
{
  "concept_id": "C1",
  "label": "automatic categorization",
  "direction": "up",
  "count": 3,
  "representative_quotes": [
    {"snippet": "...", "participant_id": "P01", "polarity": "positive",
     "source_id": "notes:P01:C1", "location": "rating-row N2"}
  ]
}
```

---

## Phase 3d — Emergent needs detection

Scan all past-use stories and `Spontaneous mentions` blocks. Identify needs participants describe that are **not** in `research_plan.needs`.

Method:
- For each past-use story, list the jobs-to-be-done implied (what was the participant trying to accomplish? what made the moment hard?)
- Compare against plan needs by statement (not just ID)
- Anything mentioned by **2+ participants** and absent from the plan is an emergent need candidate
- For each, capture: short label (4–8 words), supporting verbatim quotes with `Evidence` shape, which concepts participants felt addressed it, which they felt missed it

Emergent needs are reported in a dedicated section but are **not** added to the matrix.

---

## Phase 4 — Reconcile to Findings

Run the aggregator to compute per-cell distributions:

```bash
python3 /absolute/path/to/concept_aggregator.py aggregate \
  --ratings /tmp/concept_ratings.csv \
  --plan-json /tmp/concept_plan.json \
  --out /tmp/concept_distributions.json
```

The output JSON shape:
```json
{
  "cells": {
    "C1": {
      "N1": {
        "completely": 3, "partially": 1, "not_at_all": 1,
        "n": 5, "majority": "completely", "majority_pct": 0.6,
        "raters": {"P01": "completely", "P02": "partially"},
        "was_targeted": true
      }
    }
  },
  "concept_summaries": {
    "C1": {"n_raters": 5, "raters": ["P01","..."], "n_cells_rated": 3, "is_sparse": false}
  },
  "study_summary": {
    "n_participants_total": 5,
    "uniform_rating_candidates": [
      {"participant_id": "P05", "concept_id": "C1", "rating": "completely", "n_cells": 3}
    ]
  }
}
```

`concept_summaries` and `study_summary` feed Phases 4c–4e. `uniform_rating_candidates` is a deterministic halo *candidate* signal — Claude validates by checking explanation text for vague/generic language before treating a participant as a confirmed halo case.

For each cell, produce one `Finding` (see `docs/research_skills_schema.md`) by combining the rating distribution with the qualitative evidence.

### Verdict rules

| Situation | Verdict |
|---|---|
| ≥60% `completely` AND explanations consistent | `addresses` |
| ≥60% `partially` (or mixed `completely`/`partially` with consistent explanations) | `partial` |
| ≥60% `not_at_all` AND explanations consistent | `doesnt_address` |
| Any explanation describes the concept actively making the need *worse* (introducing friction, anxiety, error) — even one strong instance | `creates_new_problem` (sticky — overrides positive rating majority; record `reconciliation_note`) |
| <2 participants with usable evidence, OR ratings and explanations strongly contradict with no resolution | `insufficient_evidence` |
| Majority rating clear but explanations contradict | Downgrade one level (`completely` → `partially`, `partially` → `not_at_all`); record `reconciliation_note` |
| Past-use story shows concept did serve this need historically but ratings are tepid | Upgrade one level; record `reconciliation_note` |

### Halo references in `reconciliation_note`

If a halo participant's rating affected the cell, **point to the lifted observation** rather than re-explain it. Phase 4c records the halo pattern once at study level; per-cell notes should reference that — not repeat it.

- ✅ `"P05 halo applied. 4/5 explicit not_at_all confirms the verdict."`
- ❌ `"P05's completely rating is part of a halo pattern (uniform completely across all C1 needs with vague generic language). Reduced its weight..."` (re-explains; belongs in Phase 4c, not here)

### Confidence rules

| Level | Criteria |
|---|---|
| **high** | 3+ participants with consistent ratings AND consistent explanations |
| **medium** | 2 consistent, OR 3+ mixed, OR no past-use story available for that concept |
| **low** | 1 only, OR ratings vs explanations conflict, OR explanations missing/empty — directional only, do not act on Low alone |

`creates_new_problem` is reportable at any confidence (single strong negative signal warrants surfacing).

### Evidence shape

Each Finding's `evidence` is an array of:
```json
{
  "source_id": "notes:P03:C1",
  "location": "rating-row N2",
  "snippet": "verbatim quote",
  "polarity": "positive|negative|neutral",
  "participant_id": "P03"
}
```

Use `notes:<participant>:<concept>` as the source_id for evidence drawn from the session notes. Prefer 2–3 evidence items per finding (one per polarity if the cell is mixed).

---

## Phase 4b — Designed-vs-actual gap

Compute two derived sections from the Findings:

- **Designed but missed** — Findings where `was_targeted = true` AND `verdict ∈ {partial, doesnt_address, creates_new_problem}`. The concept's designed-for hypothesis didn't hold.
- **Good surprises** — Findings where `was_targeted = false` AND `verdict = addresses`. The concept hit a need it wasn't designed for.

These are first-class findings — surface them prominently in the markdown review and the HTML report.

---

## Phase 4c — Study-level observations

Identify and record patterns *once* at study level. The HTML report surfaces these in the Cross-Concept Insights tab; per-cell `reconciliation_note`s reference them rather than repeat them.

### Halo participants

For each `(participant_id, concept_id)` in `study_summary.uniform_rating_candidates`, validate by checking the participant's explanation text for that concept:

- Vague/generic language ("yeah it's all good", "sure, this would help", "sounds fine") → confirmed halo
- Specific, differentiated explanations even with uniform ratings → not halo; some participants genuinely rate everything positively with reasons. Don't flag.

For each confirmed halo, record:
```json
{
  "participant_id": "P05",
  "scope": ["C1"],
  "rationale": "P05 rated `completely` across all C1 cells with vague, generic explanations like 'yeah it's all good'. Down-weighted in per-cell reconciliations; treat as directional only.",
  "applied_in_phase4": true
}
```

### Sparse-coverage concepts

For each concept where `concept_summaries[*].is_sparse == true`, record a `SparseCoverageObs`:
```json
{
  "concept_id": "C3",
  "n_raters": 3,
  "rationale": "Study ran out of time. C3 verdicts capped at medium confidence even with uniformly positive signal."
}
```

### Notable contradictions

Lift any cross-cutting rating-vs-explanation contradiction worth probing (rather than flagging at every cell). Example: a participant who rated something `completely` while voicing categorical distrust of automation. Record:
```json
{
  "participant_id": "P02",
  "concept_id": "C3",
  "need_id": "N2",
  "rationale": "P02 rated C3 `completely` on fraud while saying 'I don't trust automated alerts'. The rating was for the concept's shape; the comment was a category-level skepticism. Logged for follow-up, not as undermining the rating.",
  "snippet": "I don't really trust automated alerts. I always second-guess them."
}
```

---

## Phase 4d — Cross-concept synthesis

Read findings as a portfolio rather than as individual concepts. Produce `cross_concept_insights`:

### `coverage_by_need`

For each need, list every concept's verdict on it. Mark `is_single_point: true` when exactly one concept reaches `addresses`. Author a one-sentence `summary` calling out who owns the need and any noteworthy non-addressing verdicts.

```json
{
  "need_id": "N2",
  "owners": [
    {"concept_id": "C1", "verdict": "partial"},
    {"concept_id": "C2", "verdict": "creates_new_problem"},
    {"concept_id": "C3", "verdict": "addresses"}
  ],
  "is_single_point": true,
  "summary": "<strong>Single point of coverage.</strong> Only C3 actually solves it. C1's cadence is the cap; C2 makes things worse."
}
```

### `recurring_drivers`

Cluster aspects across concepts by semantic equivalence (e.g., "automatic categorization" + "real-time delivery" both map to "automation / no-effort affordances" if they're driving ratings the same way). For each cluster:

- `direction`: aggregate up / down / mixed across the citing concepts
- `citations`: list of `{concept_id, count}` per concept that surfaced the driver
- `note`: optional — call out semantic inversions (e.g. "automation as up-driver, manual-effort as down-driver are the same axis")

Aim for 3–6 recurring drivers across the whole study.

### `strategic_implications`

3–5 decision-relevant takeaways framed for the design/PM conversation. Must consider:

- **Portfolio completeness** — does any single concept address all needs?
- **Best combinatorial pairing** — which 2-concept set covers the most needs?
- **Primary unmet space** — emergent needs + partial-only cells

Each implication has `headline` (bold lead) + `body` (1–2 supporting sentences).

---

## Phase 4e — Disposition assignment

For each concept, apply the disposition rule using metrics from `concept_summaries`, the findings, and the study observations.

### Decision rule

| Disposition | When |
|---|---|
| `advance` | Addresses ≥ 50% of needs, no `creates_new_problem` verdicts, evidence is non-sparse, owns at least one need |
| `advance_with_followup` | Strong-positive but evidence is sparse OR a logged contradiction warrants probing OR a single high-stakes question remains |
| `iterate` | Owns a need but adoption-fragile (designed-for need came back `partial` due to adoption gap), OR mixed verdicts that suggest re-scoping |
| `kill` | Addresses no needs, OR widely creates_new_problem, OR clearly dominated by another concept |
| `park` | `insufficient_evidence` dominant; can't decide yet — re-test before deciding |

Author the rationale referencing specific cells and metrics. The rationale is the headline content for stakeholders — make it specific:

- ✅ "Strongest single concept in the portfolio: only one to address fraud, and a positive surprise on tracking. But evidence is sparse (n=3) and one participant's automation-distrust comment warrants probing."
- ❌ "Addresses some needs with some confidence; recommend further testing." (mechanical, no signal)

Each concept gets:
```json
{
  "verdict": "advance|advance_with_followup|iterate|kill|park",
  "label": "Advance — with follow-up",
  "rationale": "..."
}
```

---

## Phase 5 — Markdown analysis review

Write `reports/concept_review_YYYY-MM-DD.md` with this structure:

```markdown
# Concept Testing Analysis — [Study Name] — [date]

## Study summary
- Concepts: [list]
- Needs: [list with statements]
- Participants: [list with N]

## Accuracy & contradiction flags
[Phase 3b flag table, or "No flags."]

## Study-level observations
- **Halo participants:** [P05 — short rationale, or "None detected"]
- **Sparse-coverage concepts:** [C3 — n=3 of 5, rationale]
- **Notable contradictions:** [P02 on C3 — short rationale]

## Verdict matrix

| Concept \ Need | [N1] | [N2] | ... |
|---|---|---|---|
| [C1] | ● addresses (high) ⊙ | ◐ partial (medium) ⊙ | ... |
| [C2] | ○ doesnt_address (low) | ⚠ creates_new_problem | ... |

Glyphs: ● addresses · ◐ partial · ○ doesnt_address · ⚠ creates_new_problem · ◌ insufficient_evidence
⊙ = was_targeted (concept was designed for this need)

## Designed-vs-actual gap

### Designed but missed
- **C1 → N2**: [one-sentence summary]

### Good surprises
- **C2 → N2**: [one-sentence summary]

## Cross-concept insights

### Coverage by need
| Need | C1 | C2 | C3 | Summary |
|---|---|---|---|---|
| N1 | ● | ◐ | ● | Well-covered. C1 owns it; C3 is a good surprise. |
| ...

### Recurring drivers
- **Automation / no-effort affordances** — driver-up — cited by C1 (4), C3 (3)
- **Manual effort & tagging burden** — driver-down — cited by C2 (4)
- ...

### Strategic implications
1. **Headline 1.** Body…
2. **Headline 2.** Body…

## Per-concept deep dives

### C1: [concept name] — Disposition: *Advance*
> [one-sentence rationale]

**Description:** [from plan]
**Designed for:** N1, N3

**Rating distribution:**
| Need | completely | partially | not_at_all | n |
|---|---|---|---|---|

**Past-use story synthesis:** [2–4 sentences with 1–2 representative blockquotes]

**Aspects:**
- [Aspect 1] — driver-up — cited by [N]

**Per-need findings:**

#### N1: [need statement] — *addresses* *(confidence: high)*
**Reconciliation:** [if any — point to lifted observations, don't re-explain halo]
> "[verbatim]" — P01

[qualitative texture if any]

[Repeat for each concept]

## Emergent needs

### [Emergent need label]
*(confidence: medium — surfaced in 2 of 5 past-use stories)*
> "[verbatim]" — P02
**Missed by:** [list]
[short commentary]
```

---

## Phase 5b — Approval gate

After presenting the markdown review, ask the researcher:

> Please review the matrix and findings. Flag any cells where you'd like me to revisit the verdict, adjust the confidence, or swap evidence quotes. Once you approve, I'll generate the final HTML report.

**Halt and wait for explicit approval.** Adjust the markdown review based on feedback and re-present until the researcher approves. Do not generate the HTML before approval.

---

## Phase 6 — Generate HTML

Build the complete spec JSON from the approved markdown content. The helper renders this into a tabbed HTML report (Overview · Cross-Concept Insights · one tab per concept · Methodology) with Harvey-ball verdicts, integrated confidence pips, designed-for accent dots, disposition badges, and a CSS-custom-property theme. See `data/examples/personal_finance_study/expected_spec.json` for a complete worked example.

```json
{
  "study_name": "...",
  "study_subtitle": "Concept Testing Report · <Project name>",
  "masthead_h1_html": "How <em>N</em> concepts address <em>M</em> needs.",
  "method_description": "Past-use stories + concept ratings",
  "date": "YYYY-MM-DD",
  "participants": ["P01"],
  "needs": [{"id": "N1", "statement": "...", "label": "..."}],
  "concepts": [
    {
      "id": "C1",
      "name": "...",
      "description": "...",
      "target_needs": [{"need_id": "N1", "hypothesis": "..."}],
      "stimulus_image": {
        "path": "/abs/path.png or null",
        "label": "Stimulus image",
        "name": "Short description of what the stimulus shows"
      },
      "disposition": {
        "verdict": "advance|advance_with_followup|iterate|kill|park",
        "label": "Advance",
        "rationale": "One to two specific sentences..."
      },
      "past_use_synthesis": "...",
      "past_use_quotes": [
        {"snippet": "...", "participant_id": "P01", "polarity": "positive|negative|neutral"}
      ],
      "aspects": [{"label": "...", "direction": "up|down|mixed", "count": 3}],
      "rating_distribution": [
        {"need_id": "N1", "completely": 3, "partially": 1, "not_at_all": 1, "n": 5}
      ],
      "dist_note": "Optional caveat under the distribution table (e.g. sparse coverage)."
    }
  ],
  "findings": [
    {
      "concept_id": "C1", "need_id": "N1",
      "was_targeted": true,
      "verdict": "addresses",
      "confidence": "high",
      "reconciliation_note": null,
      "evidence": [
        {"snippet": "...", "participant_id": "P01",
         "polarity": "positive", "source_id": "notes:P01:C1",
         "location": "rating-row N1"}
      ],
      "notes": "..."
    }
  ],
  "emergent_needs": [
    {
      "label": "...",
      "confidence": "medium",
      "confidence_note": "Surfaced unprompted in 2/5 past-use stories",
      "evidence": [{"snippet": "...", "participant_id": "P02"}],
      "addressed_by": [],
      "missed_by": ["C1", "C2"],
      "commentary": "Optional paragraph for the cross-concept tab full treatment."
    }
  ],
  "cross_concept_insights": {
    "lead_paragraph": "Three concepts read as a portfolio...",
    "coverage_intro": "...",
    "coverage_by_need": [
      {
        "need_id": "N2",
        "owners": [
          {"concept_id": "C1", "verdict": "partial"},
          {"concept_id": "C2", "verdict": "creates_new_problem"},
          {"concept_id": "C3", "verdict": "addresses"}
        ],
        "is_single_point": true,
        "summary": "<strong>Single point of coverage.</strong> Only C3..."
      }
    ],
    "drivers_intro": "...",
    "recurring_drivers": [
      {"label": "...", "direction": "up", "citations": [{"concept_id": "C1", "count": 4}], "note": null}
    ],
    "drivers_outro": "...",
    "methodology_intro": "...",
    "implications_intro": "...",
    "strategic_implications": [
      {"headline": "Bold lead.", "body": "Supporting sentence."}
    ]
  },
  "study_observations": {
    "halo_participants": [
      {"participant_id": "P05", "scope": ["C1"], "rationale": "...", "applied_in_phase4": true}
    ],
    "sparse_coverage": [
      {"concept_id": "C3", "n_raters": 3, "rationale": "..."}
    ],
    "contradictions": [
      {"participant_id": "P02", "concept_id": "C3", "need_id": "N2",
       "rationale": "...", "snippet": "..."}
    ]
  },
  "methodology": {
    "study_setup": {
      "format": "60-minute moderated 1:1 sessions...",
      "sample": "5 participants...",
      "concepts_tested": "...",
      "needs_tested": "..."
    }
  }
}
```

Write this to `/tmp/concept_html_spec.json`, then run:

```bash
python3 /absolute/path/to/concept_aggregator.py render-html \
  --spec /tmp/concept_html_spec.json \
  --out reports/concept_report_YYYY-MM-DD.html
```

Confirm to the researcher:
> HTML report saved to `reports/concept_report_YYYY-MM-DD.html`. Open in any browser. Tabbed layout: Overview, Cross-Concept Insights, one tab per concept, Methodology.

---

## Verdict and confidence quick reference

| Verdict | Meaning |
|---|---|
| `addresses` | Concept credibly serves this need based on participants' lived experience |
| `partial` | Concept addresses some aspects of the need but with caveats or gaps |
| `doesnt_address` | Concept does not credibly serve this need |
| `creates_new_problem` | Concept actively makes the need harder, introduces friction or new pain points |
| `insufficient_evidence` | Fewer than 2 participants with usable evidence, or unresolvable contradiction |

| Confidence | Interpretation |
|---|---|
| high | Pattern strong — actionable |
| medium | Pattern present — directional, validate further |
| low | Single signal or contradictory — do not act on this alone |
