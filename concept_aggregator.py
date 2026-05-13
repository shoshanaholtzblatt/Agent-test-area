#!/usr/bin/env python3
"""
concept_aggregator.py — helper for the /concept-testing skill.

Three subcommands:

  --validate     Verify a ratings CSV is structurally sound against a research plan.
  --aggregate    Emit per-cell rating distribution + per-concept and study-level
                 metrics that feed Phase 4c-4e (study observations, cross-concept
                 synthesis, disposition).
  --render-html  Emit a self-contained HTML report from a spec JSON authored by
                 Claude. Tabbed editorial layout — Overview, Insights, one tab
                 per concept, Methodology. Uses Harvey balls for verdicts and a
                 CSS-custom-property theme system.

Stdlib only. Claude composes the qualitative spec; this helper handles
deterministic CSV arithmetic and HTML/SVG/base64 assembly.
"""

import argparse
import base64
import csv
import html
import json
import mimetypes
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
CONFIDENCE_LABEL = {"high": "high confidence",
                    "medium": "medium confidence",
                    "low": "low confidence"}


# v4: ZERO IDs in display surfaces. Needs and concepts are referenced by name
# in every rendered element. `need.label` is the short name, `need.statement`
# is the longer prose form. The v3 `need_display()` helper has been removed.


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
.matrix-col-head .col-statement { display: block; font-family: var(--mono); font-size: 9px;
                                  color: var(--ink-mute); letter-spacing: 0.04em;
                                  margin-top: 4px; font-weight: 400; text-transform: none;
                                  line-height: 1.4; }
.matrix-row-head { font-family: var(--sans); font-size: 14px; font-weight: 600;
                   color: var(--ink); display: flex; flex-direction: column;
                   justify-content: center; }
.matrix-cell { text-align: center; position: relative; cursor: default; }
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
.concept-name { font-family: var(--serif); font-size: 34px; font-weight: 500;
                line-height: 1.1; letter-spacing: -0.01em; margin: 0 0 14px; }
.concept-desc { font-size: 15px; color: var(--ink-soft); margin-bottom: 22px; max-width: 60ch; }

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

/* Findings */
.finding-card { background: var(--paper); border: 1px solid var(--rule); border-radius: 4px;
                padding: 22px 26px; margin-bottom: 14px; box-shadow: var(--shadow); }
.finding-head { display: flex; align-items: center; flex-wrap: wrap; gap: 14px;
                margin-bottom: 14px; padding-bottom: 14px;
                border-bottom: 1px solid var(--rule-soft); }
.finding-head h4 { margin: 0; color: var(--ink); text-transform: none;
                   letter-spacing: -0.005em; font-size: 16px; font-family: var(--serif);
                   font-weight: 500; flex: 1; }
.finding-head .need-statement { display: block; font-family: var(--mono);
                                font-size: 10.5px; color: var(--ink-mute);
                                letter-spacing: 0.04em; font-weight: 400;
                                margin-top: 3px; text-transform: none; }
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

/* Insights tab — slide-like cards (v4) */
.insight-card { background: var(--paper); border: 1px solid var(--rule); border-radius: 4px;
                padding: 26px 30px; margin-bottom: 18px; box-shadow: var(--shadow); }
.insight-card h3 { margin-top: 0; display: flex; align-items: baseline; gap: 12px; }
.insight-card h3 .insight-num { font-family: var(--mono); font-size: 11px;
                                 color: var(--accent); letter-spacing: 0.1em; font-weight: 500; }
.insight-card p { font-size: 14.5px; }

.insight-slide { background: var(--paper); border: 1px solid var(--rule); border-radius: 4px;
                 padding: 30px 34px; margin-bottom: 22px; box-shadow: var(--shadow); }
.insight-slide .si-eyebrow { font-family: var(--mono); font-size: 10.5px;
                             letter-spacing: 0.18em; text-transform: uppercase;
                             color: var(--accent); margin: 0 0 10px; font-weight: 500; }
