#!/usr/bin/env bash
# Rebuild, validate and reproduce the study in an isolated results directory.
set -euo pipefail

cd "$(dirname "$0")/.."
python=${PYTHON:-python3}
cxx=${CXX:-g++}
threads=${1:-$("$python" -c 'import os; print(len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count() or 1)')}
output=${2:-analysis/build/reproduction}
engine="$output/staxxit"
results="$output/results"
mkdir -p "$results"

flags=(-O3 -march=native -std=c++17 -pthread -Wall -Wextra)
"$cxx" "${flags[@]}" analysis/staxxit.cpp -o "$engine"
"$cxx" "${flags[@]}" analysis/tests/heuristics.cpp -o "$output/heuristics"
"$output/heuristics"
STAXXIT_CPP="$engine" "$python" -m unittest discover -s analysis/tests -p 'test_*.py'
"$python" analysis/tests/differential.py --cpp "$engine" --output "$results/validation.json"
"$python" analysis/tests/runner_audit.py --cpp "$engine" --output "$results/validation_runner.json"
"$python" analysis/tests/cycle_witness.py --cpp "$engine" --output "$results"
"$python" analysis/complexity.py --output "$results/complexity.json"
"$python" analysis/tree_summary.py --self-test
"$python" analysis/tree_prefix_exact.py --depth 8 --output "$results/tree_prefix_exact_depth8.json"
benchmark_threads=(1)
if [[ $threads != 1 ]]; then benchmark_threads+=("$threads"); fi
"$python" analysis/benchmark.py --engine "$engine" --games 30000 --threads "${benchmark_threads[@]}" --output "$results/benchmark.json"

run() {
    "$python" analysis/run_study.py --engine "$engine" --threads "$threads" \
        --checkpoint-dir "$output/checkpoints" --results-dir "$results" --suite "$@"
}
selected() {
    "$python" -c 'import json, sys; from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))[sys.argv[2]][sys.argv[3]]
print(",".join(map(str, data)) if isinstance(data, list) else data)
' "$results/experiment_selection.json" "$1" "$2"
}

run baseline
run matrix
"$python" analysis/select_experiments.py --results-dir "$results" --matrix-only
champions=(--champion-a "$(selected champions A)" --champion-b "$(selected champions B)")
for suite in phased policies escape early_escape; do
    run "$suite" "${champions[@]}"
done
"$python" analysis/select_experiments.py --results-dir "$results"
run adaptive --games 100000 "${champions[@]}" \
    --schedule-a "$(selected schedules A)" --schedule-b "$(selected schedules B)"
run sensitivity --games 100000
"$python" analysis/summarize.py --results-dir "$results"
"$python" analysis/tree_summary.py --input "$results/baseline.json" \
    --checkpoints "$output/checkpoints" --output "$results/tree_summary.json"
"$python" analysis/verify_results.py --use-current-runner --engine "$engine" \
    --results-dir "$results" --checkpoint-dir "$output/checkpoints" \
    --suites baseline matrix phased policies escape adaptive sensitivity early_escape
