#!/usr/bin/env python3
"""
concept_aggregator.py — helper for the /concept-testing skill.

Three subcommands:

  --validate     Verify a ratings CSV is structurally sound against a research plan.
  --aggregate    Emit per-cell rating distribution + per-concept and study-level
                 metrics that feed Phase 4c-4e (study observations, cross-concept
                 synthesis, disposition).
  --render-html  Emit a self-contained HTML report from a spec JSON authored by
                 Claude. Tabbed editorial layout — Overview, Cross-Concept Insights,
                 one tab per concept, Methodology. Uses Harvey balls for verdicts
                 and a CSS-custom-property theme system.

Stdlib only. Claude composes the qualitative spec; this helper handles
deterministic CSV arithmetic and HTML/SVG/base64 assembly.
"""

import argparse
import base64
import csv
import html
import json
import mimetypes
import re
import sys
from collections import defaultdict
from pathlib import Path


VALID_RATINGS = {"completely", "partially", "not_at_all"}
RATINGS_HEADER = ("participant", "concept_id", "need_id", "rating")

VERDICTS = (
    "addresses",
    "partial",
    "doesnt_address",
    "creates_new_problem",
    "insufficient_evidence",
)

VERDICT_BALL = {
    "addresses":             "ball-full",
    "partial":               "ball-half",
    "doesnt_address":        "ball-empty",
    "creates_new_problem":   "ball-warn",
    "insufficient_evidence": "ball-insuf",
}

# short label used in matrix cells under the ball
VERDICT_SHORT_LABEL = {
    "addresses":             "addresses",
    "partial":               "partial",
    "doesnt_address":        "doesn't address",
    "creates_new_problem":   "creates new problem",
    "insufficient_evidence": "insufficient ev.",
}

# longer label used in finding cards next to the ball
VERDICT_LONG_LABEL = {
    "addresses":             "Addresses",
    "partial":               "Partial",
    "doesnt_address":        "Doesn't address",
    "creates_new_problem":   "Creates new problem",
    "insufficient_evidence": "Insufficient evidence",
}

# verdicts that need a special color override on the ball (otherwise inherits ink)
VERDICT_BALL_CLASS = {
    "creates_new_problem":   "warn",
    "insufficient_evidence": "insuf",
}

CONFIDENCES = ("high", "medium", "low")
CONF_PIPS = {"high": 3, "medium": 2, "low": 1}

RECOMMENDATION_LABEL = {
    "advance":               "Advance",
    "advance_with_followup": "Advance — with follow-up",
    "iterate":               "Iterate",
    "kill":                  "Kill",
    "park":                  "Park",
}

RECOMMENDATION_CLASS = {
    "advance":               "advance",
    "advance_with_followup": "advance",
    "iterate":               "iterate",
    "kill":                  "kill",
    "park":                  "park",
}

# Back-compat aliases — kept so other modules importing these names don't break
# during the disposition → recommendation rename. Prefer RECOMMENDATION_* in new code.
DISPOSITION_LABEL = RECOMMENDATION_LABEL
DISPOSITION_CLASS = RECOMMENDATION_CLASS