.insight-slide .si-finding { font-family: var(--serif); font-size: 24px;
                             font-weight: 500; line-height: 1.25; letter-spacing: -0.005em;
                             color: var(--ink); margin: 0 0 18px;
                             font-variation-settings: "opsz" 32; max-width: 36ch; }
.insight-slide .si-divider { width: 36px; height: 2px; background: var(--accent);
                             margin: 4px 0 16px; }
.insight-slide .si-section-eyebrow { font-family: var(--mono); font-size: 10px;
                                     letter-spacing: 0.14em; text-transform: uppercase;
                                     color: var(--ink-mute); margin: 18px 0 8px;
                                     font-weight: 500; }
.insight-slide .si-evidence { margin: 4px 0 8px; }
.insight-slide .si-evidence .si-ev { font-size: 13.5px; color: var(--ink-soft);
                                     margin: 6px 0; line-height: 1.55;
                                     padding-left: 14px; border-left: 2px solid var(--rule); }
.insight-slide .si-evidence .si-ev .si-ev-attr { font-family: var(--mono); font-size: 10.5px;
                                                 color: var(--ink-mute); letter-spacing: 0.04em;
                                                 margin-right: 6px; }
.insight-slide .si-evidence .si-ev .si-snip { font-family: var(--serif); font-style: italic;
                                              color: var(--ink); }
.insight-slide .si-evidence .si-ev .si-metric { font-family: var(--mono); font-size: 11px;
                                                color: var(--accent); letter-spacing: 0.04em; }
.insight-slide .si-sowhat { font-size: 14.5px; color: var(--ink-soft);
                            margin: 8px 0 18px; line-height: 1.6; }

.insight-recommendation { background: var(--accent-soft); color: var(--paper);
                          border-radius: 4px; padding: 18px 22px; margin-top: 8px; }
.insight-recommendation .ir-eyebrow { font-family: var(--mono); font-size: 10px;
                                      letter-spacing: 0.16em; text-transform: uppercase;
                                      color: var(--paper); opacity: 0.85;
                                      margin: 0 0 6px; font-weight: 500; }
.insight-recommendation .ir-text { font-family: var(--serif); font-size: 15.5px;
                                   line-height: 1.5; color: var(--paper); margin: 0;
                                   font-style: italic; }

/* Overview Key Insights compact cards (no evidence shown) */
.key-insight-grid { display: grid; gap: 14px; margin: 0 0 16px; }
.key-insight-compact { background: var(--paper); border: 1px solid var(--rule);
                       border-radius: 4px; padding: 20px 24px; box-shadow: var(--shadow); }
.key-insight-compact .ki-eyebrow { font-family: var(--mono); font-size: 10px;
                                   letter-spacing: 0.16em; text-transform: uppercase;
                                   color: var(--accent); margin: 0 0 6px; font-weight: 500; }
.key-insight-compact .ki-finding { font-family: var(--serif); font-size: 17px;
                                   font-weight: 500; line-height: 1.35; letter-spacing: -0.005em;
                                   color: var(--ink); margin: 0 0 10px; }
.key-insight-compact .ki-sowhat { font-size: 13.5px; color: var(--ink-soft);
                                  margin: 0 0 10px; line-height: 1.55; }
.key-insight-compact .ki-rec { background: var(--accent-soft); color: var(--paper);
                               border-radius: 3px; padding: 10px 14px; margin-top: 6px; }
.key-insight-compact .ki-rec .ki-rec-eyebrow { font-family: var(--mono); font-size: 9.5px;
                                               letter-spacing: 0.14em; text-transform: uppercase;
                                               color: var(--paper); opacity: 0.85;
                                               margin: 0 0 4px; font-weight: 500; }
.key-insight-compact .ki-rec .ki-rec-text { font-family: var(--serif); font-size: 14px;
                                            line-height: 1.5; color: var(--paper); margin: 0;
                                            font-style: italic; }
