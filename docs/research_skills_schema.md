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
  high_level_finding?: string                             // 5–15 word punchy fragment for the concept tab
  recommendation?: Recommendation                         // populated by the evaluating skill (Phase 4e)
  disposition?: Disposition                               // DEPRECATED alias of `recommendation` — see below
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

### `ConceptTestingSpec` (top-level v3 shape)

The full spec the `/concept-testing` helper renders to HTML. Combines the plan, the per-cell findings, the cross-cutting insights, and the v3 leadership-brief fields.

```ts
type ConceptTestingSpec = {
  // Project context (v3 — supplied by the researcher in Phase 1)
  project_name: string                           // becomes the masthead h1
  study_name: string                             // longer/internal name
  research_question: string                      // verbatim on Overview
  method_description: string                     // default: concept testing past-use stories + ratings
  usage_guidance: string                         // "How to use these results" — 1–2 sentences
  poc: POC

  // Leadership brief (v3 — Claude-authored in Phase 4f)
  single_sentence_takeaway: string               // one sentence
  top_findings: StructuredInsight[]              // 3–7, prioritized by stakeholder impact
  top_recommendations: StructuredInsight[]       // 3–7, ranked next-actions

  // Synthesis & evidence (existing)
  key_insights: KeyInsights                      // renamed from cross_concept_insights
  study_observations: StudyObservations          // rendered on the Methodology tab
  concepts: Concept[]                            // each carries high_level_finding + recommendation
  findings: Finding[]
  emergent_needs: EmergentNeed[]
}

type POC = {
  name: string
  role: string
  email: string
  links?: { label: string; url: string }[]   // e.g. Slack handle, page
}

type StructuredInsight = {
  insight: string                              // headline statement
  evidence: {
    snippet?: string                           // verbatim quote
    participant_id?: string
    metric?: string                            // e.g. "3/5 said wouldn't tag"
    source_ref?: string                        // anchor or concept_id reference
  }[]
  so_what: string                              // why this matters for business + customer
  now_what: string                             // implication / next action
}
```

The Overview tab renders the brief (project name h1, takeaway, research-question/method/how-to-use strip, top findings, top recommendations, Concept × Need matrix, POC card). The Key Insights tab renders `key_insights` (coverage, drivers, additional). The Methodology tab now also renders `study_observations`. Per-concept tabs render `high_level_finding`, distribution, aspects, per-need findings, this-concept gaps, and any emergent need raised during that concept's session.

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

Each concept gets a Recommendation — the headline output for stakeholders making roadmap decisions.

```ts
type Recommendation = {
  verdict: "advance" | "advance_with_followup" | "iterate" | "kill" | "park"
  label: string                  // human-friendly label e.g. "Advance — with follow-up"
  rationale: string              // 1–2 sentences referencing specific cells/metrics
}
```

| Verdict | When |
|---|---|
| `advance` | Addresses ≥ 50% of needs, no `creates_new_problem` verdicts, evidence is non-sparse, owns at least one need |
| `advance_with_followup` | Strong-positive but evidence is sparse OR a logged contradiction warrants probing |
| `iterate` | Owns a need but adoption-fragile, OR mixed verdicts that suggest re-scoping |
| `kill` | Addresses no needs, OR widely creates_new_problem, OR clearly dominated by another concept |
| `park` | `insufficient_evidence` dominant; can't decide yet |

The rationale must reference specific data ("only concept to address fraud", "owns partner-sharing", "3/5 said they wouldn't tag") — not generic ("recommend further testing").

### `Disposition` *(deprecated — alias for `Recommendation`)*

`Disposition` was the v2 name for this same shape. The field name `concept.disposition` is still accepted by the `concept-testing` helper for one minor-version transition, but new specs should write `concept.recommendation` and refer to the type as `Recommendation`. See "v3 rename" in the helper notes.

---

## Cross-concept and study-level outputs

These are *single, study-wide* objects that the evaluating skill produces alongside the per-cell `Finding[]`.

### `KeyInsights` *(renamed from `CrossConceptInsights` in v3)*

Reads the findings as a portfolio rather than as individuals. Renders on the **Key Insights** tab (panel id `cross` is preserved for back-compat with v2-era links).

```ts
type KeyInsights = {
  lead_paragraph?: string            // optional tab opener
  coverage_intro?: string            // optional intro for the coverage section
  coverage_by_need: CoverageByNeedItem[]
  coverage_so_what?: string          // section-level so-what (one sentence)
  coverage_now_what?: string         // section-level now-what (one sentence)
  drivers_intro?: string
  recurring_drivers: RecurringDriver[]
  drivers_so_what?: string
  drivers_now_what?: string
  additional_insights?: StructuredInsight[]   // 0–4 cross-concept patterns beyond coverage/drivers
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
```

`recurring_drivers` aggregates aspects across concepts by **semantic equivalence**, not exact label match. A skill should cluster "automatic categorization" + "real-time delivery" if both are driving ratings via the same underlying property (no-effort affordance).

The v2-era field `strategic_implications` is no longer part of `KeyInsights`. Strategic takeaways now live in `top_recommendations` at the top-level spec (rendered on Overview), with cross-concept design principles flowing into `additional_insights`. The helper still accepts a `strategic_implications` array for back-compat with v2 specs.

**Methodological observations** (halo, sparse coverage, contradictions) are NOT rendered on this tab — they live in `study_observations` and surface on the Methodology tab.

**Emergent needs** are NOT rendered on this tab — each is rendered on the concept tab where it was raised (matched by `evidence.source_id`/`location` containing the concept ID).

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
