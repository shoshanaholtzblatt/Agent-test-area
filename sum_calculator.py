#!/usr/bin/env python3
"""
SUM (Single Usability Metric) calculator — Jeff Sauro / MeasuringUsability.com methodology.

Reads a CSV with columns: task, participant, completion, ease, satisfaction, perception, time_s
Outputs JSON results followed by "---JSON-END---" then a markdown summary table.

Usage:
    python3 sum_calculator.py --csv /path/to/data.csv [--alpha 0.10]
"""

import argparse
import csv
import json
import math
import sys
from collections import defaultdict


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def normal_cdf(z):
    """Cumulative distribution function of the standard normal distribution."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def percentile_inc(values, p):
    """
    Excel PERCENTILE / PERCENTILE.INC equivalent (inclusive method).
    rank = 1 + p * (n - 1), 1-based, linearly interpolated.
    Matches the formula =PERCENTILE(range, p) used in SUMv5.xls.
    """
    n = len(values)
    if n == 0:
        raise ValueError("Cannot compute percentile of empty list.")
    sorted_v = sorted(values)
    rank = 1 + p * (n - 1)  # 1-based
    lo = int(math.floor(rank))
    hi = lo + 1
    frac = rank - lo
    lo_val = sorted_v[lo - 1] if lo >= 1 else sorted_v[0]
    hi_val = sorted_v[hi - 1] if hi <= n else sorted_v[n - 1]
    return lo_val + frac * (hi_val - lo_val)


def sample_mean(values):
    return sum(values) / len(values)


def sample_stdev(values):
    """Sample standard deviation (N-1 denominator)."""
    n = len(values)
    if n < 2:
        return 0.0
    m = sample_mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / (n - 1))


def probit(p):
    """Inverse normal CDF via Abramowitz & Stegun 26.2.16 rational approximation."""
    if p >= 1.0:
        return float("inf")
    if p <= 0.0:
        return float("-inf")
    if p > 0.5:
        return -probit(1.0 - p)
    t = math.sqrt(-2.0 * math.log(p))
    num = 2.515517 + 0.802853 * t + 0.010328 * t * t
    den = 1.0 + 1.432788 * t + 0.189269 * t * t + 0.001308 * t * t * t
    return -(t - num / den)


def t_inv(alpha, df):
    """Two-tailed t-distribution inverse (matches Excel TINV) via Cornish-Fisher series."""
    z = probit(1.0 - alpha / 2.0)
    z2, z3, z5, z7 = z ** 2, z ** 3, z ** 5, z ** 7
    return (z
            + (z3 + z) / (4 * df)
            + (5 * z5 + 16 * z3 + 3 * z) / (96 * df ** 2)
            + (3 * z7 + 19 * z5 + 17 * z3 - 15 * z) / (384 * df ** 3))


# ---------------------------------------------------------------------------
# Dimension calculators
# ---------------------------------------------------------------------------

def calc_completion(completions, z_crit):
    """
    Wilson score interval for completion rate.
    The Wilson centre uses z=2.0 (matches SUMv5.xls methodology) regardless of
    the alpha passed for satisfaction/time CIs. CI bounds are left uncapped so
    the upper bound can exceed 1.0 when computing SUM_high (also matches spreadsheet).
    Returns observed %, Wilson centre, CI low, CI high (all as 0–1 fractions).
    """
    n = len(completions)
    x = sum(completions)
    observed = x / n
    z_wilson = 2.0          # fixed per SUM methodology (approximation of z_0.975)
    z2 = z_wilson ** 2
    wilson = (x + z2 / 2) / (n + z2)
    se = math.sqrt(wilson * (1 - wilson) / n)
    return {
        "observed": observed,
        "pct": wilson,
        "ci_low": wilson - z_wilson * se,   # uncapped — may be < 0 for very low n
        "ci_high": wilson + z_wilson * se,  # uncapped — may exceed 1.0
    }


def calc_satisfaction(ease_list, sat_list, perception_list, z_crit, alpha, sat_spec=4.0):
    """
    Log-normal-style Z-score for composite satisfaction.
    composite_i = mean(ease_i, sat_i, perception_i)
    Z = (mean_composite − sat_spec) / stdev_composite

    displayed_pct uses the CI midpoint with t-distribution:
      (Φ(Z + t/√n) + Φ(Z − t/√n)) / 2  where t = TINV(alpha, n-1), SE = 1/√n
    """
    n = len(ease_list)
    composites = [
        (ease_list[i] + sat_list[i] + perception_list[i]) / 3.0
        for i in range(n)
    ]
    mean_s = sample_mean(composites)
    stdev_s = sample_stdev(composites)
    if stdev_s == 0:
        z = float("inf") if mean_s >= sat_spec else float("-inf")
    else:
        z = (mean_s - sat_spec) / stdev_s
    pct = normal_cdf(z)
    se_z = stdev_s / math.sqrt(n) if stdev_s > 0 else 0.0
    ci_high_z = z + z_crit * se_z
    ci_low_z = z - z_crit * se_z
    t = t_inv(alpha, n - 1)
    half = t / math.sqrt(n)
    displayed_pct = (normal_cdf(z + half) + normal_cdf(z - half)) / 2.0
    return {
        "mean": mean_s,
        "stdev": stdev_s,
        "spec": sat_spec,
        "z": z,
        "pct": pct,
        "displayed_pct": displayed_pct,
        "ci_low": normal_cdf(ci_low_z),
        "ci_high": normal_cdf(ci_high_z),
        "composites": composites,
    }


def derive_time_spec(times, completions, comp_sats, p=0.95):
    """
    95th percentile (Excel PERCENTILE.INC) of times from participants who:
      - completed the task (completion == 1)
      - have composite satisfaction >= 4.0
    Matches =PERCENTILE(R37:R86, F34) in SUMv5.xls where F34=95%.
    """
    accepted = [
        t for t, c, s in zip(times, completions, comp_sats)
        if c == 1 and s >= 4.0
    ]
    if len(accepted) < 2:
        raise ValueError(
            f"Need at least 2 accepted participants (completed + sat≥4) to derive time spec; "
            f"got {len(accepted)}."
        )
    return percentile_inc(accepted, p)


def calc_time(times, completions, comp_sats, z_crit, alpha):
    """
    Log-normal Z-score for task time against the data-derived spec.
    Uses ALL participants' times (including non-completers).

    displayed_pct uses the CI midpoint with t-distribution:
      (Φ(Z + t/√n) + Φ(Z − t/√n)) / 2  where t = TINV(alpha, n-1), SE = 1/√n
    """
    time_spec = derive_time_spec(times, completions, comp_sats)
    n = len(times)
    log_times = [math.log(t) for t in times]
    mean_log = sample_mean(log_times)
    stdev_log = sample_stdev(log_times)
    spec_log = math.log(time_spec)
    if stdev_log == 0:
        z = float("inf")
    else:
        z = (spec_log - mean_log) / stdev_log
    pct = normal_cdf(z)
    se_z = stdev_log / math.sqrt(n) if stdev_log > 0 else 0.0
    ci_high_z = z + z_crit * se_z
    ci_low_z = z - z_crit * se_z
    t = t_inv(alpha, n - 1)
    half = t / math.sqrt(n)
    displayed_pct = (normal_cdf(z + half) + normal_cdf(z - half)) / 2.0
    return {
        "time_spec": time_spec,
        "mean_log": mean_log,
        "stdev_log": stdev_log,
        "z": z,
        "pct": pct,
        "displayed_pct": displayed_pct,
        "ci_low": normal_cdf(ci_low_z),
        "ci_high": normal_cdf(ci_high_z),
    }


# ---------------------------------------------------------------------------
# Task-level and overall aggregation
# ---------------------------------------------------------------------------

def calc_task_sum(rows, z_crit, alpha):
    """
    rows: list of dicts with keys completion, ease, satisfaction, perception, time_s
    Returns a dict with all dimension results and the SUM score.
    """
    completions = [int(r["completion"]) for r in rows]
    ease = [float(r["ease"]) for r in rows]
    sat = [float(r["satisfaction"]) for r in rows]
    perception = [float(r["perception"]) for r in rows]
    times = [float(r["time_s"]) for r in rows]

    comp_result = calc_completion(completions, z_crit)

    sat_result = calc_satisfaction(ease, sat, perception, z_crit, alpha)
    comp_sats = sat_result["composites"]

    time_result = calc_time(times, completions, comp_sats, z_crit, alpha)

    # SUM score uses the observed completion rate (x/n), not the Wilson-adjusted centre.
    # The Wilson centre is used only for the CI bounds (matches SUMv5.xls).
    pct = (comp_result["observed"] + sat_result["pct"] + time_result["pct"]) / 3.0
    ci_low = (comp_result["ci_low"] + sat_result["ci_low"] + time_result["ci_low"]) / 3.0
    ci_high = (comp_result["ci_high"] + sat_result["ci_high"] + time_result["ci_high"]) / 3.0

    return {
        "n": len(rows),
        "completion": comp_result,
        "satisfaction": sat_result,
        "time": time_result,
        "sum": pct,
        "ci_low": ci_low,
        "ci_high": ci_high,
    }


def calc_overall_sum(task_results):
    sums = [v["sum"] for v in task_results.values()]
    lows = [v["ci_low"] for v in task_results.values()]
    highs = [v["ci_high"] for v in task_results.values()]
    return {
        "sum": sum(sums) / len(sums),
        "ci_low": sum(lows) / len(lows),
        "ci_high": sum(highs) / len(highs),
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def pct(v, decimals=1):
    return f"{v * 100:.{decimals}f}%"


def format_markdown_table(task_results, overall):
    header = "| Task | SUM Low | SUM Score | SUM High | Completion | Satisfaction | Time |"
    sep    = "|------|---------|-----------|----------|------------|--------------|------|"
    rows = [header, sep]
    for task_name, r in task_results.items():
        rows.append(
            f"| {task_name} "
            f"| {pct(r['ci_low'])} "
            f"| {pct(r['sum'])} "
            f"| {pct(r['ci_high'])} "
            f"| {pct(r['completion']['pct'])} "
            f"| {pct(r['satisfaction']['displayed_pct'])} "
            f"| {pct(r['time']['displayed_pct'])} |"
        )
    rows.append(
        f"| **Overall** "
        f"| {pct(overall['ci_low'])} "
        f"| {pct(overall['sum'])} "
        f"| {pct(overall['ci_high'])} "
        f"| — | — | — |"
    )
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

REQUIRED_COLS = {"task", "participant", "completion", "ease", "satisfaction", "perception", "time_s"}


def validate_rows(rows):
    errors = []
    for i, row in enumerate(rows, start=2):  # row 1 = header
        for col in REQUIRED_COLS:
            if col not in row or row[col].strip() == "":
                errors.append(f"Row {i}: missing value for '{col}'")
                continue
        try:
            c = int(row["completion"])
            if c not in (0, 1):
                errors.append(f"Row {i}: completion must be 0 or 1, got {row['completion']!r}")
        except (ValueError, KeyError):
            errors.append(f"Row {i}: completion must be 0 or 1, got {row['completion']!r}")
        for likert_col in ("ease", "satisfaction", "perception"):
            try:
                v = float(row[likert_col])
                if not (1.0 <= v <= 5.0):
                    errors.append(f"Row {i}: {likert_col} must be 1–5, got {v}")
            except (ValueError, KeyError):
                errors.append(f"Row {i}: {likert_col} must be numeric 1–5")
        try:
            t = float(row["time_s"])
            if t <= 0:
                errors.append(f"Row {i}: time_s must be > 0, got {t}")
        except (ValueError, KeyError):
            errors.append(f"Row {i}: time_s must be a positive number")
    return errors


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Compute SUM scores from usability test CSV.")
    parser.add_argument("--csv", required=True, help="Path to input CSV file")
    parser.add_argument("--alpha", type=float, default=0.10,
                        help="Significance level (default 0.10 → 90%% CI)")
    args = parser.parse_args()

    # t-distribution critical values for common alpha levels (two-tailed, df=n-1 ≈ ∞ approximation)
    # Using z for now; the skill can document the assumption.
    z_crit_map = {0.10: 1.645, 0.05: 1.960, 0.01: 2.576}
    z_crit = z_crit_map.get(args.alpha, 1.645)

    # Read CSV
    try:
        with open(args.csv, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            all_rows = list(reader)
    except FileNotFoundError:
        print(json.dumps({"error": f"File not found: {args.csv}"}))
        sys.exit(1)

    # Check required columns
    if all_rows:
        missing_cols = REQUIRED_COLS - set(all_rows[0].keys())
        if missing_cols:
            print(json.dumps({"error": f"CSV missing columns: {sorted(missing_cols)}"}))
            sys.exit(1)

    # Validate values
    errors = validate_rows(all_rows)
    if errors:
        print(json.dumps({"error": "Validation failed", "details": errors}))
        sys.exit(1)

    # Group by task (preserve insertion order)
    task_rows = defaultdict(list)
    for row in all_rows:
        task_rows[row["task"].strip()].append(row)

    # Check minimum participants per task
    min_n = 15
    under = {t: len(r) for t, r in task_rows.items() if len(r) < min_n}
    if under:
        msg = "; ".join(f"{t}: {n} participants (need {min_n})" for t, n in under.items())
        print(json.dumps({"error": f"Insufficient participants: {msg}"}))
        sys.exit(1)

    # Compute SUM per task
    task_results = {}
    for task_name, rows in task_rows.items():
        try:
            task_results[task_name] = calc_task_sum(rows, z_crit, args.alpha)
        except ValueError as e:
            print(json.dumps({"error": f"Task '{task_name}': {e}"}))
            sys.exit(1)

    overall = calc_overall_sum(task_results)

    # Serialise (strip non-JSON-safe floats)
    output = {
        "alpha": args.alpha,
        "z_crit": z_crit,
        "tasks": task_results,
        "overall": overall,
    }
    print(json.dumps(output, default=lambda x: round(x, 6) if isinstance(x, float) else x))
    print("---JSON-END---")
    print()
    print(format_markdown_table(task_results, overall))


if __name__ == "__main__":
    main()