.view-all-link { display: inline-block; margin-top: 6px; font-family: var(--mono);
                 font-size: 12px; color: var(--accent); letter-spacing: 0.08em;
                 text-decoration: none; padding: 6px 0;
                 border-bottom: 1px solid var(--accent); }
.view-all-link:hover { color: var(--ink); border-bottom-color: var(--ink); }

/* Concept preview grid on Overview */
.concept-preview-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px;
                        margin: 4px 0 0; }
.concept-preview-card { background: var(--paper); border: 1px solid var(--rule);
                        border-radius: 4px; padding: 0; overflow: hidden;
                        box-shadow: var(--shadow); display: flex; flex-direction: column; }
.concept-preview-card .cpc-thumb { aspect-ratio: 4 / 3; background: var(--bg);
                                   border-bottom: 1px solid var(--rule-soft);
                                   display: flex; align-items: center; justify-content: center;
                                   overflow: hidden; position: relative; }
.concept-preview-card .cpc-thumb img { width: 100%; height: 100%; object-fit: cover;
                                       display: block; }
.concept-preview-card .cpc-thumb .cpc-placeholder { font-family: var(--serif);
                                                    font-style: italic; font-size: 15px;
                                                    color: var(--ink-mute); text-align: center;
                                                    padding: 0 12px; }
.concept-preview-card .cpc-body { padding: 18px 20px 20px; flex: 1;
                                  display: flex; flex-direction: column; }
.concept-preview-card .cpc-name { font-family: var(--serif); font-size: 18px;
                                  font-weight: 500; color: var(--ink); margin: 0 0 8px;
                                  letter-spacing: -0.005em; }
.concept-preview-card .cpc-desc { font-size: 13.5px; color: var(--ink-soft);
                                  margin: 0 0 14px; line-height: 1.55; flex: 1; }
.concept-preview-card .cpc-link { font-family: var(--mono); font-size: 11.5px;
                                  color: var(--accent); letter-spacing: 0.08em;
                                  text-decoration: none; align-self: flex-start;
                                  padding: 6px 0; border-bottom: 1px solid var(--accent); }
.concept-preview-card .cpc-link:hover { color: var(--ink); border-bottom-color: var(--ink); }

/* Concept-tab headline section (top finding + recommendation + confidence) */
.headline-section { margin: 0 0 36px; padding: 24px 0 22px;
                    border-top: 1px solid var(--rule-soft);
                    border-bottom: 1px solid var(--rule-soft); }
.headline-section .hl-eyebrow { font-family: var(--mono); font-size: 10px;
                                letter-spacing: 0.16em; text-transform: uppercase;
                                color: var(--ink-mute); margin: 0 0 6px; font-weight: 500; }
.headline-section .hl-top-finding { font-family: var(--serif); font-style: italic;
                                    font-size: 22px; line-height: 1.35; color: var(--accent);
                                    margin: 0 0 22px; max-width: 50ch;
                                    font-variation-settings: "opsz" 32; }
.headline-section .hl-rec-text { font-family: var(--serif); font-size: 18px;
                                 line-height: 1.45; color: var(--ink); margin: 0 0 10px;
                                 max-width: 60ch; font-variation-settings: "opsz" 24; }
.headline-section .hl-confidence { display: inline-flex; align-items: center; gap: 10px;
                                   font-family: var(--mono); font-size: 11.5px;
                                   color: var(--ink-mute); letter-spacing: 0.05em;
                                   margin-top: 2px; }
.confidence-pips { display: inline-flex; gap: 4px; }
.confidence-pips span { width: 7px; height: 7px; border-radius: 50%;
                        background: var(--ink-mute); opacity: 0.25; }
.confidence-pips span.on { opacity: 1; background: var(--accent); }
.confidence-text { color: var(--ink-soft); }

/* Needs deep dive section */
.needs-deep-dive { margin: 0 0 32px; }
.needs-deep-dive h3 { margin-top: 0; }

