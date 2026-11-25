"""Exact configuration upper bounds, using only Python's standard library.

This enumerates a superset of reachable positions, not legal histories.
Run: python analysis/complexity.py [--output analysis/results/complexity.json]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

LIMIT = 18


def series_power_unrestricted(cells: int, n: int = LIMIT) -> list[list[int]]:
    """[x^w y^b] (1-x-y)^(-cells); stacks are bottom-to-top strings."""
    return [[math.comb(cells + w + b - 1, w + b) * math.comb(w + b, w)
             for b in range(n + 1)] for w in range(n + 1)]


def cell_terms(top: int | None, max_height: int | None, n: int = LIMIT):
    """top: None unrestricted, 0 white, 1 black. Include the empty cell."""
    terms = [(0, 0, 1)]
    for w in range(n + 1):
        for b in range(n + 1):
            h = w + b
            if not h or (max_height is not None and h > max_height):
                continue
            if top is None:
                ways = math.comb(h, w)
            elif top == 0:
                ways = math.comb(h - 1, w - 1) if w else 0
            else:
                ways = math.comb(h - 1, b - 1) if b else 0
            if ways:
                terms.append((w, b, ways))
    return terms


def multiply_cell(dp, terms, n=LIMIT):
    result = [[0] * (n + 1) for _ in range(n + 1)]
    for a, b, k in terms:
        for w in range(a, n + 1):
            src = dp[w - a]
            dst = result[w]
            for black in range(b, n + 1):
                dst[black] += src[black - b] * k
    return result


def configurations(max_escape_height: int | None = 11, n: int = LIMIT):
    dp = series_power_unrestricted(91, n)
    for top, cells in ((None, 6), (0, 15), (1, 15)):
        terms = cell_terms(top, max_escape_height, n)
        for _ in range(cells):
            dp = multiply_cell(dp, terms, n)
    return dp


def independent_unrestricted_formula(w: int, b: int):
    """Independent expansion of S^97(1+xS)^15(1+yS)^15."""
    return sum(
        math.comb(15, i) * math.comb(15, j)
        * math.comb(96 + w + b, w + b - i - j)
        * math.comb(w + b - i - j, w - i)
        for i in range(min(15, w) + 1)
        for j in range(min(15, b) + 1)
    )


def describe(value: int):
    return {"exact": str(value), "log10": math.log10(value),
            "scientific": f"{value:.12e}"}


def placement_phase_bound():
    """A: 0..35 placements. First white piece still on center; ignore adjacency."""
    total, by_ply = 1, []
    by_ply.append({"ply": 0, "white": 0, "black": 0, "side": "white", "boards": "1"})
    for t in range(1, 36):
        w, b = (t + 1) // 2, t // 2
        count = math.comb(90, w - 1) * math.comb(91 - w, b)
        total += count
        by_ply.append({"ply": t, "white": w, "black": b,
                       "side": "white" if t % 2 == 0 else "black", "boards": str(count)})
    return total, by_ply


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "results" / "complexity.json")
    args = parser.parse_args()
    constrained = configurations(11)
    unconstrained = configurations(None)
    assert all(unconstrained[w][b] == independent_unrestricted_formula(w, b)
               for w in range(19) for b in range(19))
    assert all(constrained[w][b] <= unconstrained[w][b]
               for w in range(19) for b in range(19))
    assert all(constrained[w][b] == constrained[b][w]
               for w in range(19) for b in range(19))
    # Toy-case check: one white stone has 91 inner + 6 neutral + 15 white outer homes.
    assert constrained[1][0] == 112
    pre_a, by_ply = placement_phase_bound()
    a_post = 2 * constrained[18][18]
    b_all = 2 * sum(map(sum, constrained))
    data = {
        "schema": "staxxit.configuration_upper_bounds.v1",
        "meaning": "Exact counts of combinatoric supersets; NOT counts of reachable legal positions.",
        "stones_per_color": 18, "inner_cells": 91,
        "outer_cells": {"white": 15, "black": 15, "neutral": 6},
        "max_escape_height": 11,
        "variant_A": {"placement_before_ply_36": describe(pre_a),
                      "zero_reserves_any_side": describe(a_post),
                      "combined_state_upper_bound": describe(pre_a + a_post),
                      "placement_by_ply": by_ply},
        "variant_B": {"all_reserves_any_side_upper_bound": describe(b_all)},
        "color_only_relaxation": {
            "zero_reserves_any_side": describe(2 * unconstrained[18][18]),
            "all_reserves_any_side": describe(2 * sum(map(sum, unconstrained)))},
        "assumptions": ["Distinct board coordinates; no symmetry quotient.",
                        "Stones of one color indistinguishable; ordered bottom-to-top color strings distinguish stacks.",
                        "Escaped stacks remain on distinct outer cells permanently and count toward stone conservation.",
                        "Outer top color restrictions enforced; maximal escape height enforced.",
                        "Connectivity, capture history, stopping rule, and turn compatibility not fully enforced.",
                        "No repetition history, pass counter, or move-limit counter included in board-state counts."],
        "checks": {"independent_formula_coefficients": 361, "color_swap_symmetry": True,
                   "single_white_positions": 112, "bounded_leq_unbounded": True},
        "sources": ["https://www-cs-faculty.stanford.edu/~knuth/persi75-talk.pdf"]
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for v in ("variant_A", "variant_B"):
        print(v, json.dumps({k: value for k, value in data[v].items() if k != "placement_by_ply"}))
    print("361 independent coefficient checks passed; output:", args.output)


if __name__ == "__main__":
    main()
