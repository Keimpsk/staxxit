"""Numerically stable Knuth summaries for the uniformly sampled baseline.

Input log sums must be natural logarithms. Depth sums are normalized by ALL
sampled games; paths that terminate before a depth contribute zero there.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
LN10 = math.log(10)
Z95 = 1.959963984540054


def logadd(a, b):
    if a is None:
        return b
    if b is None:
        return a
    hi = max(a, b)
    return hi + math.log1p(math.exp(-abs(a - b)))


def moments(n, logsum, logsum2):
    """Empirical moments of nonnegative weights, allowing zero contributions."""
    if n <= 0:
        raise ValueError("Sample count must be positive")
    if (logsum is None) != (logsum2 is None):
        raise ValueError("First and second log moments disagree about zero mass")
    if logsum is None:
        return {"samples": n, "log10_mean": None, "mean_is_observed_zero": True,
                "ess": 0.0, "relative_standard_error": None,
                "normal_ci95_log10": [None, None],
                "interval_status": "No observed weight; no informative confidence interval."}
    if not math.isfinite(logsum) or not math.isfinite(logsum2):
        raise ValueError("Expected finite natural logarithms or null for zero mass")
    # Cauchy-Schwarz gives S1^2/S2 <= n; nonnegative weights give ESS >= 1.
    logess = 2 * logsum - logsum2
    tolerance = 1e-7 * max(1, abs(logsum), abs(logsum2))
    if logess > math.log(n) + tolerance or logess < -tolerance:
        raise ValueError("Inconsistent first/second moments")
    ess = math.exp(max(0.0, min(math.log(n), logess)))
    logmean = logsum - math.log(n)
    rse = math.sqrt(max(0.0, (n / ess - 1) / (n - 1))) if n > 1 else None
    if rse is None:
        interval = [None, None]
    else:
        lower = 1 - Z95 * rse
        interval = [(logmean + math.log(lower)) / LN10 if lower > 0 else None,
                    (logmean + math.log1p(Z95 * rse)) / LN10]
    return {"samples": n, "log10_mean": logmean / LN10,
            "mean_is_observed_zero": False, "ess": ess,
            "relative_standard_error": rse, "normal_ci95_log10": interval,
            "interval_status": "Empirical normal approximation; heavy-tail coverage is not guaranteed.",
            "largest_observation_share_upper_bound": 1 / math.sqrt(ess)}


def summarize_result(result):
    if not result.get("tree_estimator_valid", False):
        raise ValueError("Uniform full-action sampling required for a valid Knuth estimate")
    n = result["games"]
    reached_counts = result.get("depth_n", [])
    first, second = result.get("depth_logsum", []), result.get("depth_logsum2", [])
    if len(first) != len(second) or len(first) != len(reached_counts):
        raise ValueError("Unequal depth array lengths")
    if not reached_counts or reached_counts[0] != n:
        raise ValueError("Depth zero must include every root")
    if abs(first[0] - math.log(n)) > 1e-7 or abs(second[0] - math.log(n)) > 1e-7:
        raise ValueError("Depth-zero root weights must all equal one")
    profile = []
    for depth, (reached, s1, s2) in enumerate(zip(reached_counts, first, second)):
        if not 0 <= reached <= n:
            raise ValueError("Invalid trajectory survival count")
        if reached == 0 and s1 is not None:
            raise ValueError("Nonzero depth weight without a visited path")
        row = {"depth": depth, "trajectories_reached": reached,
               "trajectory_survival_rate": reached / n,
               **moments(n, s1, s2)}
        profile.append(row)
    # Every trajectory Z is the sum of its depth-node weights. This checks that
    # terminal nodes and root are included consistently in both representations.
    by_depth = None
    for value in first:
        by_depth = logadd(by_depth, value)
    scalar = result.get("tree_logsum")
    if by_depth is None or scalar is None or abs(by_depth - scalar) > 1e-6 * max(1, abs(scalar)):
        raise ValueError("Scalar tree sum disagrees with sum over depth-node weights")
    return {"nodes_in_truncated_history_tree": moments(n, scalar, result["tree_logsum2"]),
            "depth_profile": profile,
            "depth_normalization": "All games, including zero contributions from already ended paths."}


def batch_diagnostics(files):
    rows = []
    for path in files:
        item = json.loads(path.read_text(encoding="utf-8"))
        result = item["result"]
        if not result.get("tree_estimator_valid", False):
            raise ValueError(f"Invalid tree estimator in {path}")
        rows.append({"start": item["config"]["start"],
                     **moments(result["games"], result["tree_logsum"], result["tree_logsum2"])})
    values = [r["log10_mean"] for r in rows if r["log10_mean"] is not None]
    return {"batches": rows,
            "batch_log10_mean_range": [min(values), max(values)] if values else [None, None],
            "note": "Ranges describe batch variability, not a guaranteed confidence interval."}


def write_csv(path, rows):
    columns = ["variant", "depth", "trajectories_reached", "samples", "trajectory_survival_rate",
               "log10_mean", "ess", "relative_standard_error", "ci95_log10_low", "ci95_log10_high"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in columns})


def self_test():
    # Three weights with mean 2, sample variance 1, SE sqrt(1/3).
    a = moments(3, math.log(6), math.log(14))
    assert abs(a["log10_mean"] - math.log10(2)) < 1e-12
    assert abs(a["ess"] - 36 / 14) < 1e-12
    assert abs(a["relative_standard_error"] - math.sqrt(1 / 3) / 2) < 1e-12
    # Zero contribution from a terminated second path must remain in denominator.
    assert abs(moments(2, math.log(10), math.log(100))["log10_mean"] - math.log10(5)) < 1e-12
    # Extreme logs do not overflow; a regular binary tree has exactly seven nodes.
    huge = moments(10, 10000 + math.log(10), 20000 + math.log(10))
    assert abs(huge["ess"] - 10) < 1e-8
    result = {"games": 2, "tree_estimator_valid": True,
              "tree_logsum": math.log(14), "tree_logsum2": math.log(98),
              "depth_n": [2, 2, 2],
              "depth_logsum": [math.log(2), math.log(4), math.log(8)],
              "depth_logsum2": [math.log(2), math.log(8), math.log(32)]}
    assert abs(summarize_result(result)["nodes_in_truncated_history_tree"]["log10_mean"] - math.log10(7)) < 1e-12
    print("tree_summary self-tests passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=HERE / "results" / "baseline.json")
    parser.add_argument("--checkpoints", type=Path, default=HERE / "checkpoints")
    parser.add_argument("--output", type=Path, default=HERE / "results" / "tree_summary.json")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    data = json.loads(args.input.read_text(encoding="utf-8"))
    output = {"schema": "staxxit.knuth_summary.v1", "source_run_id": data.get("run_id"),
              "source_manifest": data.get("manifest"),
              "source_complete": data.get("complete", False), "results": [],
              "scope": "History-tree nodes with the source run's repeat/pass/move-limit stopping rules.",
              "null_log10_convention": "Zero observed means have null log10; a null CI lower bound means the unlogged normal lower bound is nonpositive.",
              "caution": "Exploratory Monte Carlo estimate; empirical intervals can miss rare high-weight paths."}
    csv_rows = []
    for item in data["results"]:
        summary = summarize_result(item["result"])
        task = item["task"]
        checkpoint_dir = args.checkpoints / data["run_id"] / task["id"]
        batches = sorted(p for p in checkpoint_dir.glob("*.json") if p.stem.isdecimal()) if checkpoint_dir.exists() else []
        diagnostics = batch_diagnostics(batches)
        diagnostics["batch_games"] = sum(row["samples"] for row in diagnostics["batches"])
        diagnostics["all_games_covered"] = diagnostics["batch_games"] == item["result"]["games"]
        summary.update(task=task, checkpoint_batches_found=len(batches), batch_diagnostics=diagnostics)
        output["results"].append(summary)
        for row in summary["depth_profile"]:
            csv_rows.append({**row, "variant": task["variant"],
                             "ci95_log10_low": row["normal_ci95_log10"][0],
                             "ci95_log10_high": row["normal_ci95_log10"][1]})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write_csv(args.output.with_suffix(".csv"), csv_rows)
    for result in output["results"]:
        print(result["task"]["variant"], json.dumps(result["nodes_in_truncated_history_tree"]))
    print("Written", args.output)


if __name__ == "__main__":
    main()