/* Recommended refinements */
.recommended-refinements { margin: 0 0 28px; }
.recommended-refinements h3 { margin-top: 0; }
.recommended-refinements ul { margin: 0; padding: 0; list-style: none; }
.recommended-refinements li { padding: 12px 16px; margin-bottom: 8px;
                              background: var(--paper); border: 1px solid var(--rule-soft);
                              border-left: 3px solid var(--accent); border-radius: 3px;
                              font-size: 14.5px; color: var(--ink); line-height: 1.5; }

/* Emergent need on concept tabs */
.emergent-need-card { background: var(--paper); border-left: 3px solid var(--accent);
                      border: 1px solid var(--rule-soft); border-left: 3px solid var(--accent);
                      padding: 20px 24px; margin: 0 0 32px; border-radius: 3px; }
.emergent-need-card.label-emergent .en-eyebrow { font-family: var(--mono); font-size: 10px;
                                                  letter-spacing: 0.16em; text-transform: uppercase;
                                                  color: var(--accent); margin: 0 0 6px;
                                                  font-weight: 500; }
.emergent-need-card .en-label { font-family: var(--serif); font-size: 18px;
                                font-weight: 500; color: var(--ink); margin: 0 0 12px; }
.emergent-need-card .en-quote { margin: 8px 0; padding: 8px 14px; border-left: 2px solid var(--rule);
                                font-style: italic; color: var(--ink-soft); font-size: 14px; }
.emergent-need-card .en-quote .en-attr { display: block; font-style: normal;
                                          font-family: var(--mono); font-size: 11px;
                                          color: var(--ink-mute); margin-top: 4px;
                                          letter-spacing: 0.05em; }

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
  .concept-preview-grid { grid-template-columns: 1fr; }
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
    # is "Insights" per v4 (was "Key Insights" in v3, "Cross-Concept Insights" in v2).
    tabs = [("overview", "Overview"), ("cross", "Insights")]
    for c in spec.get("concepts", []):
        tabs.append((c["id"].lower(), esc(c["name"])))
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
    grid_cols = f'220px repeat({len(needs)}, 1fr)'

    parts = [f'<div class="matrix-wrap"><div class="matrix" style="grid-template-columns: {grid_cols}">']

    # header row — 1 corner + N column heads, each marked .matrix-headrow.
    # v4: column header is the short label (primary) + longer statement
    # (secondary mono line). No IDs.
    parts.append('<div class="matrix-corner matrix-headrow">Concept × Need</div>')
    for need in needs:
        label = need.get("label") or need.get("statement") or ""
        statement = need.get("statement") or ""
        sub_html = ""
        if statement and statement != label:
            sub_html = f'<span class="col-statement">{esc(statement)}</span>'
        parts.append(
            f'<div class="matrix-col-head matrix-headrow">'
            f'{esc(label)}{sub_html}</div>'
        )

    # data rows — concept name only (no ID)
    for concept in concepts:
        parts.append(
            f'<div class="matrix-row-head">{esc(concept["name"])}</div>'
        )
        for need in needs:
            f = find_index.get((concept["id"], need["id"]))
            if not f:
                # blank cell
                parts.append('<div class="matrix-cell"></div>')
                continue
            verdict = f["verdict"]
            confidence = f.get("confidence", "low")
            # v4: NO designed-for accent dot on matrix cells.
            parts.append(
                f'<div class="matrix-cell">'
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
        '<div class="legend-group"><h5>Confidence</h5>'
        f'<div class="legend-item">{render_pips("high", "pip-row")}High (consistent signal across participants)</div>'
        f'<div class="legend-item">{render_pips("medium", "pip-row")}Medium</div>'
        f'<div class="legend-item">{render_pips("low", "pip-row")}Low (sparse or contradictory)</div>'
        '</div>'
        '</div>'
    )


def _insight_recommendation_text(item):
    """v4 StructuredInsight uses `recommendation`; accept v3 `now_what` as fallback."""
    return item.get("recommendation") or item.get("now_what") or ""


