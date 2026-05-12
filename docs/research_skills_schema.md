# Research Skills — Canonical Schema

Single source of truth for the data shapes shared across research-method skills in this repo (`/concept-testing`, future `/usability` retrofit, future skills coordinated by the research orchestrator).

This doc is **informational/specification only** — no code consumes it directly. Each skill's helper validates its own inputs, and the orchestrator emits research plans that conform to these shapes.

`/sum-analysis` predates this schema and will be aligned in a future PR.

---

## Top-level objects

### `Need`

A specific user job, problem, or outcome the study evaluates concepts against.

```ts
type Need = {
  id: string                   // stable, e.g. "need_supplement_funds_03"
  statement: string            // what the user is trying to do/achieve
  source: "odi" | "knowledge_map" | "manual"
  source_metadata: object      // ODI: {direction, metric, object, clarifier}; KM: {study_refs}
  importance: number | null    // populated by orchestrator when derived from ODI
  current_satisfaction: number | null
  evaluation_criteria: string[]   // what would "addressing this" look like in practice?
}
```

### `Concept`

A design idea being evaluated.

```ts
type Concept = {
  id: string
  name: string
  description: string                                     // 1–3 sentences
  target_needs: { need_id: string; hypothesis: string }[] // designed-for, asymmetric
  assets: string[]                                        // file paths or text descriptions
  stimulus_image?: {                                      // for HTML rendering
    path: string | null                                   // resolves to base64 if present
    label: string                                         // placeholder caption
    name: string                                          // short stimulus description
  }
  top_finding?: string                                    // 5–15 word punchy fragment for the concept tab (renamed from high_level_finding in v4)
  recommendation?: Recommendation                         // populated by the evaluating skill (Phase 4e)
  recommended_refinements?: string[]                      // 2–5 actionable next steps for this concept (v4)
  disposition?: Disposition                               // DEPRECATED alias of `recommendation` — see below
  high_level_finding?: string                             // DEPRECATED alias of `top_finding`
}
```

`target_needs` is **asymmetric on purpose**: a concept can address needs it didn't target (good surprise) or miss needs it did (designed-vs-actual gap). Findings should call out both directions.

### `ResearchPlan`

The orchestrator's output and the input to a research-method skill.

```ts
type ResearchPlan = {
  study_name: string
  method: "concept_testing" | "usability" | string   // discriminator
  needs: Need[]
  concepts: Concept[]                                // omit for non-concept methods
  participants: string[]                             // optional roster
}
```

### `ConceptTestingSpec` (top-level v4 shape)

The full spec the `/concept-testing` helper renders to HTML. Combines the plan, the per-cell findings, a single ordered insights list, and the per-concept leadership content.

```ts
type ConceptTestingSpec = {
  // Project context (supplied by the researcher in Phase 1)
  project_name: string                           // becomes the masthead h1
  study_name: string                             // longer/internal name
  research_question: string                      // verbatim on Overview
  method_description: string                     // default: concept testing past-use stories + ratings
  usage_guidance: string                         // "How to use these results" — 1–2 sentences
  poc: POC

  // Leadership brief (Claude-authored)
  single_sentence_takeaway: string               // one sentence
  insights: StructuredInsight[]                  // v4 — ordered, most decision-relevant first.
                                                 // Overview shows first 5 (compact, no evidence);
                                                 // Insights tab shows all (slide-like cards).

  // Synthesis & evidence
  study_observations: StudyObservations          // rendered on the Methodology tab
  concepts: Concept[]                            // each carries top_finding + recommendation + recommended_refinements
  findings: Finding[]
  emergent_needs: EmergentNeed[]                 // rendered on the concept tab where they were raised
}

type POC = {
  name: string
  role: string
  email: string
  links?: { label: string; url: string }[]   // e.g. Slack handle, page
}

type StructuredInsight = {
  insight: string                              // finding headline
  evidence: {
    snippet?: string                           // verbatim quote
    participant_id?: string
    metric?: string                            // e.g. "3/5 said wouldn't tag"
    source_ref?: string                        // anchor or concept name reference
  }[]
  so_what: string                              // why this matters for business + customer
  recommendation: string                       // v4: was `now_what` in v3
}
```

