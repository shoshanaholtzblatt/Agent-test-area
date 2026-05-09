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
  disposition?: Disposition                               // populated by the evaluating skill (Phase 4e)
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

## Disposition (per concept)

Each concept gets a Disposition — the headline output for stakeholders making roadmap decisions.

```ts
type Disposition = {
  verdict: "advance" | "advance_with_followup" | "iterate" | "kill" | "park"
  label: string                  // human-friendly label e.g. "Advance — with follow-up"
  rationale: string              // 1–2 sentences referencing specific cells/metrics
}
```

| Disposition | When |
|---|---|
| `advance` | Addresses ≥ 50% of needs, no `creates_new_problem` verdicts, evidence is non-sparse, owns at least one need |
| `advance_with_followup` | Strong-positive but evidence is sparse OR a logged contradiction warrants probing |
| `iterate` | Owns a need but adoption-fragile, OR mixed verdicts that suggest re-scoping |
| `kill` | Addresses no needs, OR widely creates_new_problem, OR clearly dominated by another concept |
| `park` | `insufficient_evidence` dominant; can't decide yet |

The rationale must reference specific data ("only concept to address fraud", "owns partner-sharing", "3/5 said they wouldn't tag") — not generic ("recommend further testing").

---

## Cross-concept and study-level outputs

These are *single, study-wide* objects that the evaluating skill produces alongside the per-cell `Finding[]`.

### `CrossConceptInsights`

Reads the findings as a portfolio rather than as individuals.

```ts
type CrossConceptInsights = {
  lead_paragraph: string             // overview/cross-tab opener
  coverage_intro?: string            // optional intro for the coverage section
  coverage_by_need: CoverageByNeedItem[]
  drivers_intro?: string
  recurring_drivers: RecurringDriver[]
  drivers_outro?: string
  methodology_intro?: string
  implications_intro?: string
  strategic_implications: StrategicImplication[]
}

type CoverageByNeedItem = {
  need_id: string
  owners: { concept_id: string; verdict: string }[]   // every concept's verdict on this need
  is_single_point: boolean                             // exactly one concept reaches `addresses`
  summary: string                                      // 1-sentence; can include inline HTML
}

type RecurringDriver = {
  label: string                      // 3–7 words, e.g. "Automation / no-effort affordances"
  direction: "up" | "down" | "mixed"
  citations: { concept_id: string; count: number }[]
  note?: string                      // optional inversion / nuance note
}

type StrategicImplication = {
  headline: string                   // bold lead
  body: string                       // 1–2 supporting sentences; can include inline HTML
}
```

`recurring_drivers` aggregates aspects across concepts by **semantic equivalence**, not exact label match. A skill should cluster "automatic categorization" + "real-time delivery" if both are driving ratings via the same underlying property (no-effort affordance).

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