def _render_insight_evidence_block(evidence):
    """Render an evidence list (used inside the full slide on Insights tab)."""
    if not evidence:
        return ""
    parts = ['<div class="si-evidence">']
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
    return ''.join(parts)


def _render_insight_slide(item, idx):
    """One slide-like card on the Insights tab.

    Shape:
      insight: str (finding headline)
      evidence: [{snippet?, participant_id?, metric?, source_ref?}]
      so_what: str
      recommendation: str   (v4; v3 specs may carry `now_what` instead)
    """
    parts = ['<div class="insight-slide">']
    parts.append(f'<p class="si-eyebrow">Insight {idx:02d}</p>')
    parts.append(f'<p class="si-finding">{esc(item.get("insight",""))}</p>')
    parts.append('<div class="si-divider"></div>')

    evidence = item.get("evidence") or []
    if evidence:
        parts.append('<p class="si-section-eyebrow">Supporting evidence</p>')
        parts.append(_render_insight_evidence_block(evidence))

    if item.get("so_what"):
        parts.append('<p class="si-section-eyebrow">So what</p>')
        parts.append(f'<p class="si-sowhat">{esc(item["so_what"])}</p>')

    rec = _insight_recommendation_text(item)
    if rec:
        parts.append(
            '<div class="insight-recommendation">'
            '<p class="ir-eyebrow">Recommendation</p>'
            f'<p class="ir-text">{esc(rec)}</p>'
            '</div>'
        )
    parts.append('</div>')
    return ''.join(parts)


def _render_key_insight_compact(item, idx):
    """Compact card for the Overview's Key Insights section — no evidence."""
    parts = ['<div class="key-insight-compact">']
    parts.append(f'<p class="ki-eyebrow">Insight {idx:02d}</p>')
    parts.append(f'<p class="ki-finding">{esc(item.get("insight",""))}</p>')
    if item.get("so_what"):
        parts.append(f'<p class="ki-sowhat">{esc(item["so_what"])}</p>')
    rec = _insight_recommendation_text(item)
    if rec:
        parts.append(
            '<div class="ki-rec">'
            '<p class="ki-rec-eyebrow">Recommendation</p>'
            f'<p class="ki-rec-text">{esc(rec)}</p>'
            '</div>'
        )
    parts.append('</div>')
    return ''.join(parts)


def _collect_insights(spec):
    """Return spec['insights'] in v4 form. Back-compat: synthesize from v3 top_findings + top_recommendations + key_insights.additional_insights when absent."""
    if spec.get("insights"):
        return spec["insights"]
    # v3 fallback: stitch together the legacy lists in priority order.
    out = []
    for it in spec.get("top_findings") or []:
        out.append(it)
    for it in spec.get("top_recommendations") or []:
        out.append(it)
    ki = spec.get("key_insights") or {}
    for it in ki.get("additional_insights") or []:
        out.append(it)
    return out


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
    """v4 Overview order: masthead+takeaway → brief strip → matrix → Key Insights
    section → View all concepts grid → POC."""
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

    # 3. Concept × Need Matrix — MOVED UP. No designed-for accent dot.
    parts.append('<div class="section">'
                 '<div class="section-head"><span class="section-num">§01</span>'
                 '<h2>Concept × Need Matrix</h2></div>')
    parts.append(render_matrix(spec, find_index))
    parts.append('</div>')

    # 4. Key Insights section — compact cards (first 5; no evidence).
    insights = _collect_insights(spec)
    if insights:
        parts.append('<div class="section">'
                     '<div class="section-head"><span class="section-num">§02</span>'
                     '<h2>Key Insights</h2></div>')
        parts.append('<div class="key-insight-grid">')
        for i, it in enumerate(insights[:5], start=1):
            parts.append(_render_key_insight_compact(it, i))
        parts.append('</div>')
        if len(insights) > 5:
            parts.append(
                '<a class="view-all-link" href="#" data-jump="cross">'
                f'View all insights ({len(insights)}) →</a>'
            )
        else:
            parts.append(
                '<a class="view-all-link" href="#" data-jump="cross">'
                'View all insights →</a>'
            )
        parts.append('</div>')

    # 5. View all concepts — preview card grid
    concepts = spec.get("concepts", []) or []
    if concepts:
        parts.append('<div class="section">'
                     '<div class="section-head"><span class="section-num">§03</span>'
                     '<h2>View all concepts</h2></div>')
        parts.append('<div class="concept-preview-grid">')
        for c in concepts:
            parts.append(_render_concept_preview_card(c))
        parts.append('</div>')
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