def need_display(need_id, label=None, statement=None):
    """Render a need identifier for display.

    Per the v3 naming convention, IDs matching ^N(\\d+)$ render as "Need <n>".
    Otherwise fall back to label, then statement, then the raw id.
    """
    m = re.match(r'^N(\d+)$', need_id or '')
    if m:
        return f"Need {m.group(1)}"
    return label or statement or (need_id or "")


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_ratings(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("ratings CSV is empty")
        missing = [c for c in RATINGS_HEADER if c not in reader.fieldnames]
        if missing:
            raise ValueError(
                f"ratings CSV missing columns: {missing}. "
                f"expected: {list(RATINGS_HEADER)}"
            )
        for i, row in enumerate(reader, start=2):
            rows.append({
                "_lineno": i,
                "participant": (row["participant"] or "").strip(),
                "concept_id":  (row["concept_id"]  or "").strip(),
                "need_id":     (row["need_id"]     or "").strip(),
                "rating":      (row["rating"]      or "").strip(),
            })
    return rows


def load_plan(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "needs" not in data or "concepts" not in data:
        raise ValueError("plan JSON must contain 'needs' and 'concepts'")
    return data


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

def cmd_validate(args):
    try:
        plan = load_plan(args.plan_json)
        rows = load_ratings(args.ratings)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return 2

    need_ids = {n["id"] for n in plan["needs"]}
    concept_ids = {c["id"] for c in plan["concepts"]}

    errors = []
    seen = set()

    for r in rows:
        loc = f"line {r['_lineno']}"
        if r["rating"] not in VALID_RATINGS:
            errors.append(f"{loc}: invalid rating {r['rating']!r}; "
                          f"expected one of {sorted(VALID_RATINGS)}")
        if r["concept_id"] not in concept_ids:
            errors.append(f"{loc}: concept_id {r['concept_id']!r} "
                          f"not in plan (have: {sorted(concept_ids)})")
        if r["need_id"] not in need_ids:
            errors.append(f"{loc}: need_id {r['need_id']!r} "
                          f"not in plan (have: {sorted(need_ids)})")
        if not r["participant"]:
            errors.append(f"{loc}: empty participant")
        key = (r["participant"], r["concept_id"], r["need_id"])
        if key in seen:
            errors.append(f"{loc}: duplicate row for "
                          f"participant={r['participant']} "
                          f"concept_id={r['concept_id']} "
                          f"need_id={r['need_id']}")
        seen.add(key)

    if errors:
        print(json.dumps({"error": "validation_failed", "details": errors}, indent=2))
        return 1

    summary = {
        "ok": True,
        "n_rows": len(rows),
        "n_participants": len({r["participant"] for r in rows}),
        "n_concepts": len({r["concept_id"] for r in rows}),
        "n_needs": len({r["need_id"] for r in rows}),
        "expected_cells": len(concept_ids) * len(need_ids),
    }
    print(json.dumps(summary, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------

def cmd_aggregate(args):
    plan = load_plan(args.plan_json)
    rows = load_ratings(args.ratings)

    need_ids = [n["id"] for n in plan["needs"]]
    concept_ids = [c["id"] for c in plan["concepts"]]
    target_map = {
        c["id"]: {tn["need_id"] for tn in c.get("target_needs", [])}
        for c in plan["concepts"]
    }

    cells = {cid: {nid: {
        "completely": 0,
        "partially": 0,
        "not_at_all": 0,
        "n": 0,
        "raters": {},
        "was_targeted": nid in target_map.get(cid, set()),
    } for nid in need_ids} for cid in concept_ids}

    for r in rows:
        cell = cells[r["concept_id"]][r["need_id"]]
        cell[r["rating"]] += 1
        cell["n"] += 1
        cell["raters"][r["participant"]] = r["rating"]

    for cid in concept_ids:
        for nid in need_ids:
            c = cells[cid][nid]
            if c["n"] == 0:
                c["majority"] = None
                c["majority_pct"] = 0.0
            else:
                top_count = max(c["completely"], c["partially"], c["not_at_all"])
                if c["completely"] == top_count:
                    c["majority"] = "completely"
                elif c["partially"] == top_count:
                    c["majority"] = "partially"
                else:
                    c["majority"] = "not_at_all"
                c["majority_pct"] = round(top_count / c["n"], 3)

    all_participants = sorted({r["participant"] for r in rows})
    n_participants_total = len(all_participants)

    # per-concept summaries
    concept_summaries = {}
    for cid in concept_ids:
        raters_for_concept = sorted({
            p for nid in need_ids
            for p in cells[cid][nid]["raters"].keys()
        })
        n_cells_rated = sum(1 for nid in need_ids if cells[cid][nid]["n"] > 0)
        concept_summaries[cid] = {
            "n_raters": len(raters_for_concept),
            "raters": raters_for_concept,
            "n_cells_rated": n_cells_rated,
            "is_sparse": len(raters_for_concept) < n_participants_total,
        }

    # uniform-rating candidates: (participant, concept) pairs where the
    # participant rated all of that concept's need cells with the same value
    uniform_candidates = []
    for cid in concept_ids:
        cell_dict = cells[cid]
        # group ratings by participant for this concept
        by_p = defaultdict(list)
        for nid in need_ids:
            for p, rating in cell_dict[nid]["raters"].items():
                by_p[p].append((nid, rating))
        for p, ratings in sorted(by_p.items()):
            if len(ratings) >= 2:  # need at least 2 cells to call uniform
                values = {rv for _, rv in ratings}
                if len(values) == 1:
                    uniform_candidates.append({
                        "participant_id": p,
                        "concept_id": cid,
                        "rating": ratings[0][1],
                        "n_cells": len(ratings),
                    })

    out = {
        "study_name": plan.get("study_name"),
        "concept_ids": concept_ids,
        "need_ids": need_ids,
        "participants": all_participants,
        "cells": cells,
        "concept_summaries": concept_summaries,
        "study_summary": {
            "n_participants_total": n_participants_total,
            "uniform_rating_candidates": uniform_candidates,
        },
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# Render HTML
# ---------------------------------------------------------------------------

def esc(s):
    return html.escape(s if s is not None else "", quote=True)


def encode_asset(path_or_text):
    """Try to resolve `path_or_text` to a base64 image data URI.
    Returns dict: {type: 'image', data_uri, alt} or {type: 'text', value}."""
    if not path_or_text:
        return {"type": "text", "value": ""}
    p = Path(path_or_text)
    if p.is_file():
        try:
            mime, _ = mimetypes.guess_type(str(p))
            if mime and mime.startswith("image/"):
                b64 = base64.b64encode(p.read_bytes()).decode("ascii")
                return {"type": "image", "data_uri": f"data:{mime};base64,{b64}",
                        "alt": p.name}
        except Exception:
            pass
    return {"type": "text", "value": path_or_text}


CSS = """
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: var(--sans);
  background: var(--bg);
  color: var(--ink);
  line-height: 1.55;
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
}

.page { max-width: 1180px; margin: 0 auto; padding: 40px 48px 80px; }

/* Header */
.masthead { border-bottom: 1px solid var(--ink); padding-bottom: 24px; margin-bottom: 28px; }
.eyebrow { font-family: var(--mono); font-size: 11px; letter-spacing: 0.18em;
           text-transform: uppercase; color: var(--accent); margin: 0 0 12px; }
.masthead h1 { font-family: var(--serif); font-weight: 500;
               font-size: clamp(32px, 4.2vw, 48px); line-height: 1.05;
               letter-spacing: -0.02em; margin: 0 0 16px;
               font-variation-settings: "opsz" 96; }
.masthead h1 em { font-style: italic; color: var(--accent); font-weight: 400; }
.meta { display: flex; flex-wrap: wrap; gap: 18px 28px; font-size: 13px; color: var(--ink-soft); }
.meta span strong { color: var(--ink); font-weight: 600; margin-left: 6px; }

/* Tabs */
.tabnav { display: flex; gap: 4px; border-bottom: 1px solid var(--rule);
          margin-bottom: 40px; overflow-x: auto; scrollbar-width: none; }
.tabnav::-webkit-scrollbar { display: none; }
.tab { background: none; border: none; border-bottom: 2px solid transparent;
       padding: 14px 20px; margin-bottom: -1px; font-family: var(--sans);
       font-size: 14px; font-weight: 500; color: var(--ink-mute); cursor: pointer;
       white-space: nowrap; letter-spacing: 0.01em;
       transition: color 0.15s, border-color 0.15s; }
.tab:hover { color: var(--ink-soft); }
.tab.active { color: var(--ink); border-bottom-color: var(--accent); }
.tab .tab-num { font-family: var(--mono); font-size: 10px; color: var(--ink-mute);
                margin-right: 8px; font-weight: 400; }
.tab.active .tab-num { color: var(--accent); }

/* Panels */
.panel { display: none; animation: fadein 0.25s ease; }
.panel.active { display: block; }
@keyframes fadein {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: none; }
}

/* Typography */
h2 { font-family: var(--serif); font-weight: 500; font-size: 26px;
     letter-spacing: -0.01em; margin: 0 0 16px; font-variation-settings: "opsz" 36; }
h3 { font-family: var(--serif); font-weight: 500; font-size: 20px;
     letter-spacing: -0.005em; margin: 28px 0 10px; }
h4 { font-family: var(--sans); font-weight: 600; font-size: 12px;
     letter-spacing: 0.14em; text-transform: uppercase; color: var(--ink-mute);
     margin: 28px 0 12px; }
p { margin: 0 0 14px; color: var(--ink-soft); }
p.lead { font-family: var(--serif); font-size: 19px; line-height: 1.55;
         color: var(--ink); font-weight: 400; font-variation-settings: "opsz" 24; }
p.lead em { color: var(--accent); font-style: italic; }

.section { margin-bottom: 48px; }
.section-head { display: flex; align-items: baseline; gap: 16px; margin-bottom: 20px;
                border-bottom: 1px solid var(--rule); padding-bottom: 8px; }
.section-head h2 { margin-bottom: 0; }
.section-head .section-num { font-family: var(--mono); font-size: 11px;
                             color: var(--ink-mute); letter-spacing: 0.1em; }

/* Verdict matrix (Harvey balls) */
.matrix-wrap { background: var(--paper); border: 1px solid var(--rule);
               border-radius: 4px; padding: 32px; box-shadow: var(--shadow); }
.matrix { display: grid; gap: 0; }
.matrix > div { padding: 14px 16px; border-bottom: 1px solid var(--rule-soft); }
.matrix > div.matrix-headrow { border-bottom: 1px solid var(--ink-soft); background: transparent; }
.matrix-corner { font-family: var(--mono); font-size: 10px; color: var(--ink-mute);
                 letter-spacing: 0.12em; text-transform: uppercase; padding-bottom: 12px !important; }
.matrix-col-head { font-family: var(--sans); font-size: 13px; font-weight: 600;
                   color: var(--ink); text-align: center; padding-bottom: 12px !important; }
.matrix-col-head .col-id { display: block; font-family: var(--mono); font-size: 10px;
                           color: var(--accent); letter-spacing: 0.1em; margin-bottom: 4px;
                           font-weight: 500; }
.matrix-row-head { font-family: var(--sans); font-size: 14px; font-weight: 600;
                   color: var(--ink); display: flex; flex-direction: column;
                   justify-content: center; }
.matrix-row-head .row-id { font-family: var(--mono); font-size: 10px;
                           color: var(--accent); letter-spacing: 0.1em;
                           margin-bottom: 2px; font-weight: 500; }
.matrix-cell { text-align: center; position: relative; cursor: default; }
.matrix-cell.designed::before {
  content: ''; position: absolute; top: 8px; right: 8px;
  width: 6px; height: 6px; background: var(--accent); border-radius: 50%;
}
.ball-svg { width: 36px; height: 36px; color: var(--ink); margin: 4px auto 8px; display: block; }
.ball-svg.warn { color: var(--neg); }
.ball-svg.insuf { color: var(--ink-mute); }
.conf-pips { display: inline-flex; gap: 3px; margin-top: 2px; }
.conf-pips span { width: 5px; height: 5px; border-radius: 50%;
                  background: var(--ink-mute); opacity: 0.25; }
.conf-pips span.on { opacity: 1; }
.verdict-label { display: block; font-size: 11px; color: var(--ink-mute);
                 margin-top: 4px; font-family: var(--mono); letter-spacing: 0.05em; }

/* Legend */
.legend { margin-top: 24px; padding: 20px 24px; background: var(--bg);
          border: 1px solid var(--rule-soft); border-radius: 4px;
          display: grid; grid-template-columns: 1fr 1fr; gap: 24px 32px; }
.legend-group h5 { font-family: var(--sans); font-size: 11px; text-transform: uppercase;
                   letter-spacing: 0.12em; color: var(--ink-mute); margin: 0 0 10px;
                   font-weight: 600; }
.legend-item { display: flex; align-items: center; gap: 10px; font-size: 13px;
               color: var(--ink-soft); margin-bottom: 6px; }
.legend-item svg { width: 18px; height: 18px; flex-shrink: 0; }
.legend-item .pip-row { display: inline-flex; gap: 3px; width: 18px;
                        align-items: center; justify-content: center; }
.legend-item .pip-row span { width: 5px; height: 5px; border-radius: 50%;
                              background: var(--ink-mute); opacity: 0.25; }
.legend-item .pip-row span.on { opacity: 1; }
.legend-item .designed-marker { width: 6px; height: 6px; background: var(--accent);
                                 border-radius: 50%; display: inline-block; }

/* Cards */
.card { background: var(--paper); border: 1px solid var(--rule); border-radius: 4px;
        padding: 24px 28px; margin-bottom: 16px; box-shadow: var(--shadow); }
.card-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }

/* Gap section */
.gap-list { list-style: none; padding: 0; margin: 0; }
.gap-list li { padding: 14px 0; border-bottom: 1px solid var(--rule-soft);
               display: flex; align-items: flex-start; gap: 14px;
               font-size: 14px; color: var(--ink-soft); }
.gap-list li:last-child { border-bottom: none; }
.gap-list .tag { flex-shrink: 0; font-family: var(--mono); font-size: 11px;
                 background: var(--ink); color: var(--paper); padding: 3px 8px;
                 border-radius: 2px; letter-spacing: 0.05em; }
.gap-list .tag.surprise { background: var(--pos); }

/* Emergent need */
.emergent-card { border-left: 3px solid var(--accent); padding: 20px 24px;
                 background: var(--paper); margin-bottom: 16px; }
.emergent-card h4 { color: var(--ink); text-transform: none; letter-spacing: 0;
                    font-family: var(--serif); font-size: 18px; font-weight: 500; margin: 0 0 8px; }
.emergent-meta { font-size: 12px; color: var(--ink-mute); font-family: var(--mono); margin-bottom: 12px; }
.emergent-quote { margin: 8px 0; padding: 8px 14px; border-left: 2px solid var(--rule);
                  font-style: italic; color: var(--ink-soft); font-size: 14px; }
.emergent-quote .attr { display: block; font-style: normal; font-family: var(--mono);
                         font-size: 11px; color: var(--ink-mute); margin-top: 4px;
                         letter-spacing: 0.05em; }
.emergent-card .missed { margin-top: 12px; font-size: 13px; color: var(--ink-soft); }
.emergent-card .missed strong { color: var(--ink); }

/* Concept hero */
.concept-hero { display: grid; grid-template-columns: 360px 1fr; gap: 36px;
                align-items: start; margin-bottom: 36px; padding-bottom: 32px;
                border-bottom: 1px solid var(--rule); }
.concept-image { aspect-ratio: 4 / 3; background: var(--paper);
                 border: 1px dashed var(--ink-mute); border-radius: 4px;
                 display: flex; flex-direction: column; align-items: center;
                 justify-content: center; position: relative; overflow: hidden; }
.concept-image.has-image { border-style: solid; border-color: var(--rule); padding: 0; }
.concept-image.has-image img { width: 100%; height: 100%; object-fit: cover; display: block; }
.concept-image::before {
  content: ''; position: absolute; inset: 0;
  background-image: linear-gradient(135deg, transparent 48%, var(--rule-soft) 49%, var(--rule-soft) 51%, transparent 52%);
  background-size: 12px 12px; opacity: 0.5;
}
.concept-image.has-image::before { display: none; }
.concept-image .placeholder-label { font-family: var(--mono); font-size: 10px;
                                     letter-spacing: 0.15em; text-transform: uppercase;
                                     color: var(--ink-mute); margin-bottom: 6px; z-index: 1;
                                     background: var(--paper); padding: 0 8px; }
.concept-image .placeholder-name { font-family: var(--serif); font-style: italic;
                                    font-size: 18px; color: var(--ink-soft); z-index: 1;
                                    background: var(--paper); padding: 0 12px; text-align: center; }
.concept-meta-id { font-family: var(--mono); font-size: 11px; letter-spacing: 0.15em;
                   color: var(--accent); margin-bottom: 10px; text-transform: uppercase; }
.concept-name { font-family: var(--serif); font-size: 34px; font-weight: 500;
                line-height: 1.1; letter-spacing: -0.01em; margin: 0 0 14px; }
.concept-desc { font-size: 15px; color: var(--ink-soft); margin-bottom: 22px; max-width: 60ch; }
.disposition { display: inline-flex; align-items: center; gap: 12px;
               padding: 12px 18px; border-radius: 4px; background: var(--paper);
               border: 1px solid var(--rule); margin-bottom: 14px; }
.disposition .label { font-family: var(--mono); font-size: 10px; letter-spacing: 0.15em;
                       text-transform: uppercase; color: var(--ink-mute); }
.disposition .value { font-family: var(--serif); font-size: 17px; font-weight: 500; font-style: italic; }
.disposition .value.advance { color: var(--pos); }
.disposition .value.iterate { color: var(--mixed); }
.disposition .value.kill { color: var(--neg); }
.disposition .value.park { color: var(--ink-mute); }
.disposition-rationale { font-size: 14px; color: var(--ink-soft); max-width: 60ch; font-style: italic; }

/* Distribution bars */
.dist-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
.dist-table th, .dist-table td { padding: 10px 8px; text-align: left;
                                  font-size: 13px; border-bottom: 1px solid var(--rule-soft); }
.dist-table th { font-family: var(--mono); font-size: 10px; text-transform: uppercase;
                 letter-spacing: 0.1em; color: var(--ink-mute); font-weight: 500; }
.dist-bar { display: flex; height: 18px; border-radius: 2px; overflow: hidden;
            background: var(--rule-soft); min-width: 160px; }
.dist-bar .seg { height: 100%; display: flex; align-items: center; justify-content: center;
                 font-size: 11px; color: white; font-weight: 600; }
.dist-bar .seg.completely { background: var(--pos); }
.dist-bar .seg.partially { background: var(--mixed); }
.dist-bar .seg.not_at_all { background: var(--neg); }

/* Aspects */
.aspect-row { display: flex; align-items: center; gap: 14px; padding: 12px 0;
              border-bottom: 1px solid var(--rule-soft); font-size: 14px; }
.aspect-row:last-child { border: none; }
.aspect-name { flex: 1; color: var(--ink); font-weight: 500; }
.aspect-direction { font-family: var(--mono); font-size: 10px; padding: 3px 8px;
                    border-radius: 2px; letter-spacing: 0.08em; text-transform: uppercase; }
.aspect-direction.up { background: rgba(47,95,58,0.12); color: var(--pos); }
.aspect-direction.down { background: rgba(155,42,42,0.12); color: var(--neg); }
.aspect-direction.mixed { background: rgba(138,110,26,0.14); color: var(--mixed); }
.aspect-count { font-family: var(--mono); font-size: 11px; color: var(--ink-mute);
                min-width: 80px; text-align: right; }

/* Findings */
.finding-card { background: var(--paper); border: 1px solid var(--rule); border-radius: 4px;
                padding: 22px 26px; margin-bottom: 14px; box-shadow: var(--shadow); }
.finding-head { display: flex; align-items: center; flex-wrap: wrap; gap: 14px;
                margin-bottom: 14px; padding-bottom: 14px;
                border-bottom: 1px solid var(--rule-soft); }
.finding-head h4 { margin: 0; color: var(--ink); text-transform: none;
                   letter-spacing: -0.005em; font-size: 16px; font-family: var(--serif);
                   font-weight: 500; flex: 1; }
.finding-head .need-id { font-family: var(--mono); font-size: 10px;
                          color: var(--accent); letter-spacing: 0.1em; margin-right: 6px; }
.finding-head .targeted-tag { font-family: var(--mono); font-size: 10px;
                               background: var(--accent); color: var(--paper);
                               padding: 3px 8px; border-radius: 2px;
                               letter-spacing: 0.08em; text-transform: uppercase; }
.finding-verdict { display: flex; align-items: center; gap: 10px; }
.finding-verdict svg { width: 24px; height: 24px; }
.finding-verdict .vtext { font-family: var(--mono); font-size: 11px;
                          text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }
.vtext.addresses { color: var(--pos); }
.vtext.partial { color: var(--mixed); }
.vtext.doesnt_address { color: var(--neg); }
.vtext.creates_new_problem { color: var(--neg); }
.vtext.insufficient_evidence { color: var(--ink-mute); }

.reconciliation { background: var(--bg); border-left: 3px solid var(--rule);
                  padding: 12px 16px; margin: 12px 0; font-size: 13px;
                  color: var(--ink-soft); line-height: 1.55; }
.reconciliation strong { font-family: var(--mono); font-size: 10px;
                          letter-spacing: 0.12em; text-transform: uppercase;
                          color: var(--ink-mute); display: block; margin-bottom: 4px; }

blockquote { margin: 12px 0; padding: 10px 0 10px 20px;
             border-left: 3px solid var(--rule); font-family: var(--serif);
             font-style: italic; font-size: 15px; color: var(--ink); line-height: 1.5; }
blockquote.pos { border-left-color: var(--pos); }
blockquote.neg { border-left-color: var(--neg); }
blockquote .attr { display: block; font-style: normal; font-family: var(--mono);
                    font-size: 11px; color: var(--ink-mute); margin-top: 6px; letter-spacing: 0.04em; }
.finding-notes { margin-top: 12px; font-size: 13.5px; color: var(--ink-soft);
                  padding: 10px 0 0; border-top: 1px dashed var(--rule); }

/* Cross-concept insights */
.insight-card { background: var(--paper); border: 1px solid var(--rule); border-radius: 4px;
                padding: 26px 30px; margin-bottom: 18px; box-shadow: var(--shadow); }
.insight-card h3 { margin-top: 0; display: flex; align-items: baseline; gap: 12px; }
.insight-card h3 .insight-num { font-family: var(--mono); font-size: 11px;
                                 color: var(--accent); letter-spacing: 0.1em; font-weight: 500; }
.insight-card p { font-size: 14.5px; }
.coverage-grid { display: grid; gap: 16px; margin: 16px 0 8px; }
.coverage-item { padding: 16px; background: var(--bg); border-radius: 4px;
                  border: 1px solid var(--rule-soft); }
.coverage-item .nid { font-family: var(--mono); font-size: 10px;
                       color: var(--accent); letter-spacing: 0.1em; }
.coverage-item .nname { font-family: var(--serif); font-size: 15px;
                         font-weight: 500; margin: 4px 0 10px; }
.coverage-balls { display: flex; gap: 14px; margin-bottom: 8px; }
.coverage-balls > div { text-align: center; }
.coverage-balls svg { width: 22px; height: 22px; display: block; margin: 0 auto 4px; }
.coverage-balls .cid { font-family: var(--mono); font-size: 9px;
                        color: var(--ink-mute); letter-spacing: 0.05em; }
.coverage-verdict { font-size: 12px; color: var(--ink-soft); margin-top: 6px; line-height: 1.4; }
.coverage-verdict strong { color: var(--ink); }
.strategic-list { padding-left: 18px; color: var(--ink-soft); font-size: 14.5px; line-height: 1.65; }
.strategic-list li { margin-bottom: 10px; }
.strategic-list li strong { color: var(--ink); }
.strategic-list li:last-child { margin-bottom: 0; }

/* Methodology */
.method-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; }
.method-grid .insight-card { margin-bottom: 0; }
dl.def-list { margin: 0; }
dl.def-list dt { font-family: var(--mono); font-size: 11px; text-transform: uppercase;
                  letter-spacing: 0.1em; color: var(--ink); font-weight: 600;
                  margin-top: 14px; display: flex; align-items: center; gap: 8px; }
dl.def-list dt:first-child { margin-top: 0; }
dl.def-list dt svg { width: 16px; height: 16px; }
dl.def-list dt .pip-row { display: inline-flex; gap: 3px; }
dl.def-list dt .pip-row span { width: 5px; height: 5px; border-radius: 50%;
                                background: var(--ink-mute); opacity: 0.25; }
dl.def-list dt .pip-row span.on { background: var(--ink); opacity: 1; }
dl.def-list dd { margin: 4px 0 0 24px; font-size: 13.5px; color: var(--ink-soft); }

/* Footer */
footer { margin-top: 60px; padding-top: 20px; border-top: 1px solid var(--rule);
         font-family: var(--mono); font-size: 11px; color: var(--ink-mute);
         letter-spacing: 0.05em; display: flex; justify-content: space-between; }

/* Overview-as-brief */
.brief-takeaway { font-family: var(--serif); font-style: italic; font-weight: 400;
                  font-size: clamp(22px, 2.6vw, 30px); line-height: 1.3;
                  letter-spacing: -0.01em; color: var(--ink);
                  margin: 4px 0 24px; max-width: 38ch;
                  font-variation-settings: "opsz" 48; }
.brief-takeaway em { color: var(--accent); font-style: italic; }

.brief-strip { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0;
               border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule);
               margin: 0 0 36px; }
.brief-strip > div { padding: 18px 24px 18px 0; border-right: 1px solid var(--rule-soft); }
.brief-strip > div:last-child { border-right: none; padding-right: 0; }
.brief-strip h5 { font-family: var(--mono); font-size: 10px; letter-spacing: 0.16em;
                  text-transform: uppercase; color: var(--ink-mute); margin: 0 0 8px;
                  font-weight: 500; }
.brief-strip p { font-family: var(--serif); font-size: 13.5px; line-height: 1.5;
                 color: var(--ink); margin: 0; font-variation-settings: "opsz" 16; }

/* Structured insight card (top findings, top recommendations, key insights additional) */
.sicard { background: var(--paper); border: 1px solid var(--rule); border-radius: 4px;
          padding: 22px 26px; margin-bottom: 14px; box-shadow: var(--shadow); }
.sicard .si-num { font-family: var(--mono); font-size: 11px; color: var(--accent);
                  letter-spacing: 0.12em; font-weight: 500; margin-right: 10px; }
.sicard .si-headline { font-family: var(--serif); font-size: 19px; font-weight: 500;
                       line-height: 1.35; color: var(--ink); margin: 0 0 14px;
                       letter-spacing: -0.005em; font-variation-settings: "opsz" 24;
                       display: flex; align-items: baseline; }
.sicard .si-headline > span.headtext { flex: 1; }
.sicard .si-evidence { margin: 4px 0 14px; padding: 10px 0;
                       border-top: 1px dashed var(--rule-soft);
                       border-bottom: 1px dashed var(--rule-soft); }
.sicard .si-evidence .si-ev { font-size: 13px; color: var(--ink-soft);
                              margin: 6px 0; line-height: 1.5; }
.sicard .si-evidence .si-ev .si-ev-attr { font-family: var(--mono); font-size: 10.5px;
                                          color: var(--ink-mute); letter-spacing: 0.04em;
                                          margin-right: 6px; }
.sicard .si-evidence .si-ev .si-snip { font-family: var(--serif); font-style: italic;
                                        color: var(--ink); }
.sicard .si-evidence .si-ev .si-metric { font-family: var(--mono); font-size: 11px;
                                          color: var(--accent); letter-spacing: 0.04em; }
.sicard .si-so { font-size: 14px; color: var(--ink-soft); margin: 0 0 8px; line-height: 1.55; }
.sicard .si-now { font-size: 14px; color: var(--ink-soft); margin: 0; line-height: 1.55; }
.sicard .si-so em, .sicard .si-now em { font-family: var(--serif); font-style: italic;
                                         color: var(--accent); font-weight: 500;
                                         margin-right: 8px; font-size: 13.5px; }

/* POC card */
.poc-card { background: var(--paper); border: 1px solid var(--rule); border-radius: 4px;
            padding: 22px 26px; margin-top: 8px; box-shadow: var(--shadow); }
.poc-card .poc-eyebrow { font-family: var(--mono); font-size: 10px; letter-spacing: 0.16em;
                         text-transform: uppercase; color: var(--ink-mute);
                         margin: 0 0 10px; font-weight: 500; }
.poc-card .poc-name { font-family: var(--serif); font-size: 17px; font-weight: 500;
                      color: var(--ink); margin: 0; }
.poc-card .poc-name .poc-role { color: var(--ink-soft); font-style: italic;
                                font-size: 14px; margin-left: 8px; }
.poc-card .poc-email { display: block; font-family: var(--mono); font-size: 12.5px;
                       color: var(--accent); margin: 6px 0 0; text-decoration: none; }
.poc-card .poc-email:hover { text-decoration: underline; }
.poc-card .poc-links { margin: 8px 0 0; padding: 0; list-style: none;
                       font-family: var(--mono); font-size: 11.5px; color: var(--ink-mute);
                       display: flex; flex-wrap: wrap; gap: 14px; }
.poc-card .poc-links a { color: var(--accent); text-decoration: none; }
.poc-card .poc-links a:hover { text-decoration: underline; }

/* Project-name h1 styling override on the masthead */
.masthead h1.project-name { font-style: normal; }

/* Recommendation badge (renamed from disposition; structure preserved) */
.recommendation { display: inline-flex; align-items: center; gap: 12px;
                  padding: 12px 18px; border-radius: 4px; background: var(--paper);
                  border: 1px solid var(--rule); margin-bottom: 14px; }
.recommendation .label { font-family: var(--mono); font-size: 10px; letter-spacing: 0.15em;
                          text-transform: uppercase; color: var(--ink-mute); }
.recommendation .value { font-family: var(--serif); font-size: 17px; font-weight: 500; font-style: italic; }
.recommendation .value.advance { color: var(--pos); }
.recommendation .value.iterate { color: var(--mixed); }
.recommendation .value.kill { color: var(--neg); }
.recommendation .value.park { color: var(--ink-mute); }
.recommendation-rationale { font-size: 14px; color: var(--ink-soft); max-width: 60ch; font-style: italic; }

/* High-level finding strip on concept tabs */
.finding-strip { margin: 0 0 28px; padding: 16px 0 18px;
                 border-top: 1px solid var(--rule-soft);
                 border-bottom: 1px solid var(--rule-soft); }
.finding-strip h3 { font-family: var(--mono); font-size: 10px; letter-spacing: 0.16em;
                    text-transform: uppercase; color: var(--ink-mute); margin: 0 0 8px;
                    font-weight: 500; font-style: normal; }
.finding-strip p { font-family: var(--serif); font-style: italic; font-size: 19px;
                   color: var(--accent); margin: 0; line-height: 1.4; max-width: 50ch;
                   font-variation-settings: "opsz" 24; }

/* Section banner used on Key Insights cards (so/now block) */
.section-banner { background: var(--bg); border: 1px solid var(--rule-soft);
                  border-radius: 4px; padding: 14px 18px; margin: 18px 0 0;
                  font-size: 13.5px; color: var(--ink-soft); line-height: 1.55; }
.section-banner p { margin: 4px 0; color: var(--ink-soft); font-size: 13.5px; }
.section-banner em { font-family: var(--serif); font-style: italic; color: var(--accent);
                     font-weight: 500; margin-right: 8px; font-size: 13.5px; }

@media (max-width: 880px) {
  .page { padding: 24px 20px 60px; }
  .matrix-row-head { font-size: 12px; padding: 12px 8px !important; }
  .concept-hero { grid-template-columns: 1fr; }
  .legend { grid-template-columns: 1fr; }
  .method-grid { grid-template-columns: 1fr; }
  .card-grid-2 { grid-template-columns: 1fr; }
  .brief-strip { grid-template-columns: 1fr; }
  .brief-strip > div { border-right: none; border-bottom: 1px solid var(--rule-soft);
                       padding: 14px 0; }
  .brief-strip > div:last-child { border-bottom: none; }
}
""".strip()


THEME_EDITORIAL = """
:root {
  --bg: #f6f4ee;
  --paper: #fbfaf6;
  --ink: #1c1a17;
  --ink-soft: #4a463f;
  --ink-mute: #807a70;
  --rule: #d8d3c6;
  --rule-soft: #e8e3d6;
  --accent: #8b3a17;
  --accent-soft: #c9663a;
  --pos: #2f5f3a;
  --neg: #9b2a2a;
  --mixed: #8a6e1a;
  --warn-bg: #f1e6dc;
  --shadow: 0 1px 0 rgba(28,26,23,0.04), 0 6px 22px -12px rgba(28,26,23,0.18);
  --serif: 'Fraunces', Georgia, serif;
  --sans: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  --mono: 'IBM Plex Mono', ui-monospace, monospace;
}
""".strip()


SVG_SYMBOLS = """
<svg style="position:absolute;width:0;height:0" aria-hidden="true">
  <defs>
    <symbol id="ball-full" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="9" fill="currentColor"/>
    </symbol>
    <symbol id="ball-half" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.5"/>
      <path d="M 12 3 A 9 9 0 0 1 12 21 Z" fill="currentColor"/>
    </symbol>
    <symbol id="ball-empty" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.5"/>
    </symbol>
    <symbol id="ball-warn" viewBox="0 0 24 24">
      <path d="M 12 3 L 22 21 L 2 21 Z" fill="currentColor" stroke="currentColor" stroke-width="0.5" stroke-linejoin="round"/>
      <text x="12" y="18" text-anchor="middle" fill="white" font-size="11" font-weight="700" font-family="IBM Plex Sans, sans-serif">!</text>
    </symbol>
    <symbol id="ball-insuf" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2.5 2.5"/>
      <text x="12" y="16" text-anchor="middle" fill="currentColor" font-size="10" font-weight="700" font-family="IBM Plex Sans, sans-serif">?</text>
    </symbol>
  </defs>
</svg>
""".strip()


JS_TABSWITCH = """
<script>
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.target;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(target).classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
});
document.querySelectorAll('[data-jump]').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const target = link.dataset.jump;
    document.querySelector('.tab[data-target="' + target + '"]').click();
  });
});
</script>
""".strip()


# ---- ball + pip rendering helpers ---------------------------------------

def render_ball(verdict, size_class="ball-svg"):
    symbol = VERDICT_BALL.get(verdict, "ball-insuf")
    extra = VERDICT_BALL_CLASS.get(verdict, "")
    cls = size_class + ((" " + extra) if extra else "")
    return f'<svg class="{cls}"><use href="#{symbol}"/></svg>'


def render_ball_inline(verdict, color_var=None):
    """Ball outside .ball-svg styling — used in coverage grids and finding cards."""
    symbol = VERDICT_BALL.get(verdict, "ball-insuf")
    if color_var:
        style = f' style="color:var({color_var})"'
    elif verdict == "creates_new_problem":
        style = ' style="color:var(--neg)"'
    elif verdict == "insufficient_evidence":
        style = ' style="color:var(--ink-mute)"'
    else:
        style = ""
    return f'<svg{style}><use href="#{symbol}"/></svg>'


def render_pips(confidence, container_class="conf-pips"):
    n_on = CONF_PIPS.get(confidence, 0)
    pips = ''.join('<span class="on"></span>' if i < n_on else '<span></span>'
                   for i in range(3))
    return f'<span class="{container_class}">{pips}</span>'


# ---- panel renderers ----------------------------------------------------

def render_doc_head(spec):
    title = esc(spec.get("study_name", "Concept Testing Report"))
    return (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f'<title>{title} — Concept Testing Report</title>'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">'
        f'<style>{THEME_EDITORIAL}\n{CSS}</style>'
        '</head><body>'
    )


def render_masthead(spec):
    eyebrow = spec.get("study_subtitle") or "Concept Testing Report"
    project_name = spec.get("project_name")
    if project_name:
        eyebrow = "Project · " + project_name
        title_html = f'<span class="project-name-text">{esc(project_name)}</span>'
        h1_cls = ' class="project-name"'
    else:
        title_html = spec.get("masthead_h1_html") or (
            f'How <em>{len(spec.get("concepts", []))}</em> concepts address '
            f'<em>{len(spec.get("needs", []))}</em> needs.'
        )
        h1_cls = ''
    method_text = spec.get("method_description") or "Past-use stories + concept ratings"
    return (
        '<header class="masthead">'
        f'<p class="eyebrow">{esc(eyebrow)}</p>'
        f'<h1{h1_cls}>{title_html}</h1>'
        '<div class="meta">'
        f'<span>Date <strong>{esc(spec.get("date",""))}</strong></span>'
        f'<span>Participants <strong>{len(spec.get("participants",[]))}</strong></span>'
        f'<span>Concepts <strong>{len(spec.get("concepts",[]))}</strong></span>'
        f'<span>Needs tested <strong>{len(spec.get("needs",[]))}</strong></span>'
        f'<span>Method <strong>{esc(method_text)}</strong></span>'
        '</div></header>'
    )


def render_tabnav(spec):
    # Panel id "cross" is retained for back-compat (kept as DOM id); button label
    # changes from "Cross-Concept Insights" to "Key Insights" per v3.
    tabs = [("overview", "Overview"), ("cross", "Key Insights")]
    for c in spec.get("concepts", []):
        tabs.append((c["id"].lower(), f'{esc(c["id"])}: {esc(c["name"])}'))
    tabs.append(("method", "Methodology"))
    parts = ['<nav class="tabnav" role="tablist">']
    for i, (tid, label) in enumerate(tabs, start=1):
        active = " active" if i == 1 else ""
        parts.append(
            f'<button class="tab{active}" data-target="{tid}" role="tab">'
            f'<span class="tab-num">{i:02d}</span>{label}</button>'
        )
    parts.append('</nav>')
    return ''.join(parts)


def render_matrix(spec, find_index):
    needs = spec["needs"]
    concepts = spec["concepts"]
    n_cols = 1 + len(needs)
    grid_cols = f'220px repeat({len(needs)}, 1fr)'

    parts = [f'<div class="matrix-wrap"><div class="matrix" style="grid-template-columns: {grid_cols}">']

    # header row — 1 corner + N column heads, each marked .matrix-headrow
    parts.append('<div class="matrix-corner matrix-headrow">Concept × Need</div>')
    for need in needs:
        display = need_display(need.get("id", ""), need.get("label"), need.get("statement"))
        # If the ID was a generic Nn pattern, display now shows "Need n";
        # also show the underlying label (if distinct) as a smaller subtitle.
        sub_label = need.get("label") or need.get("statement") or ""
        if display == sub_label:
            sub_label = ""
        sub_html = f'<div style="font-family:var(--mono);font-size:9px;color:var(--ink-mute);letter-spacing:0.06em;font-weight:400;margin-top:3px;text-transform:none">{esc(sub_label)}</div>' if sub_label else ''
        parts.append(
            f'<div class="matrix-col-head matrix-headrow">'
            f'<span class="col-id">{esc(need["id"])}</span>{esc(display)}{sub_html}</div>'
        )

    # data rows
    for concept in concepts:
        parts.append(
            f'<div class="matrix-row-head">'
            f'<span class="row-id">{esc(concept["id"])}</span>{esc(concept["name"])}</div>'
        )
        for need in needs:
            f = find_index.get((concept["id"], need["id"]))
            if not f:
                # blank cell
                parts.append('<div class="matrix-cell"></div>')
                continue
            verdict = f["verdict"]
            confidence = f.get("confidence", "low")
            designed_cls = " designed" if f.get("was_targeted") else ""
            parts.append(
                f'<div class="matrix-cell{designed_cls}">'
                f'{render_ball(verdict)}'
                f'{render_pips(confidence)}'
                f'<span class="verdict-label">{esc(VERDICT_SHORT_LABEL.get(verdict, verdict))}</span>'
                f'</div>'
            )

    parts.append('</div>')  # close .matrix
    parts.append(render_legend())
    parts.append('</div>')  # close .matrix-wrap
    return ''.join(parts)


def render_legend():
    return (
        '<div class="legend">'
        '<div class="legend-group"><h5>Verdict</h5>'
        f'<div class="legend-item">{render_ball_inline("addresses")}Addresses the need</div>'
        f'<div class="legend-item">{render_ball_inline("partial")}Partially addresses</div>'
        f'<div class="legend-item">{render_ball_inline("doesnt_address")}Does not address</div>'
        f'<div class="legend-item">{render_ball_inline("creates_new_problem")}Creates new problem</div>'
        f'<div class="legend-item">{render_ball_inline("insufficient_evidence")}Insufficient evidence</div>'
        '</div>'
        '<div class="legend-group"><h5>Confidence &amp; design intent</h5>'
        f'<div class="legend-item">{render_pips("high", "pip-row")}High confidence (consistent signal across participants)</div>'
        f'<div class="legend-item">{render_pips("medium", "pip-row")}Medium confidence</div>'
        f'<div class="legend-item">{render_pips("low", "pip-row")}Low confidence (sparse or contradictory)</div>'
        '<div class="legend-item"><span class="designed-marker"></span>Concept was designed for this need</div>'
        '</div>'
        '</div>'
    )


def _render_structured_insight(item, idx=None):
    """Render one StructuredInsight as an .sicard block.

    Shape:
      insight: str
      evidence: [{snippet?, participant_id?, metric?, source_ref?}]
      so_what: str
      now_what: str
    """
    parts = ['<div class="sicard">']
    num_html = f'<span class="si-num">{idx:02d}</span>' if idx is not None else ''
    headline = item.get("insight") or ""
    parts.append(
        f'<h3 class="si-headline">{num_html}'
        f'<span class="headtext">{headline}</span></h3>'
    )
    evidence = item.get("evidence") or []
    if evidence:
        parts.append('<div class="si-evidence">')
        for ev in evidence:
            attr_bits = []
            if ev.get("participant_id"):
                attr_bits.append(esc(ev["participant_id"]))
            if ev.get("source_ref"):
                attr_bits.append(esc(ev["source_ref"]))
            attr = " · ".join(attr_bits)
            attr_html = f'<span class="si-ev-attr">{attr}</span>' if attr else ''
            row_parts = []
            if ev.get("snippet"):
                row_parts.append(f'<span class="si-snip">"{esc(ev["snippet"])}"</span>')
            if ev.get("metric"):
                row_parts.append(f'<span class="si-metric">{esc(ev["metric"])}</span>')
            if not row_parts:
                continue
            parts.append(
                f'<div class="si-ev">{attr_html}'
                f'{" — ".join(row_parts)}</div>'
            )
        parts.append('</div>')
    if item.get("so_what"):
        parts.append(
            f'<p class="si-so"><em>So what.</em>{esc(item["so_what"])}</p>'
        )
    if item.get("now_what"):
        parts.append(
            f'<p class="si-now"><em>Now what.</em>{esc(item["now_what"])}</p>'
        )
    parts.append('</div>')
    return ''.join(parts)


def _render_poc_card(poc):
    if not poc:
        return ""
    name = esc(poc.get("name", ""))
    role = esc(poc.get("role", ""))
    email = poc.get("email", "")
    parts = ['<div class="poc-card">',
             '<p class="poc-eyebrow">Point of contact</p>']
    role_html = f' <span class="poc-role">— {role}</span>' if role else ""
    parts.append(f'<p class="poc-name">{name}{role_html}</p>')
    if email:
        parts.append(
            f'<a class="poc-email" href="mailto:{esc(email)}">{esc(email)}</a>'
        )
    links = poc.get("links") or []
    if links:
        parts.append('<ul class="poc-links">')
        for ln in links:
            url = ln.get("url", "")
            label = ln.get("label") or url
            parts.append(f'<li><a href="{esc(url)}">{esc(label)}</a></li>')
        parts.append('</ul>')
    parts.append('</div>')
    return ''.join(parts)


def render_overview_panel(spec, find_index):
    parts = ['<section class="panel active" id="overview" role="tabpanel">']

    # 1. Single-sentence takeaway
    takeaway = spec.get("single_sentence_takeaway")
    if takeaway:
        parts.append(f'<p class="brief-takeaway">{takeaway}</p>')

    # 2. 3-column strip: research question | method | how to use
    rq = spec.get("research_question")
    method = spec.get("method_description") or "Past-use stories + per-need usefulness ratings"
    usage = spec.get("usage_guidance")
    if rq or method or usage:
        parts.append('<div class="brief-strip">')
        parts.append(
            '<div><h5>Research question</h5>'
            f'<p>{esc(rq) if rq else "—"}</p></div>'
        )
        parts.append(
            '<div><h5>Method</h5>'
            f'<p>{esc(method)}</p></div>'
        )
        parts.append(
            '<div><h5>How to use these results</h5>'
            f'<p>{esc(usage) if usage else "—"}</p></div>'
        )
        parts.append('</div>')

    # 3. Top findings
    top_findings = spec.get("top_findings") or []
    if top_findings:
        parts.append('<div class="section">'
                     '<div class="section-head"><span class="section-num">§01</span>'
                     '<h2>Top findings</h2></div>')
        for i, it in enumerate(top_findings, start=1):
            parts.append(_render_structured_insight(it, idx=i))
        parts.append('</div>')

    # 4. Top recommendations
    top_recs = spec.get("top_recommendations") or []
    if top_recs:
        parts.append('<div class="section">'
                     '<div class="section-head"><span class="section-num">§02</span>'
                     '<h2>Top recommendations</h2></div>')
        for i, it in enumerate(top_recs, start=1):
            parts.append(_render_structured_insight(it, idx=i))
        parts.append('</div>')

    # 5. Concept × Need Matrix (renamed from Verdict matrix)
    parts.append('<div class="section">'
                 '<div class="section-head"><span class="section-num">§03</span>'
                 '<h2>Concept × Need Matrix</h2></div>')
    parts.append(render_matrix(spec, find_index))
    parts.append('</div>')

    # 6. POC card
    poc = spec.get("poc")
    if poc:
        parts.append('<div class="section">'
                     '<div class="section-head"><span class="section-num">§04</span>'
                     '<h2>Point of contact</h2></div>')
        parts.append(_render_poc_card(poc))
        parts.append('</div>')

    parts.append('</section>')
    return ''.join(parts)


def compute_gap(spec, find_index):
    missed, surprises = [], []
    for c in spec["concepts"]:
        for n in spec["needs"]:
            f = find_index.get((c["id"], n["id"]))
            if not f:
                continue
            if f.get("was_targeted") and f["verdict"] in {"partial", "doesnt_address", "creates_new_problem"}:
                missed.append((c, n, f))
            if not f.get("was_targeted") and f["verdict"] == "addresses":
                surprises.append((c, n, f))
    return missed, surprises


def render_cross_panel(spec, find_index):
    """Render the Key Insights tab. Panel id `cross` kept for back-compat."""
    parts = ['<section class="panel" id="cross" role="tabpanel">']
    # v3 spec field is `key_insights`; fall back to legacy `cross_concept_insights`.
    ki = spec.get("key_insights") or spec.get("cross_concept_insights") or {}

    if ki.get("lead_paragraph"):
        parts.append(f'<p class="lead">{ki["lead_paragraph"]}</p>')

    n = 1
    # 01 — coverage by need
    coverage = ki.get("coverage_by_need") or []
    if coverage:
        parts.append(f'<div class="insight-card">'
                     f'<h3><span class="insight-num">{n:02d}</span>Need coverage across the portfolio</h3>')
        n += 1
        if ki.get("coverage_intro"):
            parts.append(f'<p>{ki["coverage_intro"]}</p>')
        n_cols = max(1, len(coverage))
        parts.append(f'<div class="coverage-grid" style="grid-template-columns: repeat({n_cols}, 1fr)">')
        for item in coverage:
            need = next((nd for nd in spec["needs"] if nd["id"] == item["need_id"]), None)
            display = need_display(
                item["need_id"],
                need.get("label") if need else None,
                need.get("statement") if need else None,
            )
            label = (need.get("label") or need.get("statement") or "") if need else ""
            parts.append('<div class="coverage-item">')
            parts.append(f'<span class="nid">{esc(item["need_id"])}</span>')
            parts.append(f'<div class="nname">{esc(display)}</div>')
            if label and label != display:
                parts.append(
                    f'<div style="font-family:var(--mono);font-size:10px;'
                    f'color:var(--ink-mute);letter-spacing:0.04em;'
                    f'margin:-6px 0 8px">{esc(label)}</div>'
                )
            parts.append('<div class="coverage-balls">')
            for owner in item.get("owners", []):
                parts.append(
                    f'<div>{render_ball_inline(owner["verdict"])}'
                    f'<span class="cid">{esc(owner["concept_id"])}</span></div>'
                )
            parts.append('</div>')
            parts.append(f'<div class="coverage-verdict">{item.get("summary","")}</div>')
            parts.append('</div>')
        parts.append('</div>')  # close coverage-grid
        # so/now block for coverage section
        cso = ki.get("coverage_so_what")
        cnow = ki.get("coverage_now_what")
        if cso or cnow:
            parts.append('<div class="section-banner">')
            if cso:
                parts.append(f'<p><em>So what.</em>{esc(cso)}</p>')
            if cnow:
                parts.append(f'<p><em>Now what.</em>{esc(cnow)}</p>')
            parts.append('</div>')
        parts.append('</div>')

    # 02 — recurring drivers
    drivers = ki.get("recurring_drivers") or []
    if drivers:
        parts.append(f'<div class="insight-card">'
                     f'<h3><span class="insight-num">{n:02d}</span>Recurring drivers across concepts</h3>')
        n += 1
        if ki.get("drivers_intro"):
            parts.append(f'<p>{ki["drivers_intro"]}</p>')
        for d in drivers:
            citations = ", ".join(
                f'{esc(c["concept_id"])} ({c["count"]})' for c in d.get("citations", [])
            )
            note = f' · {esc(d["note"])}' if d.get("note") else ""
            parts.append(
                f'<div class="aspect-row">'
                f'<div class="aspect-name">{esc(d["label"])}</div>'
                f'<span class="aspect-direction {esc(d["direction"])}">driver-{esc(d["direction"])}</span>'
                f'<span class="aspect-count">{citations}{note}</span>'
                f'</div>'
            )
        # so/now block for drivers section
        dso = ki.get("drivers_so_what") or ki.get("drivers_outro")
        dnow = ki.get("drivers_now_what")
        if dso or dnow:
            parts.append('<div class="section-banner">')
            if dso:
                parts.append(f'<p><em>So what.</em>{esc(dso)}</p>')
            if dnow:
                parts.append(f'<p><em>Now what.</em>{esc(dnow)}</p>')
            parts.append('</div>')
        parts.append('</div>')

    # 03 — additional insights (StructuredInsight)
    additional = ki.get("additional_insights") or []
    for it in additional:
        parts.append(f'<div class="insight-card">'
                     f'<h3><span class="insight-num">{n:02d}</span>{esc(it.get("insight",""))}</h3>')
        n += 1
        # render evidence + so/now using the shared structure
        evidence = it.get("evidence") or []
        if evidence:
            parts.append('<div class="si-evidence">')
            for ev in evidence:
                attr_bits = []
                if ev.get("participant_id"):
                    attr_bits.append(esc(ev["participant_id"]))
                if ev.get("source_ref"):
                    attr_bits.append(esc(ev["source_ref"]))
                attr = " · ".join(attr_bits)
                attr_html = f'<span class="si-ev-attr">{attr}</span>' if attr else ''
                row_parts = []
                if ev.get("snippet"):
                    row_parts.append(f'<span class="si-snip">"{esc(ev["snippet"])}"</span>')
                if ev.get("metric"):
                    row_parts.append(f'<span class="si-metric">{esc(ev["metric"])}</span>')
                if not row_parts:
                    continue
                parts.append(
                    f'<div class="si-ev">{attr_html}'
                    f'{" — ".join(row_parts)}</div>'
                )
            parts.append('</div>')
        if it.get("so_what"):
            parts.append(f'<p class="si-so"><em>So what.</em>{esc(it["so_what"])}</p>')
        if it.get("now_what"):
            parts.append(f'<p class="si-now"><em>Now what.</em>{esc(it["now_what"])}</p>')
        parts.append('</div>')

    # NOTE: methodological observations moved to Methodology tab.
    # NOTE: emergent needs moved to per-concept tabs (rendered if any).

    # Back-compat: legacy `strategic_implications` if present (v2 specs).
    impl = ki.get("strategic_implications") or []
    if impl:
        parts.append(f'<div class="insight-card">'
                     f'<h3><span class="insight-num">{n:02d}</span>Strategic implications</h3>')
        if ki.get("implications_intro"):
            parts.append(f'<p>{ki["implications_intro"]}</p>')
        parts.append('<ul class="strategic-list">')
        for it in impl:
            parts.append(
                f'<li><strong>{esc(it["headline"])}</strong> {it["body"]}</li>'
            )
        parts.append('</ul></div>')

    parts.append('</section>')
    return ''.join(parts)


def render_concept_panel(concept, spec, find_index):
    pid = concept["id"].lower()
    parts = [f'<section class="panel" id="{esc(pid)}" role="tabpanel">']

    # Hero (image + meta + recommendation badge)
    parts.append('<div class="concept-hero">')
    parts.append(_render_concept_image(concept))
    parts.append('<div>')
    parts.append(f'<p class="concept-meta-id">Concept {esc(concept["id"])}</p>')
    parts.append(f'<h2 class="concept-name">{esc(concept["name"])}</h2>')
    parts.append(f'<p class="concept-desc">{esc(concept.get("description",""))}</p>')

    # Recommendation (back-compat: read disposition if recommendation is absent)
    rec = concept.get("recommendation") or concept.get("disposition")
    if rec:
        verdict = rec.get("verdict", "park")
        label = rec.get("label") or RECOMMENDATION_LABEL.get(verdict, verdict)
        cls = RECOMMENDATION_CLASS.get(verdict, "park")
        parts.append('<div class="recommendation">')
        parts.append('<span class="label">Recommendation</span>')
        parts.append(f'<span class="value {esc(cls)}">{esc(label)}</span>')
        parts.append('</div>')
        if rec.get("rationale"):
            parts.append(f'<p class="recommendation-rationale">{esc(rec["rationale"])}</p>')
    parts.append('</div></div>')

    # High-level finding strip (replaces past-use synthesis section)
    hl = concept.get("high_level_finding")
    if hl:
        parts.append('<div class="finding-strip">'
                     '<h3>Finding</h3>'
                     f'<p>{esc(hl)}</p>'
                     '</div>')

    # Rating distribution
    if concept.get("rating_distribution"):
        parts.append(_render_dist_section(concept, spec))

    # Aspects
    if concept.get("aspects"):
        parts.append('<div class="section"><h3>Aspects</h3>')
        for a in concept["aspects"]:
            parts.append(
                f'<div class="aspect-row">'
                f'<div class="aspect-name">{esc(a["label"])}</div>'
                f'<span class="aspect-direction {esc(a["direction"])}">driver-{esc(a["direction"])}</span>'
                f'<span class="aspect-count">cited by {a.get("count","?")}</span>'
                f'</div>'
            )
        parts.append('</div>')

    # Per-need findings
    parts.append('<div class="section"><h3>Per-need findings</h3>')
    for need in spec["needs"]:
        f = find_index.get((concept["id"], need["id"]))
        if not f:
            continue
        parts.append(_render_finding_card(f, need))
    parts.append('</div>')

    # Designed-vs-actual gaps relevant to THIS concept
    this_missed, this_surprises = _compute_gap_for_concept(concept, spec, find_index)
    if this_missed or this_surprises:
        parts.append('<div class="section"><h3>Designed-vs-actual</h3>'
                     '<div class="card-grid-2">')
        parts.append('<div class="card"><h4>Designed but missed</h4><ul class="gap-list">')
        if this_missed:
            for n, f in this_missed:
                display = need_display(n.get("id", ""), n.get("label"), n.get("statement"))
                verdict = f["verdict"]
                parts.append(
                    f'<li><span class="tag">{esc(concept["id"])} → {esc(n["id"])}</span>'
                    f'Designed for <em>"{esc(display)}"</em>. '
                    f'Verdict: {esc(VERDICT_SHORT_LABEL.get(verdict, verdict))}.</li>'
                )
        else:
            parts.append('<li>No designed-but-missed cells for this concept.</li>')
        parts.append('</ul></div>')
        parts.append('<div class="card"><h4>Good surprises</h4><ul class="gap-list">')
        if this_surprises:
            for n, f in this_surprises:
                display = need_display(n.get("id", ""), n.get("label"), n.get("statement"))
                parts.append(
                    f'<li><span class="tag surprise">{esc(concept["id"])} → {esc(n["id"])}</span>'
                    f'Addresses <em>"{esc(display)}"</em> even though it was not designed to.</li>'
                )
        else:
            parts.append('<li>No good-surprise cells for this concept.</li>')
        parts.append('</ul></div></div></div>')

    # Emergent need raised during THIS concept's sessions
    this_emergents = _emergents_for_concept(concept, spec)
    if this_emergents:
        parts.append('<div class="section">'
                     "<h3>Emergent need raised during this concept's sessions</h3>")
        for em, evs in this_emergents:
            parts.append('<div class="emergent-card">')
            parts.append(f'<h4>{esc(em["label"])}</h4>')
            for ev in evs:
                parts.append(
                    f'<div class="emergent-quote">"{esc(ev["snippet"])}"'
                    f'<span class="attr">— {esc(ev["participant_id"])}</span></div>'
                )
            if em.get("missed_by"):
                parts.append(
                    f'<p class="missed"><strong>Missed by:</strong> '
                    f'{", ".join(esc(c) for c in em["missed_by"])}.</p>'
                )
            parts.append('</div>')
        parts.append('</div>')

    parts.append('</section>')
    return ''.join(parts)


def _compute_gap_for_concept(concept, spec, find_index):
    missed, surprises = [], []
    for n in spec["needs"]:
        f = find_index.get((concept["id"], n["id"]))
        if not f:
            continue
        if f.get("was_targeted") and f["verdict"] in {"partial", "doesnt_address", "creates_new_problem"}:
            missed.append((n, f))
        if not f.get("was_targeted") and f["verdict"] == "addresses":
            surprises.append((n, f))
    return missed, surprises


def _emergents_for_concept(concept, spec):
    """Return emergent needs that were surfaced during this concept's sessions.

    Heuristic: evidence.source_id mentions this concept_id (e.g. "notes:P02:C1").
    """
    out = []
    cid = concept["id"]
    for em in spec.get("emergent_needs") or []:
        matching = []
        for ev in em.get("evidence") or []:
            sid = ev.get("source_id") or ""
            loc = ev.get("location") or ""
            if cid in sid or cid in loc:
                matching.append(ev)
        if matching:
            out.append((em, matching))
    return out


def _render_concept_image(concept):
    si = concept.get("stimulus_image") or {}
    path = si.get("path")
    label = si.get("label") or "Stimulus image"
    name = si.get("name") or concept.get("name", "")
    if path:
        asset = encode_asset(path)
        if asset["type"] == "image":
            return (
                f'<div class="concept-image has-image">'
                f'<img src="{asset["data_uri"]}" alt="{esc(asset.get("alt", name))}"/>'
                f'</div>'
            )
    return (
        '<div class="concept-image">'
        f'<span class="placeholder-label">{esc(label)}</span>'
        f'<span class="placeholder-name">{esc(name)}</span>'
        '</div>'
    )


def _render_dist_section(concept, spec):
    nid_to_need = {n["id"]: n for n in spec["needs"]}
    parts = ['<div class="section"><h3>Rating distribution</h3>'
             '<table class="dist-table">'
             '<thead><tr><th>Need</th><th>Distribution</th><th>n</th></tr></thead><tbody>']
    for row in concept["rating_distribution"]:
        n = row["n"] or 0
        need = nid_to_need.get(row["need_id"], {})
        display = need_display(row["need_id"], need.get("label"), need.get("statement"))
        label = need.get("label") or need.get("statement") or ""
        sub = f' <span style="color:var(--ink-mute);font-size:12px">{esc(label)}</span>' if label and label != display else ""
        bar = '<div class="dist-bar">'
        for k in ("completely", "partially", "not_at_all"):
            count = row.get(k, 0)
            if count and n:
                pct = round(100 * count / n)
                bar += f'<div class="seg {k}" style="width:{pct}%">{count}</div>'
        bar += '</div>'
        parts.append(
            f'<tr><td><strong>{esc(display)}</strong>{sub}</td>'
            f'<td>{bar}</td>'
            f'<td>{n}</td></tr>'
        )
    parts.append('</tbody></table>')
    if concept.get("dist_note"):
        parts.append(
            f'<p style="margin-top:10px;font-size:13px;color:var(--ink-mute);font-style:italic">'
            f'{esc(concept["dist_note"])}</p>'
        )
    parts.append('</div>')
    return ''.join(parts)


def _render_finding_card(finding, need):
    verdict = finding["verdict"]
    confidence = finding.get("confidence", "low")
    parts = ['<div class="finding-card">']
    parts.append('<div class="finding-head">')
    display = need_display(need.get("id", ""), need.get("label"), need.get("statement"))
    label = need.get("label") or need.get("statement") or ""
    sub = f' <span style="color:var(--ink-mute);font-weight:400">— {esc(label)}</span>' if label and label != display else ""
    parts.append(
        f'<h4><span class="need-id">{esc(need["id"])}</span>{esc(display)}{sub}</h4>'
    )
    if finding.get("was_targeted"):
        parts.append('<span class="targeted-tag">Designed for</span>')
    parts.append(
        f'<div class="finding-verdict">{render_ball_inline(verdict)}'
        f'<span class="vtext {esc(verdict)}">'
        f'{esc(VERDICT_LONG_LABEL.get(verdict, verdict))} · {esc(confidence)} conf.</span></div>'
    )
    parts.append('</div>')

    if finding.get("reconciliation_note"):
        parts.append(
            f'<div class="reconciliation"><strong>Reconciliation</strong>'
            f'{esc(finding["reconciliation_note"])}</div>'
        )

    for ev in finding.get("evidence", []) or []:
        cls = "pos" if ev.get("polarity") == "positive" else ("neg" if ev.get("polarity") == "negative" else "")
        cls_attr = f' class="{cls}"' if cls else ""
        attr = esc(ev["participant_id"])
        if ev.get("location"):
            attr += f' · {esc(ev["location"])}'
        parts.append(
            f'<blockquote{cls_attr}>"{esc(ev["snippet"])}"'
            f'<span class="attr">— {attr}</span></blockquote>'
        )

    if finding.get("notes"):
        parts.append(f'<p class="finding-notes">{esc(finding["notes"])}</p>')

    parts.append('</div>')
    return ''.join(parts)


def render_method_panel(spec):
    methodology = spec.get("methodology") or {}
    setup = methodology.get("study_setup") or {}

    parts = ['<section class="panel" id="method" role="tabpanel">'
             '<div class="method-grid">']

    # 01 — Study setup
    parts.append('<div class="insight-card">'
                 '<h3><span class="insight-num">01</span>Study setup</h3>')
    if setup.get("format"):
        parts.append(f'<p><strong>Format:</strong> {esc(setup["format"])}</p>')
    if setup.get("sample"):
        parts.append(f'<p><strong>Sample:</strong> {esc(setup["sample"])}</p>')
    if setup.get("concepts_tested"):
        parts.append(f'<p><strong>Concepts tested:</strong> {esc(setup["concepts_tested"])}</p>')
    if setup.get("needs_tested"):
        parts.append(f'<p><strong>Needs tested:</strong> {esc(setup["needs_tested"])}</p>')
    parts.append('</div>')

    # 02 — Verdict definitions
    parts.append('<div class="insight-card">'
                 '<h3><span class="insight-num">02</span>Verdict definitions</h3>'
                 '<dl class="def-list">')
    parts.append(f'<dt>{render_ball_inline("addresses")}Addresses</dt>'
                 '<dd>Concept resolves the need as participants describe it, with consistent reasoning. '
                 '≥3/5 rate "completely" with substantive explanations.</dd>')
    parts.append(f'<dt>{render_ball_inline("partial")}Partial</dt>'
                 '<dd>Concept addresses some aspect of the need but a structural element of the stimulus '
                 'prevents full resolution. Mixed ratings with consistent explanations.</dd>')
    parts.append(f'<dt>{render_ball_inline("doesnt_address")}Doesn\'t address</dt>'
                 '<dd>Concept does not address the need. ≥3/5 rate "not_at_all" with consistent reasoning.</dd>')
    parts.append(f'<dt>{render_ball_inline("creates_new_problem")}Creates new problem</dt>'
                 '<dd>Concept makes the user\'s relationship to the need <em>worse</em>. '
                 'Triggered by even one strong signal — surfaced at any confidence level.</dd>')
    parts.append(f'<dt>{render_ball_inline("insufficient_evidence")}Insufficient evidence</dt>'
                 '<dd>Below the 2-participant minimum for actionable evidence on the cell. '
                 'Not an indictment of the concept; a signal that the cell is under-tested.</dd>')
    parts.append('</dl></div>')

    # 03 — Confidence definitions
    parts.append('<div class="insight-card">'
                 '<h3><span class="insight-num">03</span>Confidence definitions</h3>'
                 '<dl class="def-list">')
    parts.append(f'<dt>{render_pips("high", "pip-row")} High</dt>'
                 '<dd>Consistent signal across ≥4 participants with substantive, non-overlapping explanations. '
                 'Halo-pattern responses excluded.</dd>')
    parts.append(f'<dt>{render_pips("medium", "pip-row")} Medium</dt>'
                 '<dd>Clear majority signal but with one of: small n on the cell, mild contradiction, '
                 'or one halo response that would otherwise tip the count.</dd>')
    parts.append(f'<dt>{render_pips("low", "pip-row")} Low</dt>'
                 '<dd>Single-participant signal, sparse coverage (n≤2), or significant contradiction. '
                 'Reported but not actionable on its own.</dd>')
    parts.append('</dl></div>')

    # 04 — Reconciliation rules
    parts.append('<div class="insight-card">'
                 '<h3><span class="insight-num">04</span>Reconciliation rules</h3>'
                 '<p>Raw ratings are reconciled against participant explanations before a verdict is set. '
                 'The skill applies the following adjustments:</p>'
                 '<ul style="padding-left:18px;color:var(--ink-soft);font-size:13.5px">'
                 '<li><strong>Halo down-weighting:</strong> Participants whose ratings are uniformly positive '
                 'across all cells with vague language have their ratings reduced to directional weight only. '
                 'Detected once at study level rather than re-explained per cell.</li>'
                 '<li><strong>Contradiction logging:</strong> Where rating and explanation conflict, the rating '
                 'stands (it\'s the rated artifact), but the contradiction is flagged in reconciliation.</li>'
                 '<li><strong>Creates-new-problem trigger:</strong> A single strong signal that the concept worsens '
                 'the user\'s relationship to the need is sufficient to flag <em>creates new problem</em>, '
                 'regardless of the majority verdict.</li>'
                 '<li><strong>Sparse-coverage threshold:</strong> Cells rated by fewer than 2 participants are '
                 'surfaced as <em>insufficient evidence</em>, not as a negative verdict.</li>'
                 '</ul></div>')

    # 05 — Study observations (lifted from per-cell reconciliations).
    obs = spec.get("study_observations") or {}
    if obs.get("halo_participants") or obs.get("sparse_coverage") or obs.get("contradictions"):
        parts.append('<div class="insight-card">'
                     '<h3><span class="insight-num">05</span>Study observations</h3>'
                     '<p>Patterns lifted once at study level rather than re-explained per cell. '
                     'These shape how the matrix should be read.</p>')
        for h in obs.get("halo_participants", []) or []:
            parts.append(f'<h4>{esc(h["participant_id"])} halo pattern</h4>')
            parts.append(f'<p>{h.get("rationale","")}</p>')
        for s in obs.get("sparse_coverage", []) or []:
            parts.append(f'<h4>Sparse coverage on {esc(s["concept_id"])}</h4>')
            parts.append(
                f'<p>{esc(s["concept_id"])} was rated by only '
                f'{s.get("n_raters","?")} participants. {s.get("rationale","")}</p>'
            )
        for ct in obs.get("contradictions", []) or []:
            who = esc(ct["participant_id"])
            scope = ct.get("concept_id", "")
            if scope:
                parts.append(f'<h4>{who} contradiction on {esc(scope)}</h4>')
            else:
                parts.append(f'<h4>{who} contradiction</h4>')
            parts.append(f'<p>{ct.get("rationale","")}</p>')
        parts.append('</div>')

    parts.append('</div></section>')
    return ''.join(parts)


def render_footer(spec):
    left = f'Generated {esc(spec.get("date",""))} · /concept-testing'
    right = esc(spec.get("study_subtitle") or "")
    return f'<footer><span>{left}</span><span>{right}</span></footer>'


def cmd_render_html(args):
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    find_index = {(f["concept_id"], f["need_id"]): f for f in spec.get("findings", [])}

    parts = [
        render_doc_head(spec),
        SVG_SYMBOLS,
        '<div class="page">',
        render_masthead(spec),
        render_tabnav(spec),
        render_overview_panel(spec, find_index),
        render_cross_panel(spec, find_index),
    ]
    for concept in spec.get("concepts", []):
        parts.append(render_concept_panel(concept, spec, find_index))
    parts.append(render_method_panel(spec))
    parts.append(render_footer(spec))
    parts.append('</div>')
    parts.append(JS_TABSWITCH)
    parts.append('</body></html>')

    Path(args.out).write_text(''.join(parts), encoding="utf-8")
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("validate", help="validate a ratings CSV against a research plan")
    pv.add_argument("--ratings", required=True)
    pv.add_argument("--plan-json", required=True)
    pv.set_defaults(func=cmd_validate)

    pa = sub.add_parser("aggregate", help="emit per-cell rating distribution + per-concept and study-level metrics")
    pa.add_argument("--ratings", required=True)
    pa.add_argument("--plan-json", required=True)
    pa.add_argument("--out", required=True)
    pa.set_defaults(func=cmd_aggregate)

    pr = sub.add_parser("render-html", help="render a self-contained HTML report from a spec JSON")
    pr.add_argument("--spec", required=True)
    pr.add_argument("--out", required=True)
    pr.set_defaults(func=cmd_render_html)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(json.dumps({"error": str(e), "type": type(e).__name__}), file=sys.stderr)
        sys.exit(2)
