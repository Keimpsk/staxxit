"""Collect reproducible game records with bounded, resumable chunk archives."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_bytes(data)
    for attempt in range(8):
        try:
            os.replace(temp, path)
            return
        except PermissionError:
            if attempt == 7: raise
            time.sleep(min(.05*2**attempt, 1.))

def write_json(path, data):
    atomic_bytes(path, (json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode())

def task_list(baseline_games, matrix_games):
    result = []
    for v in 'AB':
        if baseline_games:
            result.append(dict(id=f'baseline_{v}', family='baseline', variant=v,
                               white=0, black=0, games=baseline_games))
        if matrix_games:
            result.extend(dict(id=f'matrix_{v}_w{w:02d}_b{b:02d}', family='matrix', variant=v,
                               white=w, black=b, games=matrix_games)
                          for w in range(12) for b in range(12))
    return result

def validate_batch(records, stats, task, start, count, seed, limit):
    if records['schema'] != 'staxxit.records.v1': raise ValueError('Unknown record schema')
    c = records['config']
    for key, value in dict(variant=task['variant'], seed=str(seed), start=start, games=count,
                           limit=limit, white=task['white'], black=task['black']).items():
        if c[key] != value: raise ValueError(f'Engine record configuration mismatch: {key}')
    if stats['games'] != count or sum(stats['outcomes']) != count or sum(stats['duration']) != count:
        raise ValueError('Invalid chunk game counters')
    actions = sum(stats['actions'])
    if stats['conservation_checks'] != actions+count or stats['turns'] != actions+stats['passes']:
        raise ValueError('Invalid material/action counters')
    if stats['turns'] != sum(i*n for i,n in enumerate(stats['duration'])):
        raise ValueError('Invalid duration histogram')
    games = {g['game_id']: g for g in records['games']}
    if len(games) != len(records['games']): raise ValueError('Duplicate archived game id')
    for game_id, game in games.items():
        if not start <= game_id < start+count: raise ValueError('Game id outside chunk')
        if game['config'] != c: raise ValueError('Trace/chunk configuration mismatch')
        if len(game['moves']) != game['metrics']['turns']:
            raise ValueError('Trace duration differs from move count')
        if len(game['snapshots']) != len(game['moves'])+1:
            raise ValueError('Missing replay snapshots')
    for selection in records['selections']:
        if selection['game_id'] not in games: raise ValueError('Missing selected trace')
        if not all(type(x) is int for x in selection['rank']): raise ValueError('Non-integer rank')
    return games

def merge_selections(best, batch, task):
    games = {g['game_id']:g for g in batch['games']}
    for selected in batch['selections']:
        if selected['category']=='best_strategy' and task['family']!='matrix':
            continue
        strategy = selected.get('strategy', -1)
        key = (task['variant'], selected['category'], strategy)
        item = dict(selected, task_id=task['id'], family=task['family'], variant=task['variant'])
        old = best.get(key)
        better = old is None or item['rank'] > old['selection']['rank']
        if old is not None and item['rank'] == old['selection']['rank']:
            better = (item['task_id'], item['game_id']) < (old['selection']['task_id'], old['selection']['game_id'])
        if better:
            best[key] = dict(selection=item, trace=games[item['game_id']])

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine', type=Path, default=HERE/'build'/'staxxit_gallery.exe')
    p.add_argument('--baseline-games', type=int, default=1000000, help='per variant')
    p.add_argument('--matrix-games', type=int, default=10000, help='per ordered strategy pair per variant')
    p.add_argument('--seed', type=int, default=2026112501)
    p.add_argument('--limit', type=int, default=536)
    p.add_argument('--threads', type=int, default=32)
    p.add_argument('--chunk', type=int, default=10000)
    p.add_argument('--checkpoint-dir', type=Path, default=HERE/'checkpoints'/'gallery')
    p.add_argument('--results-dir', type=Path, default=HERE/'results'/'gallery')
    a = p.parse_args()
    if a.baseline_games<0 or a.matrix_games<0 or not(a.baseline_games or a.matrix_games):
        p.error('Choose a positive sample size for at least one family')
    if not 1<=a.threads<=256 or a.chunk<1 or not 1<=a.limit<=100000:
        p.error('Invalid chunk/threads/limit')
    tasks = task_list(a.baseline_games, a.matrix_games)
    engine = a.engine.resolve()
    simulation = dict(schema='staxxit.gallery.study.v1', seed_recipe='sha256-v1',
                      seed=a.seed, limit=a.limit, chunk=a.chunk, tasks=tasks,
                      engine_sha256=sha(engine),
                      sources={name:sha(HERE/name) for name in ('staxxit.cpp','game_records.hpp')})
    run_id = hashlib.sha256(json.dumps(simulation, sort_keys=True).encode()).hexdigest()[:16]
    for existing in (a.results_dir/'catalog.json', a.results_dir/'progress.json'):
        if existing.exists():
            prior=json.loads(existing.read_text(encoding='utf-8'))
            prior_id=prior.get('run_id',prior.get('manifest',{}).get('run_id'))
            if prior_id != run_id:
                raise ValueError(f'Different study already uses {a.results_dir}; choose a new --results-dir')
    checkpoint = a.checkpoint_dir/run_id
    manifest = dict(simulation, run_id=run_id, collector_sha256=sha(__file__), threads=a.threads,
                    baseline_games_per_variant=a.baseline_games, matrix_games_per_cell=a.matrix_games,
                    best_strategy_population='balanced matrix only',
                    ties='Maximum rank; then lexicographically smallest task_id; then smallest game_id')
    write_json(checkpoint/'manifest.json', manifest)
    total = sum(t['games'] for t in tasks)
    completed = newly_run = chunk_count = 0
    started = time.monotonic()
    best, completed_tasks, summaries = {}, [], []
    from summarize import aggregate
    for task in tasks:
        seed = int.from_bytes(hashlib.sha256(f"staxxit.gallery.v1:{a.seed}:{task['id']}".encode()).digest()[:8], 'little')
        statistics = []
        for start in range(0, task['games'], a.chunk):
            count = min(a.chunk, task['games']-start)
            path = checkpoint/task['id']/f'{start:09d}.json.gz'
            cfg = dict(task=task, seed=str(seed), start=start, games=count, limit=a.limit,
                       engine_sha256=simulation['engine_sha256'])
            if path.exists():
                payload = json.loads(gzip.decompress(path.read_bytes()))
                if payload['config'] != cfg: raise ValueError(f'Checkpoint mismatch: {path}')
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                stats_path = path.with_suffix('.stats.json')
                records_path = path.with_suffix('.records.json')
                cmd = [str(engine), '--variant', task['variant'], '--seed', str(seed),
                       '--games', str(count), '--start', str(start), '--limit', str(a.limit),
                       '--threads', str(a.threads), '--white', str(task['white']), '--black', str(task['black']),
                       '--verify-every-step', '--output', str(stats_path), '--records', str(records_path)]
                before = time.monotonic()
                run = subprocess.run(cmd, capture_output=True, text=True)
                if run.returncode:
                    raise RuntimeError(f'Engine failed: {run.stderr}')
                payload = dict(config=cfg, seconds=time.monotonic()-before,
                               statistics=json.loads(stats_path.read_text(encoding='utf-8')),
                               records=json.loads(records_path.read_text(encoding='utf-8')))
                validate_batch(payload['records'], payload['statistics'], task, start, count, seed, a.limit)
                packed = json.dumps(payload, separators=(',', ':'), allow_nan=False).encode()
                atomic_bytes(path, gzip.compress(packed, mtime=0))
                stats_path.unlink()
                records_path.unlink()
                newly_run += count
            validate_batch(payload['records'], payload['statistics'], task, start, count, seed, a.limit)
            statistics.append(payload['statistics'])
            merge_selections(best, payload['records'], task)
            completed += count
            chunk_count += 1
            elapsed = time.monotonic()-started
            rate = newly_run/elapsed if newly_run else 0
            print(json.dumps(dict(run_id=run_id, task=task['id'], completed=completed, total=total,
                                  games_per_second=round(rate,1),
                                  eta_seconds=round((total-completed)/rate,1) if rate else None)), flush=True)
        summaries.append(dict(task=task, seed=str(seed), result=aggregate(statistics)))
        completed_tasks.append(task['id'])
        write_json(a.results_dir/'progress.json', dict(run_id=run_id, complete=False,
                   completed=completed, total=total, completed_tasks=completed_tasks))
    from gallery_export import export_gallery
    catalog = export_gallery(a.results_dir, best, dict(manifest, complete=True,
                             games=total, completed_tasks=len(completed_tasks), chunks=chunk_count), summaries)
    print(json.dumps(dict(complete=True, run_id=run_id, games=total, selections=len(catalog['selections']),
                         unique_games=len(catalog['games']), results_dir=str(a.results_dir))), flush=True)

if __name__=='__main__': main()