def _render_concept_preview_card(concept):
    pid = concept["id"].lower()
    si = concept.get("stimulus_image") or {}
    thumb_path = si.get("path")
    placeholder_name = si.get("name") or concept.get("name", "")

    thumb_html = ""
    if thumb_path:
        asset = encode_asset(thumb_path)
        if asset["type"] == "image":
            thumb_html = (
                f'<div class="cpc-thumb">'
                f'<img src="{asset["data_uri"]}" alt="{esc(asset.get("alt", placeholder_name))}"/>'
                f'</div>'
            )
    if not thumb_html:
        thumb_html = (
            '<div class="cpc-thumb">'
            f'<span class="cpc-placeholder">{esc(placeholder_name)}</span>'
            '</div>'
        )

    desc = concept.get("description", "") or ""
    if len(desc) > 120:
        desc = desc[:117].rstrip() + "…"

    return (
        '<div class="concept-preview-card">'
        f'{thumb_html}'
        '<div class="cpc-body">'
        f'<p class="cpc-name">{esc(concept["name"])}</p>'
        f'<p class="cpc-desc">{esc(desc)}</p>'
        f'<a class="cpc-link" href="#" data-jump="{esc(pid)}">View concept →</a>'
        '</div></div>'
    )


def render_cross_panel(spec, find_index):
    """Render the v4 Insights tab as a stack of slide-like cards.

    Panel id `cross` is preserved for back-compat with v2/v3 anchor links;
    button text is now "Insights".
    """
    parts = ['<section class="panel" id="cross" role="tabpanel">']
    insights = _collect_insights(spec)
    if insights:
        for i, item in enumerate(insights, start=1):
            parts.append(_render_insight_slide(item, i))
    else:
        parts.append(
            '<p class="lead">No insights authored for this study.</p>'
        )
    parts.append('</section>')
    return ''.join(parts)


def _concept_recommendation_v4(concept):
    """Return v4-shape `{statement, confidence}` for a concept.

    Back-compat: a v3-shape recommendation with a `verdict` key is reshaped on
    read into `{statement: rationale or label, confidence: "medium"}`. Same
    pattern as the v2→v3 disposition→recommendation transition.
    """
    rec = concept.get("recommendation") or concept.get("disposition")
    if not rec:
        return None
    if "verdict" in rec:
        # v3 shape (or older `disposition`) — coerce
        statement = (rec.get("rationale")
                     or rec.get("statement")
                     or rec.get("label")
                     or "")
        print(
            f"[concept_aggregator] warn: concept {concept.get('id','?')} uses v3 "
            f"recommendation shape with verdict={rec.get('verdict')!r}; falling "
            f"back to {{statement, confidence: 'medium'}} for v4 rendering.",
            file=sys.stderr,
        )
        return {"statement": statement,
                "confidence": rec.get("confidence", "medium")}
    return {"statement": rec.get("statement", ""),
            "confidence": rec.get("confidence", "medium")}


