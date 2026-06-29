# Human Intelligence System — Working Conversation (Transcript)

_Captured June 28, 2026. This is the conversation between Shoshana and Claude. Deck/HTML file contents are omitted per request; the discussion, questions, and reasoning are preserved. Where a turn was mostly deck-building, the substantive reasoning is kept and the file mechanics are noted in brackets._

---

## 1 — Shoshana

People have been trying to make UX research reusable for a long time. They looked for ways to atomatize insights. They built different systems to enable this. What has worked and what has not worked to date? What about today's technology including LLMs makes it different now? What is still going to be a challenge?

**Claude:**

The dream has always been the same: turn expensive, one-off studies into a durable, searchable knowledge asset so the org stops re-learning the same things.

**What people tried.** Research repositories (SharePoint folders → Confluence/Notion wikis → purpose-built tools like Dovetail, EnjoyHQ, Aurelius, Condens). Atomic research (Daniel Pidcock's "Atomic UX Research," ~2018): break findings into a chain — Experiment → Fact → Insight → Conclusion — so a single observation becomes a reusable nugget. Taxonomies and tagging to make nuggets findable. ResearchOps as the organizational layer.

**What actually worked.** Centralization beats scattered decks. Tagging plus good metadata prevented some duplicate studies. ResearchOps professionalized the back office. The atomic *concept* was intellectually correct: insights are more valuable decomposed and recombinable than locked in narrative reports.

**What didn't work.** Most insight repositories became write-only graveyards. The failure modes: the tax of atomization fell on the researcher (manual, tedious, done after the real work, skipped under deadline); taxonomies rot; garbage retrieval (keyword/tag search couldn't match the PM's question to the researcher's old language); no demand-side pull (PMs/designers rarely searched before starting); atomization stripped nuance (decontextualized nuggets get misused). Net: the supply side was expensive and the demand side never showed up. The systems optimized for storage, not reuse.

**Why LLMs change the calculus.** (1) Atomization stops being manual — LLMs transcribe, segment, tag, extract candidate insights automatically. (2) Retrieval moves from keywords to meaning — semantic/vector search and RAG. (3) Synthesis on demand — ask the corpus, get a synthesized cited answer across many studies. (4) Lower activation energy for non-researchers via chat.

**What's still hard.** Garbage in, confident garbage out (fluency makes bad evidence more dangerous). Context and validity don't survive atomization well (when, which segment, what product version, what sample size/method). Hallucinated or mis-attributed insights. Recency and decay. Trust and adoption. Judgment isn't retrievable (knowing which question to ask, spotting that users say X but do Y). Privacy/consent and PII at scale.

The honest framing: LLMs convincingly solve the *mechanical* bottlenecks (capture, structuring, retrieval) that killed previous systems. They do *not* solve the *epistemic* ones (validity, context, judgment, trust) — and those arguably get riskier because fluent synthesis hides weak evidence.

---

## 2 — Shoshana

The team is going to be building several parts to this human intelligence system. The first are core Jobs-to-be-done. We have already seen this research be reusable in this format. We are going to store all of the jobs-to-be-done for both external and internal products in a data lake for people to access and use. We also want to think about how to make insights reusable. And we will be exploring good use cases for synthetic users. We have Claude code internally but it does not have web access and it cannot connect to Google drive. We will have the ability to create an internal MCP and could use that to read from the lake. But we'd like to understand different options including pros and cons of rag vs a knowledge graph vs rag-graph. We'd like to understand if there is anything else we should be considering that would make Claude be able to look across multiple data sources more easily and deliver coherent considerations and summaries. What are the things that are going to continue to get in our way? What can we do to mitigate them? We have been developing Claude skills for better note extraction from transcripts and the skill does a good job of carrying forward the quote, the source line reference and the context from the interview. Will skills help us do the same when we are talking about data that is not stored locally? Lastly we should also be considering what parts make sense to build vs buy. We have already run into issues with considering synthetic users externally because there is hesitation with giving external vendors all the data about our customers in their external system.

**Claude:**

Through-line up front: **the internal MCP + a provenance-rich lake is the single foundation that powers retrieval, your skills, and internal synthetic users — and it's also what resolves your vendor-privacy problem.**

**JTBD and insights are different data — don't force one architecture on both.** JTBD are structured, few, stable, proven reusable. Insights are many, messy, contextual, decaying. Pick per-asset.

**RAG vs knowledge graph vs graph-RAG.** RAG (semantic/vector): cheap, scales with unstructured text, great for "find me relevant evidence"; weak at relationships, multi-hop, aggregation, and global synthesis. Best for insights/transcripts. Knowledge graph: explicit entities + edges; excellent at traversal, multi-hop, governance, provenance; cost is the schema (it rots like research taxonomies). Best for JTBD (already structured, small). Graph-RAG (Microsoft GraphRAG pattern): LLM extracts a graph + community summaries, combined with vector retrieval; answers global synthesis questions plain RAG fails at; more pipeline, compute, maintenance. Recommendation: strong RAG + rich metadata for insights; a light knowledge graph (or relational + semantic) for JTBD; add graph edges where multi-hop arises; defer full graph-RAG until proven demand.

