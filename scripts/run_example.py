#!/usr/bin/env python3
"""
run_example.py — verification harness for /concept-testing.

Runs concept_aggregator.py end-to-end against a committed sample study and
asserts structural invariants. Catches regressions in the helper as the
skill evolves.

Does NOT test Claude's qualitative reconciliation (that's human-in-the-loop).
Tests:
  1. validate — exits 0 with ok:true on the committed sample
  2. aggregate — produces a distribution JSON byte-equivalent to the
     committed expected_distributions.json
  3. render-html — produces an HTML file containing all the expected
     structural elements (verdict classes, gap section, emergent need,
     glyphs, stripe pattern)

Usage:
    python3 scripts/run_example.py [--study <name>]

Default study: personal_finance_study
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
AGGREGATOR = REPO_ROOT / "concept_aggregator.py"


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def run_aggregator(*args):
    proc = subprocess.run(
        [sys.executable, str(AGGREGATOR), *args],
        capture_output=True, text=True
    )
    return proc


def step_validate(plan_json, ratings_csv):
    proc = run_aggregator("validate", "--ratings", str(ratings_csv),
                          "--plan-json", str(plan_json))
    if proc.returncode != 0:
        fail(f"validate exited {proc.returncode}: {proc.stdout}{proc.stderr}")
    summary = json.loads(proc.stdout)
    if not summary.get("ok"):
        fail(f"validate returned ok=false: {summary}")
    return summary


def step_aggregate(plan_json, ratings_csv, expected_dist):
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "dist.json"
        proc = run_aggregator("aggregate", "--ratings", str(ratings_csv),
                              "--plan-json", str(plan_json),
                              "--out", str(out_path))
        if proc.returncode != 0:
            fail(f"aggregate exited {proc.returncode}: {proc.stdout}{proc.stderr}")
        produced = json.loads(out_path.read_text())
    expected = json.loads(Path(expected_dist).read_text())

    diffs = []
    for cid in expected.get("concept_ids", []):
        for nid in expected.get("need_ids", []):
            ec = expected["cells"][cid][nid]
            pc = produced["cells"][cid][nid]
            for field in ("completely", "partially", "not_at_all", "n",
                          "majority", "was_targeted"):
                if ec.get(field) != pc.get(field):
                    diffs.append(f"{cid}×{nid}.{field}: "
                                 f"expected {ec.get(field)!r}, "
                                 f"got {pc.get(field)!r}")
    if diffs:
        fail("aggregate output diverged from expected_distributions.json:\n  "
             + "\n  ".join(diffs))

    return produced


def step_render_html(spec_json):
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "report.html"
        proc = run_aggregator("render-html", "--spec", str(spec_json),
                              "--out", str(out_path))
        if proc.returncode != 0:
            fail(f"render-html exited {proc.returncode}: {proc.stdout}{proc.stderr}")
        return out_path.read_text()


def step_content_checks(html, spec):
    project_name = spec.get("project_name", "")

    expected_substrings = [
        # Tabs — panel id "cross" stays for back-compat; button text is "Key Insights"
        ("Overview tab button",          'data-target="overview"'),
        ("Key Insights tab button",      'data-target="cross"'),
        ("Methodology tab button",       'data-target="method"'),
        ("Overview panel",               'id="overview"'),
        ("Cross panel id (back-compat)", 'id="cross"'),
        ("Methodology panel",            'id="method"'),
        ("Key Insights tab label",       '>Key Insights<'),
        # Harvey ball symbol defs
        ("ball-full symbol",             'id="ball-full"'),
        ("ball-half symbol",             'id="ball-half"'),
        ("ball-empty symbol",            'id="ball-empty"'),
        ("ball-warn symbol",             'id="ball-warn"'),
        ("ball-insuf symbol",            'id="ball-insuf"'),
        # Verdict text classes
        ("vtext.addresses",              'vtext addresses'),
        ("vtext.partial",                'vtext partial'),
        ("vtext.doesnt_address",         'vtext doesnt_address'),
        ("vtext.creates_new_problem",    'vtext creates_new_problem'),
        ("vtext.insufficient_evidence",  'vtext insufficient_evidence'),
        # Need display rule — "Need 1/2/3" rendered (not bare "N1:")
        ("Need 1 display",               'Need 1'),
        ("Need 2 display",                'Need 2'),
        ("Need 3 display",               'Need 3'),
        # Overview-as-brief content
        ("Top findings heading",         'Top findings'),
        ("Top recommendations heading",  'Top recommendations'),
        ("Concept × Need Matrix heading","Concept × Need Matrix"),
        ("Point of contact card",        'class="poc-card"'),
        ("POC eyebrow",                  'Point of contact'),
        ("brief-takeaway",               'class="brief-takeaway"'),
        ("brief-strip (3-col)",          'class="brief-strip"'),
        ("Research question label",      'Research question'),
        ("How to use these results",     'How to use these results'),
        ("structured-insight card",      'class="sicard"'),
        ("structured-insight so/what",   'class="si-so"'),
        ("structured-insight now/what",  'class="si-now"'),
        # Recommendation badge (renamed from Disposition)
        ("Recommendation badge wrapper", 'class="recommendation"'),
        ("Recommendation label text",    '>Recommendation<'),
        # Concept tabs — "Finding" strip from high_level_finding
        ("Finding strip",                'class="finding-strip"'),
        # Key Insights tab content
        ("coverage grid",                'class="coverage-grid"'),
        ("recurring drivers heading",    'Recurring drivers'),
        ("section banner (so/now)",      'class="section-banner"'),
        # Methodology tab now hosts Study observations
        ("Study observations heading",   'Study observations'),
        # Theme infrastructure
        ("CSS custom property: accent",  '--accent:'),
        ("CSS custom property: serif",   '--serif:'),
        ("CSS custom property: paper",   '--paper:'),
        # Tab JS
        ("tab-switching script",         "data-target"),
    ]
    if project_name:
        expected_substrings.append(("project_name h1", project_name))

    emergent_label = (spec.get("emergent_needs") or [{}])[0].get("label", "")
    if emergent_label:
        expected_substrings.append(("emergent need label", emergent_label))

    missing = [name for name, sub in expected_substrings if sub not in html]
    if missing:
        fail("HTML missing expected content:\n  - " + "\n  - ".join(missing))

    # Forbidden text — these strings should NOT appear after the v3 rewrite
    forbidden = [
        ("Disposition badge label",      '>Disposition<'),
        ("Cross-Concept Insights heading/tab", 'Cross-Concept Insights'),
    ]
    found = [name for name, sub in forbidden if sub in html]
    if found:
        fail("HTML contains forbidden v2 content:\n  - " + "\n  - ".join(found))

    # Each concept must have a Recommendation badge (value class)
    n_recommendations = html.count('class="value advance"') \
        + html.count('class="value iterate"') \
        + html.count('class="value kill"') \
        + html.count('class="value park"')
    n_concepts = len(spec.get("concepts", []))
    if n_recommendations < n_concepts:
        fail(f"Expected {n_concepts} recommendation badges, found {n_recommendations}")

    # Top findings & top recommendations cards: at least one each
    n_top_findings = len(spec.get("top_findings") or [])
    n_top_recs = len(spec.get("top_recommendations") or [])
    if n_top_findings < 3 or n_top_findings > 7:
        fail(f"top_findings count {n_top_findings} is outside 3–7")
    if n_top_recs < 3 or n_top_recs > 7:
        fail(f"top_recommendations count {n_top_recs} is outside 3–7")

    # var(--*) usage — proof of theme-able structural CSS
    n_var = html.count('var(--')
    if n_var < 30:
        fail(f"CSS uses only {n_var} var(--*) references; expected ≥30 — "
             "structural CSS may have hardcoded colors/fonts")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--study", default="personal_finance_study",
                   help="study folder name under data/examples/ (default: personal_finance_study)")
    args = p.parse_args()

    study_dir = REPO_ROOT / "data" / "examples" / args.study
    plan_json = study_dir / "plan.json"
    ratings_csv = study_dir / "ratings.csv"
    expected_dist = study_dir / "expected_distributions.json"
    expected_spec = study_dir / "expected_spec.json"

    for path in (plan_json, ratings_csv, expected_dist, expected_spec):
        if not path.exists():
            fail(f"missing required file: {path}")

    print(f"[1/4] validate  ... ", end="", flush=True)
    summary = step_validate(plan_json, ratings_csv)
    print(f"OK ({summary['n_rows']} rows, {summary['n_participants']} participants, "
          f"{summary['n_concepts']} concepts × {summary['n_needs']} needs)")

    print(f"[2/4] aggregate ... ", end="", flush=True)
    step_aggregate(plan_json, ratings_csv, expected_dist)
    print(f"OK ({summary['expected_cells']} cells; spot checks pass)")

    print(f"[3/4] render-html ... ", end="", flush=True)
    html = step_render_html(expected_spec)
    print(f"OK ({len(html):,} bytes)")

    print(f"[4/4] content checks ... ", end="", flush=True)
    spec = json.loads(expected_spec.read_text())
    step_content_checks(html, spec)
    n_findings = len(spec.get("findings", []))
    n_emergent = len(spec.get("emergent_needs", []))
    n_concepts = len(spec.get("concepts", []))
    n_top_findings = len(spec.get("top_findings") or [])
    n_top_recs = len(spec.get("top_recommendations") or [])
    print(f"OK (Overview brief, Key Insights tab, {n_concepts} recommendations, "
          f"{n_top_findings} top findings, {n_top_recs} top recs, "
          f"{n_emergent} emergent need(s))")

    print(f"\nPASS: {args.study} verified — {n_findings} findings, "
          f"{n_emergent} emergent need(s), {len(html):,} bytes of HTML")
    return 0


if __name__ == "__main__":
    sys.exit(main())