def render_concept_panel(concept, spec, find_index):
    pid = concept["id"].lower()
    parts = [f'<section class="panel" id="{esc(pid)}" role="tabpanel">']

    # 1. Hero (compact) — image + name + description ONLY. No badge, no eyebrow.
    parts.append('<div class="concept-hero">')
    parts.append(_render_concept_image(concept))
    parts.append('<div>')
    parts.append(f'<h2 class="concept-name">{esc(concept["name"])}</h2>')
    parts.append(f'<p class="concept-desc">{esc(concept.get("description",""))}</p>')
    parts.append('</div></div>')

    # 2. Headline section — top_finding + recommendation + confidence
    top_finding = concept.get("top_finding") or concept.get("high_level_finding")
    rec = _concept_recommendation_v4(concept)
    if top_finding or rec:
        parts.append('<div class="headline-section">')
        if top_finding:
            parts.append('<p class="hl-eyebrow">Top finding</p>')
            parts.append(f'<p class="hl-top-finding">{esc(top_finding)}</p>')
        if rec:
            parts.append('<p class="hl-eyebrow">Overall recommendation</p>')
            parts.append(f'<p class="hl-rec-text">{esc(rec["statement"])}</p>')
            conf = rec.get("confidence", "medium")
            parts.append(
                '<div class="hl-confidence">'
                f'{render_pips(conf, "confidence-pips")}'
                f'<span class="confidence-text">· {esc(CONFIDENCE_LABEL.get(conf, conf + " confidence"))}</span>'
                '</div>'
            )
        parts.append('</div>')

    # 3. Rating distribution (kept from v3, displayed before needs deep dive)
    if concept.get("rating_distribution"):
        parts.append(_render_dist_section(concept, spec))

    # 4. Needs deep dive — per-need finding cards
    parts.append('<div class="needs-deep-dive">'
                 '<h3>Needs deep dive</h3>')
    for need in spec["needs"]:
        f = find_index.get((concept["id"], need["id"]))
        if not f:
            continue
        parts.append(_render_finding_card(f, need))
    parts.append('</div>')

    # 5. Emergent need raised during THIS concept's sessions
    this_emergents = _emergents_for_concept(concept, spec)
    if this_emergents:
        for em, evs in this_emergents:
            parts.append('<div class="emergent-need-card label-emergent">')
            parts.append('<p class="en-eyebrow">Emergent need</p>')
            parts.append(f'<p class="en-label">{esc(em["label"])}</p>')
            for ev in evs[:2]:
                parts.append(
                    f'<div class="en-quote">"{esc(ev["snippet"])}"'
                    f'<span class="en-attr">— {esc(ev["participant_id"])}</span></div>'
                )
            parts.append('</div>')

    # 6. Recommended refinements
    refinements = concept.get("recommended_refinements") or []
    if refinements:
        parts.append('<div class="recommended-refinements">'
                     '<h3>Recommended refinements</h3>'
                     '<ul>')
        for r in refinements:
            parts.append(f'<li>{esc(r)}</li>')
        parts.append('</ul></div>')

    parts.append('</section>')
    return ''.join(parts)


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
        label = need.get("label") or need.get("statement") or ""
        statement = need.get("statement") or ""
        sub = ""
        if statement and statement != label:
            sub = f' <span style="color:var(--ink-mute);font-size:12px">{esc(statement)}</span>'
        bar = '<div class="dist-bar">'
        for k in ("completely", "partially", "not_at_all"):
            count = row.get(k, 0)
            if count and n:
                pct = round(100 * count / n)
                bar += f'<div class="seg {k}" style="width:{pct}%">{count}</div>'
        bar += '</div>'
        parts.append(
            f'<tr><td><strong>{esc(label)}</strong>{sub}</td>'
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
    label = need.get("label") or need.get("statement") or ""
    statement = need.get("statement") or ""
    sub = ""
    if statement and statement != label:
        sub = f'<span class="need-statement">{esc(statement)}</span>'
    parts.append(f'<h4>{esc(label)}{sub}</h4>')
    parts.append(
        f'<div class="finding-verdict">{render_ball_inline(verdict)}'
        f'<span class="vtext {esc(verdict)}">'
        f'{esc(VERDICT_LONG_LABEL.get(verdict, verdict))} · {esc(confidence)} confidence</span>'
        f'{render_pips(confidence, "confidence-pips")}'
        f'</div>'
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
