"""Summaries without converting repetition/stalemate/limits into draws."""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTCOMES = ('white', 'black', 'draw', 'repeat', 'blocked', 'limit')
ACTIONS = ('place', 'move', 'capture', 'split', 'escape')
SUM_SCALARS = ('games', 'turns', 'passes', 'center_resets', 'early_capture', 'early_escape', 'conservation_checks')
SUM_ARRAYS = ('outcomes', 'actions', 'phase_turns', 'phase_choices', 'placement_phase_turns',
              'placement_phase_choices', 'source_heights', 'max_heights', 'duration', 'first_empty', 'depth_n',
              'actions_by_player', 'early_capture_by_player', 'early_escape_by_player')

def add_nested(a, b):
    if isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            raise ValueError('Incompatible checkpoint array shapes')
        return [add_nested(x, y) for x, y in zip(a, b)]
    return a+b

def logadd(a, b):
    if a is None: return b
    if b is None: return a
    m = max(a, b)
    return m + math.log(math.exp(a-m)+math.exp(b-m))

def aggregate(chunks):
    if not chunks: raise ValueError('No data')
    r = {k: 0 for k in SUM_SCALARS}
    for c in chunks:
        for k in SUM_SCALARS:
            r[k] += c.get(k, 0)
        for k in SUM_ARRAYS:
            if k not in c: continue
            r[k] = c[k] if k not in r else add_nested(r[k], c[k])
    r['tree_estimator_valid'] = all(c.get('tree_estimator_valid', False) for c in chunks)
    for k in ('tree_logsum', 'tree_logsum2'):
        if k in chunks[0]:
            r[k] = None
            for c in chunks:
                r[k] = logadd(r[k], c[k])
    for k in ('depth_logsum', 'depth_logsum2'):
        if k in chunks[0]:
            r[k] = [None]*len(chunks[0][k])
            for c in chunks:
                if len(r[k]) != len(c[k]): raise ValueError('Incompatible tree profiles')
                r[k] = [logadd(x, y) for x, y in zip(r[k], c[k])]
    if 'depth_n' in chunks[0]:
        r['depth_n'] = [sum(c['depth_n'][d] for c in chunks) for d in range(len(chunks[0]['depth_n']))]
    if not r['tree_estimator_valid']:
        for k in ('tree_logsum', 'tree_logsum2', 'depth_n', 'depth_logsum', 'depth_logsum2'):
            r.pop(k, None)
    r['chunks'] = len(chunks)
    return r

def wilson(k, n, z=1.959963984540054):
    if not n: return [None, None]
    ph = k/n
    d = 1+z*z/n
    mid = (ph+z*z/(2*n))/d
    half = z*math.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/d
    return [max(0., mid-half), min(1., mid+half)]

def quantile(hist, fraction):
    n = sum(hist)
    if not n: return None
    cutoff = max(1, math.ceil(n*fraction))
    acc = 0
    for i, count in enumerate(hist):
        acc += count
        if acc >= cutoff: return i

def describe(r):
    n = r['games']
    o = r['outcomes']
    hist = r['duration']
    if sum(o) != n or sum(hist) != n:
        raise ValueError('Outcome/duration count does not match games')
    total = sum(i*v for i, v in enumerate(hist))
    if total != r['turns']:
        raise ValueError('Duration histogram/turn counter mismatch')
    mean = total/n
    variance = max(0., (sum(i*i*v for i, v in enumerate(hist))-n*mean*mean)/(n-1)) if n>1 else 0.
    sem = math.sqrt(variance/n)
    regular = sum(o[:3])
    phase = lambda nums, dens: [x/y if y else None for x, y in zip(nums, dens)]
    first = []
    for color, counts in zip(('white', 'black', 'never'), r['first_empty']):
        count = sum(counts)
        wins = counts[0 if color == 'white' else 1] if color != 'never' else 0
        first.append(dict(first=color, games=count, outcomes=dict(zip(OUTCOMES, counts)),
                          win_rate=wins/count if count and color!='never' else None,
                          win_ci95=wilson(wins, count) if color!='never' else [None, None]))
    return dict(games=n, outcomes={name:dict(count=k, rate=k/n, ci95=wilson(k, n))
                    for name, k in zip(OUTCOMES, o)}, regular_completion=regular/n,
                white_score_bounds=[(o[0]+.5*o[2])/n, (o[0]+.5*o[2]+sum(o[3:]))/n],
                regular_white_score=(o[0]+.5*o[2])/regular if regular else None,
                mean_turns=mean, mean_turns_ci95=[mean-1.95996398454*sem, mean+1.95996398454*sem],
                median_turns=quantile(hist, .5), p10_turns=quantile(hist, .1), p90_turns=quantile(hist, .9),
                p99_turns=quantile(hist, .99), actions=dict(zip(ACTIONS, r['actions'])),
                legal_choices_per_turn=phase(r['phase_choices'], r['phase_turns']),
                legal_choices_by_placement_stage=phase(r['placement_phase_choices'], r['placement_phase_turns']),
                early_capture_per_game=r['early_capture']/n, early_escape_per_game=r['early_escape']/n,
                center_resets=r['center_resets'], passes=r['passes'], first_empty=first)