**What else matters for cross-source coherence.** A metadata/provenance layer (stable IDs, source, verbatim quote, line/timestamp, product, segment, method, sample size, date, confidence/recency). Entity resolution across sources (the quiet killer). Query routing/orchestration via MCP. An eval set (golden questions).

**Will skills carry provenance for non-local data? Yes — conditionally.** The skill encodes a procedure; it works over the lake *if and only if the MCP returns those fields*. MCP/retrieval fetches with fidelity; the skill enforces consistent carry-forward. Failure mode: a lake that stores "insight text only."

**Continuing challenges + mitigations.** Provenance loss/decontextualization; schema/taxonomy maintenance; recency/decay; confident synthesis over thin samples; entity resolution; access control; evaluation; adoption. Mitigations in priority order: enforce provenance at ingestion; build entity resolution/shared vocabulary; surface recency + confidence; stand up an eval set; instrument usage.

**Build vs buy.** Build the MCP over your lake, the JTBD schema/provenance model, your skills, internal synthetic users (your IP, keep data internal). Buy commodity infra: vector DB, embeddings, graph DB, transcription, ingestion. Rule: anything that only works by shipping all your customer data into an external system is a "build internally or run-in-your-boundary" candidate.

**Synthetic users.** Good: formative/divergent — pretesting guides/surveys, generating hypotheses, stress-testing personas, broadening coverage. Risky: summative/validation, "users want X." Privacy connection: they're far more useful grounded in your JTBD + insights — which is exactly why you don't want them in a vendor's system. Build them internally on your own lake + Claude.

---

## 3 — Shoshana

is all of this overkill for insights reusability? Today we do create meta-synthesis or research POV decks that are very valuable to partners. We pull together all of the sources, understand the business context and create a specialized deck with our understanding of what each part tells us and informs today's decision making. Will any of these systems be able to do that easily? Or is there so much judgement in that curation and storytelling that it will still be needed? Be totally honest -- don't just say what you think I want to hear.

**Claude:**

Honest answer: for the meta-synthesis POV deck specifically, yes — a lot of the heavy architecture is overkill, and the curation/storytelling judgment will still be needed.

Decompose the POV deck: **Gathering and recall** — where the architecture earns its keep; RAG + provenance reduces "did we miss something." **Understanding the business context and the decision** — mostly you; the system doesn't know which exec is skeptical or what got killed last quarter. **Weighing evidence, not counting it** — assistable, but the weighting is judgment (a model treats 5 users and a 2,000-person survey as equally quotable). **Choosing the throughline / the POV** — the irreducible core; an argument about what the evidence means for this decision now. **Deciding what to leave out** — judgment; models are bad at it. **Drafting and production** — assistable, real time savings.

Two cautions: the act of doing the synthesis is how you build the conviction to defend it in the room; a fluent deck nobody can stand behind is a trap. And as models improve, the binding constraint shifts to "who provides the business context" and "who's accountable for the call" — which stays human.

Practically, this should right-size your ambition: a strong RAG layer with excellent provenance is probably plenty, and the meta-synthesis stays human-led with AI assist. Save the graph/graph-RAG for proven demand for global cross-corpus questions your researchers can't already answer by hand — not as a bet that the system will produce the POV decks. It won't.

---

## 4 — Shoshana

_[Uploaded five .docx files of a parallel conversation with Gemini.]_ I had a similar conversation with Gemini. Does Gemini's synthesis add anything to this discussion?

**Claude:**

