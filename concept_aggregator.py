#!/usr/bin/env python3
"""
concept_aggregator.py — helper for the /concept-testing skill.

Three subcommands:

  --validate     Verify a ratings CSV is structurally sound against a research plan.
  --aggregate    Emit per-cell rating distribution JSON for Claude to reconcile.
  --render-html  Emit a self-contained HTML report from a spec JSON authored by Claude.

Stdlib only — mirrors the constraint of sum_calculator.py.

The Python side handles deterministic CSV parsing/arithmetic and HTML/SVG/base64
assembly (kept out of the LLM token stream). Claude parses the markdown research
plan and authors qualitative judgments into the spec JSON.
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
    "doesn't_address",
    "creates_new_problem",
    "insufficient_evidence",
)
CONFIDENCES = ("high", "medium", "low")


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
                "concept_id": (row["concept_id"] or "").strip(),
                "need_id": (row["need_id"] or "").strip(),
                "rating": (row["rating"] or "").strip(),
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

    out = {
        "study_name": plan.get("study_name"),
        "concept_ids": concept_ids,
        "need_ids": need_ids,
        "participants": sorted({r["participant"] for r in rows}),
        "cells": cells,
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# Render HTML
# ---------------------------------------------------------------------------

VERDICT_STYLE = {
    "addresses":            {"fill": "#2e7d32", "text": "#ffffff", "glyph": "",  "label": "addresses"},
    "partial":              {"fill": "#f9a825", "text": "#1a1a1a", "glyph": "",  "label": "partial"},
    "doesn't_address":      {"fill": "#c62828", "text": "#ffffff", "glyph": "",  "label": "doesn't address"},
    "creates_new_problem":  {"fill": "#7f0000", "text": "#ffffff", "glyph": "!", "label": "creates new problem"},
    "insufficient_evidence":{"fill": "#9e9e9e", "text": "#ffffff", "glyph": "?", "label": "insufficient evidence"},
}


def encode_asset(path_or_text):
    """Return an inline-renderable representation of a concept asset.
    Returns a dict: {type: 'image', data_uri: ...} or {type: 'text', value: ...}."""
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


def esc(s):
    return html.escape(s if s is not None else "", quote=True)


def render_legend():
    items = []
    for v in VERDICTS:
        s = VERDICT_STYLE[v]
        glyph = f' <span class="cell-glyph">{s["glyph"]}</span>' if s["glyph"] else ""
        items.append(
            f'<span class="legend-swatch" style="background:{s["fill"]};color:{s["text"]}">'
            f'{esc(s["label"])}{glyph}</span>'
        )
    return (
        '<div class="legend">'
        '<strong>Verdict:</strong> ' + ' '.join(items) +
        ' &nbsp;<strong>Confidence:</strong> '
        '<span class="conf-dot conf-high"></span> high '
        '<span class="conf-dot conf-medium"></span> medium '
        '<span class="conf-dot conf-low"></span> low '
        '&nbsp;<strong>Border:</strong> thick = concept was designed for this need'
        '</div>'
    )


def render_matrix(spec, find_index):
    needs = spec["needs"]
    concepts = spec["concepts"]
    cell_w, cell_h = 96, 64
    label_h = 140
    label_w = 180
    width = label_w + len(needs) * cell_w + 40
    height = label_h + len(concepts) * cell_h + 40

    parts = [f'<svg viewBox="0 0 {width} {height}" '
             f'width="{width}" height="{height}" '
             'xmlns="http://www.w3.org/2000/svg" class="matrix-svg" '
             'role="img" aria-label="Concept by need verdict matrix">']

    # diagonal-stripe pattern for insufficient_evidence
    parts.append(
        '<defs>'
        '<pattern id="stripe" patternUnits="userSpaceOnUse" width="8" height="8" '
        'patternTransform="rotate(45)">'
        '<rect width="8" height="8" fill="#9e9e9e"/>'
        '<line x1="0" y1="0" x2="0" y2="8" stroke="#bdbdbd" stroke-width="3"/>'
        '</pattern>'
        '</defs>'
    )

    # column headers (need labels, rotated)
    for j, need in enumerate(needs):
        x = label_w + j * cell_w + cell_w / 2
        y = label_h - 8
        label = need.get("label") or need.get("statement") or need["id"]
        parts.append(
            f'<text x="{x}" y="{y}" transform="rotate(-45 {x} {y})" '
            f'class="matrix-col-label" text-anchor="start">'
            f'{esc(need["id"])}: {esc(label[:40])}</text>'
        )

    # row labels + cells
    for i, concept in enumerate(concepts):
        cy = label_h + i * cell_h
        # row label
        parts.append(
            f'<text x="{label_w - 12}" y="{cy + cell_h/2 + 5}" '
            f'class="matrix-row-label" text-anchor="end">'
            f'{esc(concept["id"])}: {esc(concept["name"][:24])}</text>'
        )
        for j, need in enumerate(needs):
            cx = label_w + j * cell_w
            finding = find_index.get((concept["id"], need["id"]))
            if not finding:
                fill = "#eeeeee"; tcolor = "#666"; glyph = ""; verdict_label = "—"; conf_class = ""
                quote_preview = ""
                was_targeted = False
            else:
                v = finding["verdict"]
                style = VERDICT_STYLE.get(v, VERDICT_STYLE["insufficient_evidence"])
                fill = style["fill"] if v != "insufficient_evidence" else "url(#stripe)"
                tcolor = style["text"]
                glyph = style["glyph"]
                verdict_label = style["label"]
                conf_class = "conf-" + finding.get("confidence", "low")
                ev = finding.get("evidence") or []
                quote_preview = ev[0]["snippet"] if ev else ""
                was_targeted = finding.get("was_targeted", False)

            border_w = 3 if was_targeted else 1
            border_c = "#1a1a1a" if was_targeted else "#cccccc"
            anchor_id = f'cell-{concept["id"]}-{need["id"]}'

            tooltip = f'{verdict_label}'
            if quote_preview:
                tooltip += f' — "{quote_preview[:140]}"'

            parts.append(f'<a href="#{anchor_id}">')
            parts.append(
                f'<rect x="{cx}" y="{cy}" width="{cell_w}" height="{cell_h}" '
                f'fill="{fill}" stroke="{border_c}" stroke-width="{border_w}">'
                f'<title>{esc(tooltip)}</title>'
                f'</rect>'
            )
            if glyph:
                parts.append(
                    f'<text x="{cx + cell_w/2}" y="{cy + cell_h/2 + 8}" '
                    f'fill="{tcolor}" class="cell-glyph-svg" text-anchor="middle">'
                    f'{esc(glyph)}</text>'
                )
            # confidence dot
            if finding:
                cdx = cx + cell_w - 10
                cdy = cy + 10
                if finding.get("confidence") == "high":
                    parts.append(f'<circle cx="{cdx}" cy="{cdy}" r="4" fill="#1a1a1a"/>')
                elif finding.get("confidence") == "medium":
                    parts.append(f'<circle cx="{cdx}" cy="{cdy}" r="4" fill="#1a1a1a" fill-opacity="0.4"/>')
                else:
                    parts.append(f'<circle cx="{cdx}" cy="{cdy}" r="4" fill="none" stroke="#1a1a1a" stroke-width="1.5"/>')
            parts.append('</a>')

    parts.append('</svg>')
    return "".join(parts)


def render_concept_article(concept, spec, find_index):
    nid_to_need = {n["id"]: n for n in spec["needs"]}
    asset = encode_asset(concept.get("asset_path") or
                         (concept.get("assets")[0] if concept.get("assets") else ""))

    out = [f'<article class="concept" id="concept-{esc(concept["id"])}">']
    out.append(f'<h3>{esc(concept["id"])}: {esc(concept["name"])}</h3>')
    out.append(f'<p class="concept-description">{esc(concept.get("description",""))}</p>')

    if asset["type"] == "image":
        out.append(f'<figure><img src="{asset["data_uri"]}" alt="{esc(asset.get("alt",""))}"/></figure>')
    elif asset.get("value"):
        out.append(f'<figure class="text-asset"><pre>{esc(asset["value"])}</pre></figure>')

    # rating distribution
    if "rating_distribution" in concept:
        out.append('<h4>Rating distribution</h4>')
        out.append('<table class="dist"><thead><tr>'
                   '<th>need</th><th>completely</th><th>partially</th>'
                   '<th>not_at_all</th><th>n</th></tr></thead><tbody>')
        for row in concept["rating_distribution"]:
            need = nid_to_need.get(row["need_id"], {})
            need_label = need.get("label") or need.get("statement") or row["need_id"]
            out.append(
                f'<tr><td>{esc(row["need_id"])}: {esc(need_label[:60])}</td>'
                f'<td>{row["completely"]}</td><td>{row["partially"]}</td>'
                f'<td>{row["not_at_all"]}</td><td>{row["n"]}</td></tr>'
            )
        out.append('</tbody></table>')

    # past-use synthesis
    if concept.get("past_use_synthesis"):
        out.append('<h4>Past-use story synthesis</h4>')
        out.append(f'<p>{esc(concept["past_use_synthesis"])}</p>')
    for q in concept.get("past_use_quotes", []) or []:
        out.append(
            f'<blockquote>"{esc(q["snippet"])}" '
            f'<span class="attribution">— {esc(q["participant_id"])}</span></blockquote>'
        )

    # aspects
    if concept.get("aspects"):
        out.append('<h4>Aspects</h4><ul class="aspects">')
        for a in concept["aspects"]:
            out.append(
                f'<li><strong>{esc(a["label"])}</strong> '
                f'<span class="aspect-direction aspect-{esc(a["direction"])}">'
                f'driver-{esc(a["direction"])}</span> '
                f'<span class="aspect-count">cited by {a["count"]}</span></li>'
            )
        out.append('</ul>')

    # per-need findings
    out.append('<h4>Per-need findings</h4>')
    for need in spec["needs"]:
        finding = find_index.get((concept["id"], need["id"]))
        if not finding:
            continue
        verdict = finding["verdict"]
        style = VERDICT_STYLE.get(verdict, VERDICT_STYLE["insufficient_evidence"])
        anchor_id = f'cell-{concept["id"]}-{need["id"]}'
        target_marker = ' <span class="targeted">(designed for)</span>' if finding.get("was_targeted") else ""

        out.append(f'<div class="finding" id="{anchor_id}">')
        need_label = need.get("label") or need.get("statement") or need["id"]
        out.append(
            f'<h5>{esc(need["id"])}: {esc(need_label)}{target_marker}</h5>'
        )
        out.append(
            f'<p class="verdict-line">'
            f'<span class="verdict verdict-{esc(verdict)}" '
            f'style="background:{style["fill"]};color:{style["text"]}">'
            f'{esc(style["label"])}</span> '
            f'<span class="confidence-tag conf-{esc(finding["confidence"])}">'
            f'confidence: {esc(finding["confidence"])}</span>'
            f'</p>'
        )
        if finding.get("reconciliation_note"):
            out.append(f'<p class="reconciliation"><em>Reconciliation:</em> '
                       f'{esc(finding["reconciliation_note"])}</p>')
        for ev in finding.get("evidence", []) or []:
            polarity_cls = f"polarity-{esc(ev.get('polarity','neutral'))}"
            out.append(
                f'<blockquote class="{polarity_cls}">"{esc(ev["snippet"])}" '
                f'<span class="attribution">— {esc(ev["participant_id"])}'
                + (f' · {esc(ev["location"])}' if ev.get("location") else "")
                + '</span></blockquote>'
            )
        if finding.get("notes"):
            out.append(f'<p class="finding-notes">{esc(finding["notes"])}</p>')
        out.append('</div>')

    out.append('</article>')
    return "".join(out)


def render_emergent(spec):
    if not spec.get("emergent_needs"):
        return ""
    out = ['<section id="emergent"><h2>Emergent needs</h2>',
           '<p class="section-intro">Needs surfaced in past-use stories that the '
           'research plan did not anticipate.</p>']
    for em in spec["emergent_needs"]:
        out.append('<div class="emergent-need">')
        out.append(f'<h3>{esc(em["label"])}</h3>')
        out.append(
            f'<p class="confidence-line">'
            f'<span class="confidence-tag conf-{esc(em["confidence"])}">'
            f'confidence: {esc(em["confidence"])}</span> '
            f'<em>{esc(em.get("confidence_note",""))}</em></p>'
        )
        for ev in em.get("evidence", []) or []:
            out.append(
                f'<blockquote>"{esc(ev["snippet"])}" '
                f'<span class="attribution">— {esc(ev["participant_id"])}</span></blockquote>'
            )
        if em.get("addressed_by"):
            out.append('<p><strong>Concepts that addressed it:</strong> '
                       + ", ".join(esc(c) for c in em["addressed_by"]) + '</p>')
        if em.get("missed_by"):
            out.append('<p><strong>Concepts that missed it:</strong> '
                       + ", ".join(esc(c) for c in em["missed_by"]) + '</p>')
        out.append('</div>')
    out.append('</section>')
    return "".join(out)


def render_gap(spec, find_index):
    missed = []
    surprises = []
    for c in spec["concepts"]:
        for n in spec["needs"]:
            f = find_index.get((c["id"], n["id"]))
            if not f:
                continue
            if f.get("was_targeted") and f["verdict"] in {"partial", "doesn't_address", "creates_new_problem"}:
                missed.append((c, n, f))
            if not f.get("was_targeted") and f["verdict"] == "addresses":
                surprises.append((c, n, f))

    if not missed and not surprises:
        return ""

    out = ['<section id="gap"><h2>Designed-vs-actual gap</h2>']

    out.append('<h3>Designed but missed</h3>')
    if missed:
        out.append('<ul>')
        for c, n, f in missed:
            anchor = f'cell-{c["id"]}-{n["id"]}'
            need_label = n.get("label") or n.get("statement") or n["id"]
            out.append(
                f'<li><a href="#{anchor}"><strong>{esc(c["id"])} → {esc(n["id"])}</strong></a>: '
                f'{esc(c["name"])} was designed to address "{esc(need_label[:80])}" '
                f'but verdict is <em>{esc(VERDICT_STYLE[f["verdict"]]["label"])}</em>.</li>'
            )
        out.append('</ul>')
    else:
        out.append('<p><em>No designed-but-missed cells.</em></p>')

    out.append('<h3>Good surprises</h3>')
    if surprises:
        out.append('<ul>')
        for c, n, f in surprises:
            anchor = f'cell-{c["id"]}-{n["id"]}'
            need_label = n.get("label") or n.get("statement") or n["id"]
            out.append(
                f'<li><a href="#{anchor}"><strong>{esc(c["id"])} → {esc(n["id"])}</strong></a>: '
                f'{esc(c["name"])} addresses "{esc(need_label[:80])}" '
                f'even though it was not designed to.</li>'
            )
        out.append('</ul>')
    else:
        out.append('<p><em>No good-surprise cells.</em></p>')

    out.append('</section>')
    return "".join(out)


CSS = """
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       max-width: 1100px; margin: 2em auto; padding: 0 2em; color: #1a1a1a;
       line-height: 1.5; }
