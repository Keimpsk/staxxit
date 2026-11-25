"""Exploratory selection rule fixed before follow-up runs; no optimality claim."""
import argparse
import hashlib
import json
from pathlib import Path
from summarize import write_csv, wilson
from run_study import atomic_json

HERE = Path(__file__).resolve().parent

def load_complete(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    if not data['complete']: raise RuntimeError(f'Incomplete source: {path}')
    return data

def score(o, color):
    n = sum(o)
    regular = sum(o[:3])
    win, draw = o[color], o[2]
    return dict(games=n, wins=win, draws=draw, regular_games=regular,
                regular_score=(win+.5*draw)/regular if regular else None,
                score_lower=(win+.5*draw)/n if n else None,
                score_upper=(win+.5*draw+sum(o[3:]))/n if n else None,
                win_rate=win/n if n else None, win_ci95=wilson(win, n))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results-dir', type=Path, default=HERE/'results')
    a = p.parse_args()
    selection = dict(rule='Largest score among regular outcomes, ties by smallest strategy id; exploratory, conditional on completion. Follow-up seeds independent.', champions={}, schedules={}, source_hashes={})
    for v in 'AB':
        path = a.results_dir/f'ranking_{v}.json'
        rows = json.loads(path.read_text(encoding='utf-8'))
        rows.sort(key=lambda x: (-(x['regular_score'] if x['regular_score'] is not None else -1), x['strategy']))
        selection['champions'][v] = rows[0]['strategy']
        selection['source_hashes'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    matrix = load_complete(a.results_dir/'matrix.json')
    if len(matrix['results']) != 288: raise RuntimeError('Expected full 12x12x2 matrix')
    path = a.results_dir/'phased.json'
    if path.exists():
        phased = load_complete(path)
        if phased['manifest']['champions'] != selection['champions']:
            raise RuntimeError('Stale phased experiment: champions differ from current matrix selection')
        rows = []
        for v in 'AB':
            schedule = []
            for phase in range(3):
                candidates = []
                for candidate in range(12):
                    outcome = [0]*6
                    for color, name in enumerate(('white', 'black')):
                        label = f'phased_{v}_phase{phase}_candidate{candidate:02d}_{name}'
                        item = next(x for x in phased['results'] if x['task']['id']==label)
                        counts = item['result']['outcomes'][:]
                        if color: counts[0], counts[1] = counts[1], counts[0]
                        outcome = [x+y for x,y in zip(outcome, counts)]
                    s = score(outcome, 0)
                    row = dict(variant=v, stage=phase, candidate=candidate, **s)
                    candidates.append(row)
                    rows.append(row)
                best = min(candidates, key=lambda x: (-(x['regular_score'] if x['regular_score'] is not None else -1), x['candidate']))
                schedule.append(best['candidate'])
            selection['schedules'][v] = schedule
        write_csv(a.results_dir/'phase_comparison.csv', rows)
        selection['source_hashes']['phased.json'] = hashlib.sha256(path.read_bytes()).hexdigest()
    atomic_json(a.results_dir/'experiment_selection.json', selection)
    print(json.dumps(selection, indent=2))

if __name__=='__main__': main()