Yes — it adds real things. **Genuinely worth taking:** programmatic gap analysis (use graph structure to surface what you haven't researched and auto-draft study briefs) — with the caveat that graph density measures *documentation*, not knowledge or importance. A pre-aggregated summary layer (hierarchical indexing). A metadata header injected into every chunk (contextual retrieval). Entity resolution with a concrete mechanism. Your note-extraction skill as an ingestion gatekeeper. The skill-provenance mechanism for remote data (MCP wraps text in block IDs the skill retains). Plus challenge categories I didn't raise: unknown unknowns, multimodal loss, outlier smoothing, low UX maturity.

**Where I'd push back:** Gemini contradicts itself — one doc prescribes full GraphRAG (Neo4j, Leiden clustering), another says it's overkill. It oversells automated gap analysis. It waves at the internal-vs-external data problem with a single metadata flag (access control is harder than tagging).

**Reassuring:** on the conclusions that matter most we converged independently — atomic research's failure modes, semantic search removing the tagging tax, recency/decay, build the MCP and synthetic users internally over bought infra, synthetic users as sandbox not source, and that the POV deck stays human ("the plumbing doesn't cook the meal; your partners are paying for the chef"). Net: borrow its mechanisms; keep my sequencing.

---

## 5 — Shoshana

So is GraphRag worth the effort or you are saying we should start with RAG and build our usecases out further to see if GraphRag is worth it

**Claude:**

Start with RAG. Build strong RAG with rich provenance first, expand your use cases, and let real demand tell you whether GraphRAG earns its keep. RAG already serves insight reuse, quote-fetching, micro lookups, your skills, and grounding internal synthetic users. GraphRAG's distinctive value is narrow (global multi-hop synthesis, whole-corpus themes, gap analysis) and its costs are ongoing (extraction QA, entity resolution, schema upkeep, reindexing, token overhead) — the taxonomy tax in a new outfit.

But build RAG **graph-ready**: a strict consistent metadata envelope, stable canonical IDs, provenance/chunk IDs preserved through retrieval, and a clean canonical JTBD schema. Then the graph layer is mostly drawing edges between nodes you already identified.

Refinement: your JTBD are proto-graph nodes, so if anything justifies a light relationship layer early, it's the JTBD (relational + semantic), not the messy insight corpus. Trip-wires to add the graph: researchers repeatedly answering multi-hop/whole-corpus questions by hand and it hurts; real demand for cross-product job-overlap maps or gap analysis; insight volume large enough that top-k retrieval visibly misses global patterns.

---

## 6 — Shoshana

And this is what Gemini said to the same question: _[pasted Gemini's "No, for 80% of companies a full-scale GraphRAG is not worth it" answer — cost shape (ingestion token burn, query latency, maintenance), when it's worth it (macro synthesis), and a pragmatic path: Adaptive RAG gateway classifier, leaner fine-tuned extraction models, lazy incremental graphs]._

**Claude:**

This is Gemini's strongest answer yet, and we substantially agree — it's landed where the lean recommendation was all along (worth noting, since its earlier docs prescribed the full blueprint).

Three things worth taking: the cost-shape breakdown (ingestion burn / latency / maintenance); the adaptive RAG / gateway classifier (cheap intent classification routes lookups to vector RAG, escalates to graph only for cross-cutting questions); lazy/incremental graph building (grow the graph as your skill processes each transcript).

Two cautions: the specific numbers and the "Sci-Fi Triplex" tool name are false precision — verify before relying (the real model is SciPhi's Triplex; a mangled name is a tell of pattern-matched recall). And the "use a separate small extraction model" advice may be premature for you — you already have a working Claude extraction skill; don't add a second model to save tokens you aren't yet spending. It also oversells "standard RAG fails entirely" on macro queries — long-context models, reranking, and the hierarchical-summary middle path handle a lot without a full graph. Ladder: vector RAG → add hierarchical summaries → add a light JTBD graph → full GraphRAG only if demand proves it.

---

## 7 — Shoshana

Ok but haven't we had RAG for a long time. Why build this now? What is different about now?

**Claude:**

RAG — the retrieval part — was never the bottleneck, so its age isn't the point. The things that blocked research reuse were elsewhere, and several moved at once in roughly the last 18 months.

The old systems failed because (1) a human had to do the structuring/tagging, (2) the synthesized output wasn't trustworthy enough to act on, and (3) wiring a model to your data was expensive bespoke engineering. All three just changed:

- **Synthesis quality crossed the "trustworthy enough to act on" line.** Earlier RAG retrieved fine but the generation mangled/hallucinated the summary. Reliable synthesis is recent.
- **The model can now do the structuring labor humans abandoned.** Your note-extraction skill reliably carrying quote + source line + context is the proof point.
- **MCP standardized the integration that used to kill these projects** (didn't exist until late 2024).
- Retrieval got better underneath (embeddings, agentic multi-step retrieval).
- Cost dropped to where cross-corpus synthesis is routine.

The one that matters most for you: good-enough internal models + MCP means trustworthy synthesis without customer data leaving your boundary — the trade-off that previously forced a choice. That's also why internal synthetic users are suddenly viable. Building now isn't chasing hype; the prerequisites weren't in place 24 months ago.

---

## 8 — Shoshana

One thing I am still confused about. I thought I had read that graphs were good at handling unstructured data. But now you are saying that is not true. Why did I think that?

**Claude:**

"Graphs handle unstructured data" is true in a different sense than the one in play, and GraphRAG marketing blurs it.

**Graph databases vs relational databases:** here it means *schema-flexible* — you can add node/edge types as you go, handling irregular, evolving data better than rigid SQL. Real, and probably what you read. But "flexible schema" is not "raw unstructured text"; it's *semi-structured*. The data still has to be entities and relationships.

**Knowledge graphs as a representation:** by definition structure — entities + typed relationships. Good at relationships, not at raw qualitative text. Something first has to read the rambling answer and decide "this is a Pain_Point node." That extraction step flattens nuance. The graph stores the result; it doesn't process the messiness.

The thing that genuinely "handles unstructured data" is the **LLM plus vector search**, not the graph. That's the sleight of hand in GraphRAG marketing: the LLM reads and extracts, vector search retrieves the narrative, and the graph stores the relationships — the graph gets credit for the other two's work. Which is why both Gemini and I said GraphRAG keeps links back to source chunks: graph holds relationships, you go back to raw text for nuance.

---

## 9 — Shoshana

_[Long message]_ I need help structuring a deck for a workshop this week. The goal ... clarify the vision for a human intelligence system ... what success will look like 1 year from now ... business success metrics ... milestones ... skills and resourcing ... Getting really crisp on the exact use cases is really important ... We are going to use the PDLC as a framing ... I have 30-45 mins. Some of this can be discussion. Give me some outline options. What do you think is important to include?

**Claude:** _[Gave a POV that the opener's #1 job is to make the afternoon ideation productive by teaching what a well-specified use case looks like and why. Offered three outline options — A: Past→Present→Prize→Practice; B: use-case lens first (recommended); C: outcomes-first. Recommended B with a compact history slide. Proposed the use-case "anatomy" (9 dimensions) as the teaching core and afternoon worksheet, the fetch→synthesize→judge ladder, a 1-year success strawman, and what to cut. Then asked, via the question tool, which outline and the audience.]_

---

## 10 — Shoshana _(answering the outline question with more context)_

This is really interesting. I need to give you some additional context. We need to be thinking about the whole intelligence system. Not just the insights part. But also the JTBD part and the synthetic users. A couple questions for later in the day -- is it worth brainstorming about use cases for each separately? How should I address the core differences in this talk early on. I also have to deal with partners who want to dig into talking about inputs and data structures. When our goal needs to be getting crisp on the use cases. Right? Or am I thinking about this wrong? I'm also wondering what is worth discussing now vs later in terms of alt options for the insights hub -- specifically what NotebookLM provides and where it falls short.

**Claude:** _[Searched the web for current NotebookLM capabilities.]_

**The three parts aren't peers — they're layered.** JTBD + insights are the knowledge *substrate*; synthetic users are an *application* on top. JTBD: structured/proven/stable. Insights: unstructured/contextual/decaying. Synthetic users: generative/experimental, only good when grounded in the other two. Set this up early or the room applies one mental model to all three.

**Brainstorm each separately? Mostly no.** Keep PDLC as the single generative axis and tag each use case with the component(s) it draws on — surfaces which component matters where, exposes cross-cutting combinations, avoids redundancy. Carve out a short dedicated synthetic-users prompt since it's least familiar.

**Partners wanting data structures: you're right, with a refinement.** Use cases first is correct (the use case determines the data structure; designing structures first is how these systems died). Don't shut them down — sequence them: the use-case anatomy includes a "data sources & fidelity" dimension, give them a parking lot, name the failure mode out loud. The one legitimate version of their instinct: if a data source doesn't exist or governance forbids it, that kills use cases — so add a late-day feasibility check on prioritized use cases.

**NotebookLM: mention briefly now, deep-eval later.** What it provides: bounded-notebook grounded Q&A with citations, summaries, audio overviews; Enterprise governance (no training on your data, VPC-SC, CMEK, US/EU residency, IAM, audit logs); Pro up to 300 sources/notebook, 500 notebooks/user. Where it falls short for an org-wide system: bounded notebook not a living lake; no cross-notebook synthesis or JTBD graph; citations lack exact line refs; not extensible (no custom skills/MCP/synthetic users); even Enterprise is Google Cloud (outside your boundary). It's a great benchmark and a possible fast pilot for narrow tactical lookup on non-sensitive data — not the integrated system. Which reinforces the thesis: whether it suffices depends on which use cases you prioritize and their data sensitivity.

The opener (still Option B) gains one slide — the three-part layered system — after the vision, before the use-case lens.

---

## 11 — Shoshana

Let's build out the outline for option B -- show me what you are thinking for each of the slides

**Claude:** _[Gave the full slide-by-slide build-out, assuming a mixed/cross-functional room, ~44 minutes: 1 prize, 2 the two-use-case hook, 3 thesis + 9-dimension lens, 4 why-it-failed/why-now, 5 the ladder, 6 three layers, 7 synthetic users, 8 1-year strawman + metrics, 9 how-we-work-today + parking lot, plus appendix. Flagged that slide 6's dimensions should match the afternoon worksheet and that slide 8's metrics were guesses.]_

---

## 12 — Shoshana

Is synthetic users really just a part of a use case rather than a part of the system? I'm also not sure it is obvious the need to get the use cases right without the example. I'm not sure about this order...

**Claude:**

Both instincts are right. **On synthetic users — a category error in my framing.** JTBD and insights are knowledge *assets*; synthetic users is a *capability you build on top of* them — closer to an application (a class of use cases) than a structural part. The cleaner model is three *layers*: Assets (JTBD + insights) → Access (MCP + retrieval + skills) → Applications (tactical lookup, cross-corpus synthesis, POV-deck assist, gap analysis, *and* synthetic users). It feels like a pillar because it's strategically prominent; structurally it's an application that might be *built using* skill machinery.

**On the order — you're right, and it's the more important fix.** Asserting the thesis before the audience has felt the problem inverts it. Go inductive: show the two-use-case example first, let them feel that two things both called "reuse research" need different machinery and cost, and let the thesis fall out. Reordered flow: prize → the hook (two use cases) → so here's the thesis + lens → why it failed before / why now → approaches & cost ladder → the system (three layers, synthetic users as flagship application) → 1-year success → how we work today. Energy on use cases first; history becomes the answer to "why are we only doing this now?"

---

## 13 — Shoshana

Given that is a synthetic user really different from a claude skill that tells you how to do analysis?

**Claude:**

Mechanically they're cousins — both are Claude + an instruction-and-context package, grounded in data; you could even implement a synthetic user *as* a skill. The difference is the *role in research*: a skill is the **researcher's method**; a synthetic user is a **simulated subject**.

An analysis skill consumes real evidence and produces a grounded, auditable artifact (your note-extraction skill carries a real human's quote, source line, context). A synthetic user doesn't analyze evidence; it *manufactures* it — a model's guess with no real person behind it. The decisive distinction is the **truth status of the output**: a skill *organizes* real evidence; a synthetic user *invents* plausible evidence. That cascades into auditability, failure mode (confident fabrication, self-confirming if grounded on your own priors), and evidentiary weight (never use a synthetic user for validation).

This sharpens the layered model: the skill lives in Access (method); the synthetic user lives in Applications (a thing you produce). Same building blocks, opposite jobs. Worth one explicit beat on the synthetic-users slide, because it's the only thing in the system that manufactures data instead of organizing it — that's why it carries different risk.

---

## 14 — Shoshana

ok how should we build this into the presentation

**Claude:** _[Proposed splitting the system content into two slides — slide 6 the three-layer model, slide 7 a dedicated synthetic-users slide where the skill-vs-synthetic-user contrast lives (side-by-side "organizes REAL evidence" vs "manufactures SIMULATED evidence," caption "same building blocks, opposite jobs," plus a "so what" row: only part that creates data → different risk/governance → pre-work never validation → build internally). Kept the fuller spectrum nuance as a speaker note. Confirmed the final 9-slide flow.]_

---

## 15 — Shoshana

it is also worth calling out that synthetic users will also likely consume other data in the data lake including other external data sets we will want to pipe in to improve accuracy.

**Claude:**

Good catch — strengthens both slides and the build-internal argument. On slide 6, broaden Assets so it's not just JTBD and insights: include external datasets piped in. On slide 7, add a beat: synthetic users consume *across* the lake (JTBD, insights, external datasets) to improve fidelity — which sharpens the build-internal point, because combining your customer data with licensed external data to ground a persona makes shipping it to a vendor a real licensing-and-governance problem.

Guardrail to keep as a speaker note: more grounding data raises *fidelity*, not *truth* — so "pre-work, never validation" matters *more* as personas get more convincing. And external-data ingestion is its own workstream (licensing, freshness, provenance) — a parking-lot item.

---

## 16 — Shoshana

yes build the deck

**Claude:** _[Built the 9-slide opener as a .pptx with python-pptx (npm registry was blocked), navy/teal/amber palette, speaker notes on every slide; QA'd by rendering to images and fixing two defects — the "Fetch" ladder card overflow and dropped chips on the three-layers slide. Saved to the workspace.]_

---

## 17 — Shoshana

Do you have speaker notes for each slide?

**Claude:** _[Confirmed yes and listed the notes for all 11 slides — cues, not a script — including the "more grounding raises fidelity, not truth" caveat on synthetic users and the "we're not choosing architecture today" reminder on the ladder.]_

---

## 18 — Shoshana

I don't understand slide 3 tell me more about it

**Claude:**

Slide 3 is the heart of the deck. It states the thesis (the use case decides which approach fits and what it costs) and gives the tool that makes it actionable: the 3×3 grid is the **anatomy of a crisp use case** — nine attributes that are *diagnostic*, each pointing at an approach and a cost. Walked each dimension and the decision it drives, explained it doubles as the afternoon capture template, and showed it working on the two slide-2 examples (tactical lookup → cheap retrieval, worth automating; POV deck → human-led, AI assists, not automatable). Same nine questions, opposite conclusions.

---

## 19 — Shoshana

Can you make this into an HTML deck with all of the speaker notes so I can send it to myself at work more easily

**Claude:** _[Built a self-contained HTML version of the opener — one file, all slides, speaker notes shown beneath each, keyboard navigation, notes toggle, print-to-PDF support. Saved to the workspace alongside the .pptx.]_

---

## 20 — Shoshana

I'd like to build out a few slide like that NotebookLM slide but don't label it appendix. I am going to show these later in the day. We have some other options (all likely short term). We are getting approval to store the JTBD data in github and will have a github MCP connected to claude code and any skills we make. How does this set up compare to storing JTBD data in the data lake? We also have another MCP that can query quant data in the data lake today that can be queried in plain language with our claude code. Why is storing in the lake better or worse than Github? We also have another option for insights. We have access to Glean and it can connect to our Google Drive. We can build an MCP to connect to Glean. Glean uses Rag. How does that compare to other options. Build out those slides.

**Claude:**

**JTBD → GitHub vs lake.** GitHub is the better *short-term* home for JTBD: small, structured, curated, version-sensitive; git gives history, diffs, PR review as a quality gate; already approved. The lake wins only when you need JTBD queried alongside quant and insights or at semantic scale. Not either/or — GitHub as system-of-record now, mirror to the lake when cross-source querying is the need.

**Quant → lake.** A database job (aggregation, joins, scale, refresh) GitHub can't do, and the plain-language MCP already works today. The principle: the data's *shape* picks the store.

**Insights → Glean.** Fastest path to org-wide lookup over research already in Drive, permissions-aware. But RAG with a black-box ceiling — can't run your extraction skill, can't control chunking, doc-level citations. Great for tactical lookup now; doesn't replace a purpose-built pipeline for high-fidelity synthesis.

_[Built a separate four-slide HTML options deck: JTBD GitHub-vs-lake; quant/data-home; Glean vs alternatives; a short-term map. No "appendix" label.]_

---

## 21 — Shoshana

Are you saying that claude code cannot query JTBD data in github and cross reference that with quant data in the lake? It would have to all be in the lake? Is it about being in the lake or is it about having something else in the lake too?

**Claude:**

You caught a real overstatement. Yes — Claude Code can query JTBD in GitHub and quant in the lake and cross-reference them via both MCPs, without everything in the lake. My slide implied co-location was required; too strong.

It's not fundamentally about being in the lake. It's about two things co-location gives you for free: (1) **shared keys / entity resolution** (common IDs; if GitHub says "Enterprise Admin" and the lake says "ent_admin_v2," Claude has to bridge that — a vocabulary problem, not a location one), and (2) **an engine for heavy joins and somewhere to persist the relationships** (federation works when each source returns a small filtered slice; it breaks only when the join itself is big). And the *somewhere* doesn't have to be the JTBD data — you can keep JTBD's source-of-truth in GitHub and put only the connective tissue (canonical IDs, mappings, embeddings, graph edges) in the lake.

---

## 22 — Shoshana

ok that may be true for only quant JTBD data that consists of the job, the outcome statement, the components of the opportunity score. But what if I told you that I want to be able to also store short transcript snippets that show what meeting or not meeting that outcome statement looks and sounds like. This is something that I would like to be able to reference and use in our concept testing skill. Would that change anything? I'm also still not fully understanding the value of a graph for JTBD data -- would you need the data to live in the lake for creating a graph? Lastly I am wondering if we are doing our research and analysis with Claude skills and there is a github MCP that makes it easy to write to Github, but governance does not want to allow Claude to write to the lake. Is that another consideration?

**Claude:**

**Transcript snippets — mostly no change, with one fork.** If they're *curated exemplars* (a few per outcome, with quote + source + context), git handles them fine and the concept-testing skill reaches them by key — no semantic search needed. Git's versioning is an asset (every exemplar is reviewable). The fork: if you later want to search across *all* snippets semantically, that's a vector index (RAG layer), a different job. Curated exemplars in GitHub; full evidence corpus in the RAG layer.

**Graph value for JTBD — and it doesn't need the lake.** A graph is about *relationships* (job hierarchies, jobs↔outcomes↔opportunity scores, jobs↔products, outcomes↔exemplars↔studies, and cross-layer jobs↔insights↔quant). For JTBD alone, much is doable relationally. A graph is a structure, not a location: it needs stable node IDs and somewhere for edges — a relationships file in GitHub, a graph DB whose nodes point at GitHub records, or the lake. Promote to a graph DB when traversal and cross-layer scale justify it.

**Write-governance — yes, decisive.** If Claude skills produce JTBD and must write somewhere, and governance allows GitHub writes (via reviewed PRs) but not lake writes, GitHub is the natural write path — and it's *better governance*: Claude proposes, a human reviews and merges. Architecture: write path = Claude → GitHub (reviewed); read path = Claude reads GitHub and federates with the lake's quant MCP; any GitHub→lake movement via a separate governed pipeline. The deciding factors are access pattern, where relationships are persisted, and the write/governance path — none of which is "must sit in the lake."

---

## 23 — Shoshana

one bit of clarification -- jobs are not shared across internal and external personas. The jobs are totally different. Think jobs about allocating funds across priorities for personal finance and jobs about promoting the feature you just built.

**Claude:**

Important correction — it kills my "shared jobs across internal/external" example. If external jobs are "allocate funds across competing priorities" and internal jobs are "promote the feature I just shipped," there's no job-to-job overlap to traverse. Two different domains, not one taxonomy.

What still holds is **within-domain, cross-layer** linking (external JTBD ↔ external quant ↔ external insights). The graph's value for JTBD is relationships *inside* a domain, not bridging the two. And it simplifies the architecture: internal and external look like two separate domains — different jobs, different sensitivity, probably different governance — arguing for two distinct namespaces (plausibly two GitHub repos) that share *schema and skills* but not *data*. It weakens "unify everything" at the JTBD-to-JTBD level, leaves the within-domain story and the GitHub-as-home conclusion intact.

---

## 24 — Shoshana

now there could be jobs for personal and jobs for business that it might be useful to analyze across

**Claude:**

Right — and that one is real, because personal and business are both customer domains, so the same or analogous job can exist across them (e.g., "allocate funds across competing priorities" for a personal user and a business user). Analyzing across them is valuable (is the job underserved for business but well-served for personal?). This revives the graph/relationship value — correctly scoped to within the customer domain.

What makes it possible is a **modeling decision**, not storage: a shared, aligned job taxonomy across personal and business. Decide deliberately whether the two versions are *the same job* (one canonical node, outcomes/opportunity scores tagged by segment) or *analogous jobs* (two nodes linked). This is where a graph (or relational model with a job dimension + segment attribute) earns its keep for JTBD. It still doesn't require the lake — canonical IDs and links are small curated metadata that live fine in the GitHub taxonomy.

---

## 25 — Shoshana

right now they do not follow the same taxonomy -- that would need to be a separate effort to align them. Worth calling out though.

**Claude:**

Exactly — the cleanest illustration of the theme: even if every byte were in one place, you couldn't analyze across personal and business today, because the blocker isn't storage, it's that the taxonomies aren't aligned. Co-locating wouldn't buy the comparison; the alignment work would (the entity-resolution problem made concrete).

Framing for the room: cross-segment analysis is a desirable future capability gated on a separate taxonomy-alignment effort — not a near-term win, not delivered by the architecture. Three notes: it's a dependency (don't inflate the short-term promise); it's high-judgment work, not a technical migration, so it should be demand-driven; and it reinforces the storage conclusion (the output is a shared vocabulary + links — small metadata that sits fine in GitHub). I'd capture it as a named dependency on the short-term map.

---

## 26 — Shoshana

yes -- ok update the slides

**Claude:** _[Updated the options deck: fixed the over-claim that JTBD must go to the lake for cross-source work (federation works today; lake is for "links, not the data" on heavy joins); added GitHub's write-governance edge and the lake's write restriction; added the taxonomy-alignment dependency callout; updated speaker notes.]_

---

## 27 — Shoshana

A couple of things -- the only quant data that we are making a decision about is survey data. Does that belong in the lake vs github. It is not going to need version control. While it will not be as large as other analytics in the lake. It could be useful to look at survey data across many surveys and generate synthesis or summaries. Does this adjust that slide? Also I feel like the insights glean slide is combining too many things. I still want a NotebookLM slide. Then I want a Glean vs build your own RAG system I think. Then I think it is worth having in my back pocket a RAG vs GraphRAG for insights. After chatting today I don't think it makes sense to even talk about vanilla graph for insights or unstructured qual data.

**Claude:**

**Survey data → still the lake**, but for a different reason than scale. The value is synthesizing across many surveys (aggregation/grouping = a query-engine job), the plain-language MCP already does it, and you explicitly don't need version control — so GitHub's one real edge doesn't apply. Smaller size is fine. Caveat (in notes): open-ended free-text responses needing semantic search lean toward the insights RAG layer, not a survey table.

**Insights split into three slides:** NotebookLM (standalone), Glean vs build-your-own RAG, and a back-pocket RAG vs GraphRAG — framed as RAG-vs-GraphRAG only, with an explicit line that vanilla graph is the wrong tool for unstructured qual.

_[Rebuilt the options deck as six slides: JTBD GitHub-vs-lake; survey data; NotebookLM; Glean vs build-your-own RAG; the short-term map; and the back-pocket RAG-vs-GraphRAG last so it's only reached if the room goes deep.]_

---

## 28 — Shoshana

one question on the JTBD storage slide -- are you saying you can't store curated exemplars in the lake or are you just calling out that the currated exemplars can be read by the key of the outcome statement. I guess I am just wondering if there is a counter point for the data lake. If not I am wondering if it is a strength.

**Claude:**

You caught a real imprecision. The lake *can* store curated exemplars — storing them isn't GitHub-only, and either store can be read by key. So "holds curated exemplars" was sloppy as a GitHub strength.

The genuine GitHub edge isn't *storing* the exemplars, it's *curating* them: in GitHub each is versioned and added through a reviewed PR — exactly what you want for a vetted "what good looks like" reference — and Claude can write them there under review, which it can't in the lake. And there's a counterpoint for the lake: if exemplars grow from a small curated set you fetch by key into a corpus you want to *fuzzy-search*, the lake's semantic retrieval beats read-by-key. So: storage is neutral; GitHub wins on versioned, reviewed curation; the lake wins if/when you need semantic search across exemplars.

_[Fixed the slide bullet to say exemplars are "versioned & PR-reviewed" rather than implying GitHub uniquely holds them, and added the nuance to the speaker note.]_

---

## 29 — Shoshana

I'd like to talk timing of these slides -- is this best after we do the use case ideation or is it better at the start of the day?

**Claude:**

After ideation — specifically after you've *prioritized* the use cases, as the bridge into milestones. It's consistent with your thesis (the use case decides the approach); showing GitHub-vs-lake and Glean-vs-build at the start inverts your own message. It protects against the partner-derail (front-loading architecture legitimizes diving into data structures before use cases are crisp). Decisions are better anchored to concrete prioritized use cases. And the deck ends on a short-term map + dependency — a natural lead-in to milestones. You lose nothing by waiting, because the conceptual grounding people need to ideate is already in the opener (the ladder and three-layer model). One concession: a single early sentence — "we have real near-term options; we'll dig in after we've prioritized" — reassures the toolbox exists without anchoring.

---

## 30 — Shoshana

I like that idea as the on ramp to milestones. I am also thinking another conversation I had planned for the morning should also go to the end -- it is more data / architecture. Ok can we revisit the first deck now.

**Claude:**

Moving the data/architecture conversation to the end is the same logic as the options deck — both are solution-and-detail that should follow the use cases. The day reshapes into diverge-then-converge: morning = opener + ideation + prioritization; afternoon = options (on-ramp) → data/architecture → milestones + resourcing.

That mostly hits the opener in three places: the "How we'll work today" slide should show the two-part arc (so the moved conversations have a scheduled home); the NotebookLM appendix is now covered by the options deck (drop it); and the conceptual architecture slides (ladder + three layers) are the open question. _[Asked, via the question tool, what to do with the ladder + three-layer slides, and how deep a pass to take. Answers: keep them in the morning; do a full content review.]_

---

## 31 — Shoshana _(after the review)_

I have some other changes I'd like to consider. I feel like the use cases are not hitting the mark ... we need to make it easier to understand why it is so important to understand the use cases and how that maps directly to the best architecture decisions. I also feel like the 9 dimensions feels like a lot. Is there any way to slim that down ... I am also feeling like I am not sure the story is the right order. Can you consider these changes and consider an alt start. _[Proposed a new opening: the research MVP's vision diagram (even though it's wrong/confusing); two research programs that reliably built knowledge — JTBD dashboard and critical task analysis dashboard — that reduced bespoke/duplicative research; but reusable insights remain elusive; AI/Claude changing how we work; understand use cases to decide storage/access; envision 1 year to build the roadmap.]_ I'm still torn on going into why insights reuse failed ... later and starting with the use cases. Build out some outline options for me to consider and weigh against the already built approach.

**Claude:**

Your proposed opening is stronger because it grounds the day in real history. Fixes:

- **Use-case → architecture mapping:** reframe the hook from "two use cases, different cost" to a worked table — use case → kind of question → where it lives/how reached (lookup → Glean now; cross-survey synthesis → the lake; judgment call → human-led, AI assists). That slide *is* the argument for why use cases matter.
- **Slim the lens** to a use-case card. (After your feedback this became: Consumer & decision; Example questions [the anchor]; Output; Data: sources, sensitivity & fidelity; Impact — with question type and judgment *read off* the example questions and PDLC stage captured by where the use case came up.)
- **Structural bonus:** her messy diagram creates the need; the three-layer model later becomes the "cleared-up" version of it.

Three orders to weigh — A: justify late (why-now as justification before the roadmap, recommended); B: why-now up front (right after naming the gap); C: lean (history as one beat). _[Asked which order and whether to slim the lens.]_

---

## 32 — Shoshana _(answering)_

Can you build A and B. _[On the lens:]_ Those 4 are really hard to understand. I like Consumer & decision ... I also had output before ... maybe it is better to capture example questions instead of asking people to say if it is lookup or synthesis ... we can also then look at the example questions and apply ... judgement ... I had one other ... when in the PDLC does it show up -- but maybe your value or impact is better ... I'm not sure we are going to be good at estimating frequency or volume, impact is likely better ... data and sensitivity and provenance and fidelity can probably come together as a category maybe -- what do you think?

**Claude:** _[Adopted the revised 5-field use-case card (Consumer & decision; Example questions as the anchor; Output; Data: sources/sensitivity/fidelity combined; Impact), with question type and judgment read off the examples and PDLC captured by the ideation structure. Built the reworked opener as a single HTML file with an A/B toggle (the two orders differ only in where the why-now slide sits): new grounded narrative (title → her messy diagram → two proven programs → gap + the Claude moment), the mapping payoff slide absorbing the ladder, the slim card, the three-layer model as the cleared-up diagram, synthetic users, why-now, 1-year/roadmap, diverge/converge agenda, glossary. Noted the diagram is a placeholder to swap for the real one.]_

---

## 33 — Shoshana

B is definitely the right order. Now we can work on getting the exact content correct.

**Claude:** _[Locked Order B and removed the A/B toggle, leaving a clean 13-slide narrative. Flagged the slides where real input is needed — her actual diagram, the two proven programs' real details and impact, the mapping examples, and the 1-year enablements/metrics — and asked where to start.]_

---

## 34 — Shoshana

Can you actually store our whole conversation verbatim as an md file? Don't worry about the [decks]. I [care] more about the conversation and my questions.

**Claude:** _[This file.]_
