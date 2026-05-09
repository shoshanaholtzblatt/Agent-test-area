# Research Plan — [Study Name]

**Method:** concept_testing

<!--
This template is the input format for /concept-testing.

The research orchestrator (future) emits this file; researchers can also
hand-author it. Headings are parsed by the skill — keep the structure
intact. Add as many ### Need or ### Concept blocks as you have.

Need IDs and Concept IDs are stable strings (e.g. N1, N2, C1, C2 — or
domain-specific like need_supplement_funds_03). They must match the
values used in the ratings CSV.
-->

## Needs

### N1
- **Statement:** [what the user is trying to do or achieve]
- **Source:** odi | knowledge_map | manual
- **Importance:** [number, optional — leave blank if unknown]
- **Current satisfaction:** [number, optional]
- **Evaluation criteria:**
  - [what would "addressing this need" look like in practice?]
  - [add more bullets as needed]

### N2
- **Statement:**
- **Source:**
- **Importance:**
- **Current satisfaction:**
- **Evaluation criteria:**
  -

<!-- Add as many needs as the study covers. -->

---

## Concepts

### C1: [Concept name]
- **Description:** [1–3 sentences explaining the concept as it was shown to participants.]
- **Target needs:**
  - N1 — [hypothesis: why we expect this concept to address N1]
  - N3 — [hypothesis]
- **Assets:**
  - /absolute/path/to/concept_c1.png
  - "Or a text-only description if no image is available."

### C2: [Concept name]
- **Description:**
- **Target needs:**
  -
- **Assets:**
  -

<!--
target_needs is asymmetric on purpose. A concept can address needs it
didn't target (good surprise) or miss needs it did target (designed-vs-
actual gap). The skill surfaces both directions in the findings.

A concept with NO target_needs is valid (purely exploratory).
-->

---

## Participants

- P01
- P02
- P03

<!-- Optional roster. The skill will infer participants from the ratings
CSV if this list is omitted. -->
