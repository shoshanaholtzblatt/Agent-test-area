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
    expected_substrings = [
        ("verdict-addresses class",         'verdict-addresses'),
        ("verdict-partial class",           'verdict-partial'),
        ("verdict-doesn't_address class",   "verdict-doesn&#x27;t_address"),
        ("verdict-creates_new_problem class", 'verdict-creates_new_problem'),
        ("verdict-insufficient_evidence class", 'verdict-insufficient_evidence'),
        ("Designed but missed section",     'Designed but missed'),
        ("Good surprises section",          'Good surprises'),
        ("emergent-needs section heading",  'Emergent needs'),
        ("creates_new_problem ! glyph",     '>!<'),
        ("insufficient_evidence stripe pattern", 'id="stripe"'),
    ]
    emergent_label = (spec.get("emergent_needs") or [{}])[0].get("label", "")
    if emergent_label:
        expected_substrings.append(("emergent need label",
                                    f">{emergent_label}<"))

    missing = [name for name, sub in expected_substrings if sub not in html]
    if missing:
        fail("HTML missing expected content:\n  - " + "\n  - ".join(missing))

    has_designed_missed_entry = ("Designed but missed</h3><ul>" in html)
    has_good_surprise_entry = ("Good surprises</h3><ul>" in html)
    if not has_designed_missed_entry:
        fail("HTML 'Designed but missed' section is empty (expected at least one entry)")
    if not has_good_surprise_entry:
        fail("HTML 'Good surprises' section is empty (expected at least one entry)")


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
    print(f"OK (5 verdict classes, gap section, {n_emergent} emergent need(s), glyphs)")

    print(f"\nPASS: {args.study} verified — {n_findings} findings, "
          f"{n_emergent} emergent need(s), {len(html):,} bytes of HTML")
    return 0


if __name__ == "__main__":
    sys.exit(main())