def write_csv(path, rows):
    if not rows: return
    with Path(path).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def render_suite(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    rows = []
    for item in data['results']:
        item['summary'] = describe(item['result'])
        s, t = item['summary'], item['task']
        row = dict(id=t['id'], variant=t['variant'], white=t['white'], black=t['black'], games=s['games'])
        for name in OUTCOMES:
            v = s['outcomes'][name]
            row[name] = v['count']
            row[name+'_rate'] = v['rate']
            row[name+'_ci_low'], row[name+'_ci_high'] = v['ci95']
        row.update(mean_turns=s['mean_turns'], median_turns=s['median_turns'],
                   regular_completion=s['regular_completion'], regular_white_score=s['regular_white_score'],
                   white_score_lower=s['white_score_bounds'][0], white_score_upper=s['white_score_bounds'][1])
        rows.append(row)
    path.with_name(path.stem+'_summary.json').write_text(json.dumps(data, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    write_csv(path.with_suffix('.csv'), rows)
    if path.stem == 'matrix':
        for variant in ('A', 'B'):
            selected = [x for x in data['results'] if x['task']['variant']==variant]
            matrix_rows = []
            for w in range(12):
                row = {'white_strategy': w}
                for b in range(12):
                    match = next((x for x in selected if x['task']['white']==w and x['task']['black']==b), None)
                    row[f'black_{b}'] = match['summary']['outcomes']['white']['rate'] if match else None
                matrix_rows.append(row)
            write_csv(path.with_name(f'win_matrix_{variant}.csv'), matrix_rows)
            ranking = []
            for strategy in range(12):
                points = regular = games = wins = draws = unresolved = 0
                for item in selected:
                    t, r = item['task'], item['result']
                    for c in (0, 1):
                        if t['white' if c==0 else 'black'] != strategy: continue
                        o = r['outcomes']
                        wins += o[c]
                        draws += o[2]
                        regular += sum(o[:3])
                        games += r['games']
                        unresolved += sum(o[3:])
                ranking.append(dict(strategy=strategy, games=games, wins=wins, draws=draws,
                    regular_games=regular, unresolved=unresolved, regular_score=(wins+.5*draws)/regular if regular else None,
                    score_lower=(wins+.5*draws)/games if games else None,
                    score_upper=(wins+.5*draws+unresolved)/games if games else None))
            ranking.sort(key=lambda x: -(x['regular_score'] or 0))
            write_csv(path.with_name(f'ranking_{variant}.csv'), ranking)
            path.with_name(f'ranking_{variant}.json').write_text(json.dumps(ranking, indent=2)+'\n', encoding='utf-8')
    return data

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results-dir', type=Path, default=HERE/'results')
    a = p.parse_args()
    for suite in ('baseline', 'matrix', 'phased', 'policies', 'escape', 'adaptive', 'sensitivity'):
        path = a.results_dir/f'{suite}.json'
        if path.exists():
            data = render_suite(path)
            print(f'{suite}: {len(data["results"])} tasks, {sum(x["result"]["games"] for x in data["results"]):,} games')

if __name__ == '__main__': main()