h1 { font-size: 1.8em; margin-bottom: 0.2em; }
h2 { border-bottom: 2px solid #1a1a1a; padding-bottom: 0.3em; margin-top: 2em; }
h3 { margin-top: 1.6em; }
.meta { color: #666; font-size: 0.9em; }
.section-intro { color: #555; font-size: 0.95em; }
#matrix { overflow-x: auto; padding: 1em 0; }
.matrix-svg { display: block; }
.matrix-col-label, .matrix-row-label { font-size: 12px; fill: #1a1a1a; }
.cell-glyph-svg { font-size: 22px; font-weight: bold; }
.legend { font-size: 0.85em; color: #333; margin-top: 0.6em;
          padding: 0.6em; background: #f5f5f5; border-radius: 4px; }
.legend-swatch { display: inline-block; padding: 2px 8px; border-radius: 3px;
                 margin: 0 4px; font-weight: 500; }
.cell-glyph { font-weight: bold; }
.conf-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%;
            margin: 0 2px; vertical-align: middle; }
.conf-high { background: #1a1a1a; }
.conf-medium { background: #1a1a1a; opacity: 0.4; }
.conf-low { background: transparent; border: 1.5px solid #1a1a1a; }
article.concept { border: 1px solid #ddd; border-radius: 6px;
                  padding: 1.2em 1.5em; margin: 1.5em 0; background: #fafafa; }
article.concept figure { margin: 0.8em 0; }
article.concept figure img { max-width: 100%; border-radius: 4px; }
.text-asset pre { white-space: pre-wrap; background: #f0f0f0; padding: 0.8em;
                  border-radius: 4px; font-family: inherit; }
table.dist { border-collapse: collapse; font-size: 0.9em; margin: 0.6em 0; }
table.dist th, table.dist td { padding: 4px 10px; border: 1px solid #ddd;
                                text-align: left; }
table.dist th { background: #efefef; }
ul.aspects { list-style: none; padding-left: 0; }
ul.aspects li { padding: 4px 0; }
.aspect-direction { font-size: 0.8em; padding: 1px 6px; border-radius: 3px;
                     margin: 0 4px; }
.aspect-up { background: #c8e6c9; }
.aspect-down { background: #ffcdd2; }
.aspect-mixed { background: #fff9c4; }
.aspect-count { color: #666; font-size: 0.85em; }
.finding { border-left: 3px solid #ddd; padding: 0.4em 1em; margin: 0.8em 0; }
.finding h5 { margin: 0.2em 0; font-size: 1em; }
.targeted { color: #555; font-weight: normal; font-size: 0.85em; }
.verdict { display: inline-block; padding: 2px 8px; border-radius: 3px;
           font-weight: 500; font-size: 0.9em; }
.confidence-tag { font-size: 0.8em; padding: 2px 6px; border-radius: 3px;
                   margin-left: 6px; background: #e0e0e0; }
.confidence-tag.conf-high { background: #c8e6c9; }
.confidence-tag.conf-medium { background: #fff9c4; }
.confidence-tag.conf-low { background: #ffcdd2; }
.reconciliation { color: #555; font-size: 0.9em; }
blockquote { border-left: 3px solid #bbb; margin: 0.4em 0; padding: 0.2em 0.8em;
              font-style: italic; color: #333; }
blockquote.polarity-positive { border-left-color: #2e7d32; }
blockquote.polarity-negative { border-left-color: #c62828; }
blockquote .attribution { font-style: normal; color: #666; font-size: 0.85em; }
.finding-notes { color: #444; font-size: 0.95em; }
footer { color: #888; font-size: 0.8em; margin-top: 3em; padding-top: 1em;
         border-top: 1px solid #ddd; }
.emergent-need { padding: 0.6em 0; }
"""


def cmd_render_html(args):
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))

    findings = spec.get("findings", [])
    find_index = {(f["concept_id"], f["need_id"]): f for f in findings}

    parts = ['<!DOCTYPE html><html lang="en"><head>',
             '<meta charset="utf-8">',
             f'<title>Concept Testing — {esc(spec.get("study_name","Report"))}</title>',
             f'<style>{CSS}</style>',
             '</head><body>',
             '<header>',
             f'<h1>Concept Testing — {esc(spec.get("study_name","Report"))}</h1>',
             f'<p class="meta">{esc(spec.get("date",""))} · '
             f'{len(spec.get("participants",[]))} participants · '
             f'{len(spec.get("concepts",[]))} concepts × '
             f'{len(spec.get("needs",[]))} needs</p>',
             '</header>']

    parts.append('<section id="matrix"><h2>Verdict matrix</h2>')
    parts.append(render_matrix(spec, find_index))
    parts.append(render_legend())
    parts.append('</section>')

    parts.append(render_gap(spec, find_index))
    parts.append(render_emergent(spec))

    parts.append('<section id="concepts"><h2>Per-concept deep dives</h2>')
    for concept in spec.get("concepts", []):
        parts.append(render_concept_article(concept, spec, find_index))
    parts.append('</section>')

    if spec.get("cross_cutting"):
        parts.append('<section id="cross"><h2>Cross-cutting observations</h2>')
        parts.append(f'<p>{esc(spec["cross_cutting"])}</p>')
        parts.append('</section>')

    parts.append(f'<footer>Generated {esc(spec.get("date",""))} '
                 'by /concept-testing</footer>')
    parts.append('</body></html>')

    Path(args.out).write_text("".join(parts), encoding="utf-8")
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

    pa = sub.add_parser("aggregate", help="emit per-cell rating distribution JSON")
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