The Overview tab renders, in order: takeaway → research-question/method/how-to-use strip → Concept × Need matrix → Key Insights section (first 5 insights, compact) → View all concepts preview grid → Point of contact card. The Insights tab renders every entry in `spec.insights[]` as a slide-like card (finding + evidence + so-what + accent-boxed recommendation). The Methodology tab renders `study_observations`. Per-concept tabs render a compact hero, a headline section (top_finding + recommendation with confidence pips + text), the rating distribution, a per-need finding deep dive, an emergent-need card if applicable, and a 2–5-item recommended-refinements list.

**Removed in v4:** `top_findings`, `top_recommendations`, `key_insights` (all consolidated into `insights[]`); `cross_cutting`. The previous `concept.aspects` field is still accepted in the spec — the helper preserves the data but does not render it.

The orchestrator emits `ResearchPlan` as a markdown file with conventional headings (`research_plan.md`); the skill parses headings into this typed shape internally. See `data/concept_research_plan_template.md` for the markdown layout used by `/concept-testing`.

---

## Findings (output of any concept-evaluating skill)

### `Evidence`

A single piece of qualitative or quantitative support for a finding.

```ts
type Evidence = {
  source_id: string            // e.g. "notes:P03:C1" — which artifact this came from
  location: string             // e.g. "rating-row N2", "past-use story para 2", "transcript ~14:22"
  snippet: string              // VERBATIM quote
  polarity: "positive" | "negative" | "neutral"
  participant_id: string
}
```

`source_id` and `location` are deliberately permissive — v1 sources are notes-doc cells; future versions can add transcripts, video timestamps, log entries.

### `Finding`

One per (concept, need) cell of the result matrix.

```ts
type Finding = {
  need_id: string
  concept_id: string
  was_targeted: boolean              // derived from concept.target_needs
  verdict: "addresses"
         | "partial"
         | "doesnt_address"
         | "creates_new_problem"
         | "insufficient_evidence"
  confidence: "high" | "medium" | "low"
  evidence: Evidence[]
  reconciliation_note: string | null // present when verdict differs from raw rating majority
  notes: string                      // qualitative texture the verdict can't capture
}
```

### Verdict semantics

| Verdict | Meaning |
|---|---|
| `addresses` | Concept credibly serves this need based on participants' lived experience |
| `partial` | Concept addresses some aspects of the need but with caveats or gaps |
| `doesnt_address` | Concept does not credibly serve this need |
| `creates_new_problem` | Concept actively makes the need harder, introduces friction, or creates a new pain point. Sticky — overrides positive ratings when even one strong instance is present. Reportable at any confidence. |
| `insufficient_evidence` | Fewer than 2 participants with usable evidence, or ratings and explanations conflict with no resolution. Distinct from `doesnt_address`. |

### Confidence semantics

| Level | Criteria |
|---|---|
| `high` | 3+ participants with consistent ratings AND explanations pointing the same direction |
| `medium` | 2 participants consistent, OR 3+ with mixed signals, OR no past-use story available |
| `low` | 1 participant only, OR ratings vs explanations conflict, OR evidence is missing/empty. Directional only — do not act on Low alone. |

`creates_new_problem` is reportable at any confidence — a single strong negative signal warrants surfacing.

---

## Per-concept output objects

### `Aspect`

A theme inductively extracted from rating-explanation text within one concept.

```ts
type Aspect = {
  concept_id: string
  label: string                          // 2–6 words, noun phrase
  direction: "up" | "down" | "mixed"     // did it drive ratings up, down, or both?
  count: number                          // how many participants cited it
  representative_quotes: Evidence[]      // 1–3 verbatim
}
```

Aspect taxonomy is intentionally not predefined — extraction is inductive per study.

### `EmergentNeed`

A need surfaced in past-use stories that the `ResearchPlan.needs` list didn't anticipate.

```ts
type EmergentNeed = {
  label: string                          // 4–8 words
  confidence: "high" | "medium" | "low"
  confidence_note: string                // e.g. "surfaced in 3 of 5 past-use stories"
  evidence: Evidence[]
  addressed_by: string[]                 // concept_ids participants felt addressed it
  missed_by: string[]                    // concept_ids participants felt failed it
}
```

Emergent needs are reported in their own section. They are **not** added to the matrix (which stays scoped to `ResearchPlan.needs` so the design-judgment surface stays crisp).

---

## Designed-vs-actual gap

Two derived sections any concept-evaluating skill should emit, computable from `Finding[]` + `Concept.target_needs`:

