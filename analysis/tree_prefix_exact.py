"""Exact shallow history-tree counts as a check on Monte Carlo depth profiles."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import time

from reference import oracle

HERE = Path(__file__).resolve().parent


def count_prefix(variant, max_depth):
    counts = [0] * (max_depth + 1)

    def visit(state, depth):
        counts[depth] += 1
        if depth == max_depth or oracle.result(state, variant) >= 0:
            return
        actions = oracle.legal(state, variant)
        if not actions:
            # Under this deliberately shallow cutoff all players retain stock,
            # so a pass would contradict the frontier-placement invariant.
            raise AssertionError("Unexpected pass in the early placement prefix")
        for action in actions:
            following = state.copy()
            oracle.apply(following, action)
            visit(following, depth + 1)

    visit(oracle.State(), 0)
    expected = [1, 1, 6, 48 if variant == 'A' else 54]
    assert counts[:min(4, len(counts))] == expected[:min(4, len(counts))]
    return {"variant": variant, "max_depth": max_depth,
            "history_nodes_by_depth": counts,
            "total_history_nodes": sum(counts),
            "log10_history_nodes_by_depth": [math.log10(n) for n in counts]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--depth', type=int, default=6)
    parser.add_argument('--output', type=Path, default=HERE/'results'/'tree_prefix_exact.json')
    args = parser.parse_args()
    if not 0 <= args.depth <= 8:
        parser.error('Use a shallow depth 0..8; this enumerates histories without transposition merging.')
    started = time.monotonic()
    result = {"schema": "staxxit.exact_history_prefix.v1", "complete": True,
              "method": "Exhaustive legal action histories through the independent Python oracle; no transposition merging.",
              "results": [count_prefix(v, args.depth) for v in 'AB'],
              "elapsed_seconds": time.monotonic()-started}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
