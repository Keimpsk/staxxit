"""Measure scaling and check that changing thread count preserves game outcomes."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
from run_study import atomic_json

HERE = Path(__file__).resolve().parent

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine', type=Path, default=HERE/'build'/'staxxit.exe')
    p.add_argument('--games', type=int, default=10000)
    p.add_argument('--threads', type=int, nargs='+', default=[1, 4, 8, 16, 32])
    p.add_argument('--output', type=Path, default=HERE/'results'/'benchmark.json')
    a = p.parse_args()
    rows = []
    (HERE/'build').mkdir(exist_ok=True)
    for variant in 'AB':
        reference = None
        for threads in a.threads:
            output = HERE/'build'/f'bench_{variant}_{threads}.json'
            cmd = [str(a.engine.resolve()), '--variant', variant, '--games', str(a.games),
                   '--verify-every-step',
                   '--seed', '8122026', '--threads', str(threads), '--limit', '536', '--output', str(output)]
            before = time.perf_counter()
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            elapsed = time.perf_counter()-before
            data = json.loads(output.read_text(encoding='utf-8'))
            stable_keys = ('games', 'turns', 'passes', 'center_resets', 'early_capture', 'early_escape',
                           'outcomes', 'actions', 'phase_turns', 'phase_choices', 'placement_phase_turns',
                           'placement_phase_choices', 'source_heights', 'max_heights', 'duration', 'first_empty')
            stable = {k:data[k] for k in stable_keys}
            if reference is None: reference=stable
            if stable != reference: raise RuntimeError(f'Non-reproducible thread count {threads}')
            row = dict(variant=variant, threads=threads, games=a.games, elapsed_seconds=elapsed,
                       games_per_second=a.games/elapsed, turns_per_second=data['turns']/elapsed,
                       outcome_sha256=hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest())
            rows.append(row)
            print(json.dumps(row), flush=True)
    atomic_json(a.output, dict(engine_sha256=hashlib.sha256(a.engine.read_bytes()).hexdigest(),
               note='Single measured trial per condition; shared machine, thermal/load effects uncontrolled.', rows=rows))

if __name__=='__main__': main()