- **Designed but missed** — Findings where `was_targeted = true` AND `verdict ∈ { partial, doesnt_address, creates_new_problem }`. The original hypothesis didn't hold.
- **Good surprises** — Findings where `was_targeted = false` AND `verdict = addresses`. The concept hit a need it wasn't designed for.

Both surface high-leverage insights for the next design iteration.

---

## Recommendation (per concept)

Each concept gets a Recommendation — the headline output for stakeholders making roadmap decisions. v4 uses free-form prose with a separate confidence indicator; the v2/v3 enum (`advance|iterate|kill|park|advance_with_followup`) is **deprecated**.

```ts
type Recommendation = {
  statement: string              // free-form prose (1–3 sentences) — what to do with this concept
  confidence: "high" | "medium" | "low"   // strength of evidence across the concept's cells
}
```

The statement should be specific and tied to data ("Strongest single concept — run a focused second round to n=5 before locking it into the MVP"), not generic ("recommend further testing"). Confidence summarizes evidence strength across the concept's cells; it visualizes in the report as pip dots (●●●/●●○/●○○) and an accompanying text label ("· high confidence").

### `Recommendation` *(v3 enum shape — deprecated)*

The v3 shape carried `{verdict, label, rationale}` where `verdict` was one of `advance | advance_with_followup | iterate | kill | park`. The helper still accepts this shape for one minor-version transition: it coerces `{verdict, rationale}` into `{statement: rationale, confidence: "medium"}` and logs a warning. New specs should write the v4 shape directly.

### `Disposition` *(deprecated — alias for the v3 `Recommendation` shape)*

`Disposition` was the v2 name. The field name `concept.disposition` is still accepted by the helper but maps through the v3 fallback. New specs should write `concept.recommendation` in v4 form.

---

## Cross-concept and study-level outputs

These are *single, study-wide* objects that the evaluating skill produces alongside the per-cell `Finding[]`.

### `StructuredInsight` *(v4 — single ordered list)*

In v4 the cross-concept synthesis collapses to a single ordered `spec.insights[]` list. Each entry is a `StructuredInsight` (see the top-level shape above). The first 5 render on the Overview as compact cards (no evidence); all entries render on the Insights tab as slide-like cards with finding + evidence + so-what + accent-boxed recommendation.

Author 7–10 insights, ordered by stakeholder impact. Source material includes:

- Cross-concept patterns ("no single concept covers the full need set")
- Individual concept results that change the strategic picture
- Recurring-driver patterns rewritten as human-language insights ("Automation and low-effort concepts were preferred") — **not** as a separate drivers table
- Emergent needs that are decision-relevant for the portfolio
- Methodological cautions only when they shift a leadership decision (otherwise keep them on the Method tab)

### `KeyInsights` *(deprecated in v4)*

The v3 `key_insights` object (with `coverage_by_need`, `recurring_drivers`, `additional_insights`, section-level so-what/now-what) is no longer rendered. The helper accepts v3 specs and stitches `top_findings + top_recommendations + key_insights.additional_insights` into the v4 `insights[]` list for one transitional minor version. Drivers and coverage tables are gone — rewrite that content as human-language insight cards.

**Methodological observations** (halo, sparse coverage, contradictions) continue to live in `study_observations` and render on the Methodology tab.

**Emergent needs** are rendered on the concept tab where they were raised (matched by `evidence.source_id`/`location` containing the concept ID). The cross-concept rollup belongs in `insights[]` if it changes the leadership decision.

### `StudyObservations`

Patterns lifted out of per-cell reconciliations and surfaced once at study level. Per-cell `reconciliation_note`s reference these rather than re-explain them.

```ts
type StudyObservations = {
  halo_participants: HaloParticipantObs[]
  sparse_coverage: SparseCoverageObs[]
  contradictions: ContradictionObs[]
}

type HaloParticipantObs = {
  participant_id: string
  scope: string[]                    // concept_ids where halo was confirmed
  rationale: string
  applied_in_phase4: boolean         // true if reconciliation down-weighted this participant
}

type SparseCoverageObs = {
  concept_id: string
  n_raters: number
  rationale: string                  // why is the coverage sparse?
}

type ContradictionObs = {
  participant_id: string
  concept_id?: string
  need_id?: string
  rationale: string
  snippet: string                    // verbatim quote
}
```

Halo detection has a deterministic candidate (uniform-rating across a concept's cells) and a qualitative confirmation (vague language in the explanations). Both required to confirm.
