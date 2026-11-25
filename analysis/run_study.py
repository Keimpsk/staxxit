"""Deterministic, atomic chunk checkpoints. Standard library only."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    # Windows scanners/readers can briefly hold a destination handle without
    # FILE_SHARE_DELETE. Retry the same atomic replacement; never truncate it.
    for attempt in range(8):
        try:
            os.replace(temp, path)
            return
        except PermissionError:
            if attempt == 7: raise
            time.sleep(min(.05 * 2**attempt, 1.))

def validate_chunk(data, config):
    n, limit = config['games'], config['limit']
    if data['games'] != n or len(data['outcomes']) != 6 or sum(data['outcomes']) != n:
        raise RuntimeError('Invalid checkpoint outcome counters')
    if len(data['duration']) != limit+1 or sum(data['duration']) != n:
        raise RuntimeError('Invalid checkpoint duration histogram')
    turns = sum(i*k for i,k in enumerate(data['duration']))
    actions = sum(data['actions'])
    if turns != data['turns'] or turns != actions+data['passes']:
        raise RuntimeError('Inconsistent checkpoint action/turn counters')
    if data['conservation_checks'] != actions+n:
        raise RuntimeError('Missing runtime stone-conservation checks')
    if data['seed'] != config['seed'] or data['start'] != config['start'] or data['limit'] != limit:
        raise RuntimeError('Checkpoint engine metadata differs from configuration')

def task(suite, variant, white=0, black=0, extra=None, tag=None):
    extra = extra or []
    label = tag or f'w{white:02d}_b{black:02d}'
    return dict(id=f'{suite}_{variant}_{label}', suite=suite, variant=variant,
                white=white, black=black, extra=extra)

def tasks_for(suite, champions, schedules=None):
    if suite == 'baseline':
        return [task(suite, v) for v in 'AB']
    if suite == 'matrix':
        return [task(suite, v, w, b) for v in 'AB' for w in range(12) for b in range(12)]
    if suite == 'phased':
        tasks = []
        for v in 'AB':
            champ = champions[v]
            for phase in range(3):
                for candidate in range(12):
                    schedule = [champ]*3
                    schedule[phase] = candidate
                    for color in ('white', 'black'):
                        tasks.append(task(suite, v, champ, champ,
                            [f'--{color}-schedule', ','.join(map(str, schedule))],
                            f'phase{phase}_candidate{candidate:02d}_{color}'))
        return tasks
    if suite == 'policies':
        return [task(suite, 'B', champions['B'], champions['B'],
                ['--white-policy', str(w), '--black-policy', str(b)], f'wp{w}_bp{b}')
                for w in range(6) for b in range(6)]
    if suite == 'escape':
        return [task(suite, 'B', champions['B'], champions['B'],
                (['--white-escape-first'] if w else []) + (['--black-escape-first'] if b else []),
                f'we{w}_be{b}') for w in range(2) for b in range(2)]
    if suite == 'early_escape':
        tasks = []
        for wp, bp, switches in ((0, 0, ((0, 0), (1, 0), (0, 1), (1, 1))),
                                 (1, 2, ((0, 0), (1, 0))),
                                 (2, 1, ((0, 0), (0, 1)))):
            policy = ['--white-policy', str(wp), '--black-policy', str(bp)]
            for we, be in switches:
                flags = (['--white-early-escape-first'] if we else []) + (
                    ['--black-early-escape-first'] if be else [])
                tasks.append(task(suite, 'B', champions['B'], champions['B'],
                                  policy + flags, f'wp{wp}_bp{bp}_we{we}_be{be}'))
        return tasks
    if suite == 'adaptive':
        return [task(suite, v, champions[v], champions[v],
                (['--white-schedule', schedules[v]] if w else []) +
                (['--black-schedule', schedules[v]] if b else []), f'wa{w}_ba{b}')
                for v in 'AB' for w in range(2) for b in range(2)]
    if suite == 'sensitivity':
        return [dict(task(suite, v, tag=f'limit{limit}'), limit=limit)
                for v in 'AB' for limit in (128, 256, 1024, 2048)]
    raise ValueError(suite)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine', type=Path, default=HERE/'build'/'staxxit.exe')
    p.add_argument('--suite', choices=['baseline', 'matrix', 'phased', 'policies', 'escape',
                                       'early_escape', 'adaptive', 'sensitivity'], required=True)
    p.add_argument('--games', type=int, help='games per task (1m baseline, 100k early_escape, 10k otherwise)')
    p.add_argument('--chunk', type=int, default=10000)
    p.add_argument('--seed', type=int, default=20261125)
    p.add_argument('--limit', type=int, default=536)
    p.add_argument('--threads', type=int, default=min(16, os.cpu_count() or 1))
    p.add_argument('--champion-a', type=int, default=0)
    p.add_argument('--champion-b', type=int, default=0)
    p.add_argument('--schedule-a', default='0,0,0')
    p.add_argument('--schedule-b', default='0,0,0')
    p.add_argument('--checkpoint-dir', type=Path, default=HERE/'checkpoints')
    p.add_argument('--results-dir', type=Path, default=HERE/'results')
    p.add_argument('--only', help='task-id substring filter for diagnosis')
    p.add_argument('--resume-run', help='Existing 16-hex checkpoint id; permits runner-only maintenance with identical engine/settings')
    a = p.parse_args()
    defaults = {'baseline': 1_000_000, 'early_escape': 100_000}
    n = a.games if a.games is not None else defaults.get(a.suite, 10_000)
    if n <= 0 or a.chunk <= 0 or a.threads <= 0:
        p.error('games, chunk and threads must be positive')
    champions = {'A': a.champion_a, 'B': a.champion_b}
    schedules = {'A': a.schedule_a, 'B': a.schedule_b}
    expected = tasks_for(a.suite, champions, schedules)
    tasks = [t for t in expected if not a.only or a.only in t['id']]
    if not tasks: p.error('No tasks selected')
    engine = a.engine.resolve()
    fingerprint = dict(engine_sha256=digest(engine), source_sha256=digest(HERE/'staxxit.cpp'),
                       runner_sha256=digest(__file__), seed=a.seed, limit=a.limit, games_per_task=n,
                       champions=champions, schedules=schedules, suite=a.suite, chunk=a.chunk,
                       selected_task_ids=[t['id'] for t in tasks])
    run_id = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()[:16]
    if a.resume_run:
        if len(a.resume_run) != 16 or any(c not in '0123456789abcdef' for c in a.resume_run):
            p.error('resume-run must be a 16-character lowercase hexadecimal id')
        original = json.loads((a.checkpoint_dir/a.resume_run/'manifest.json').read_text(encoding='utf-8'))
        for key, value in fingerprint.items():
            if key != 'runner_sha256' and original.get(key) != value:
                raise RuntimeError(f'Resume configuration mismatch: {key}')
        fingerprint['runner_sha256'] = original['runner_sha256']
        run_id = a.resume_run
    checkpoint_root = a.checkpoint_dir/run_id
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    atomic_json(checkpoint_root/'manifest.json', dict(**fingerprint, tasks=tasks, threads=a.threads,
                current_resume_runner_sha256=digest(__file__)))
    total = len(tasks)*n
    completed = 0
    newly_run = 0
    started = time.monotonic()
    summaries = []
    for t in tasks:
        chunks = []
        stable = hashlib.sha256(f"{a.seed}:{t['id']}".encode()).digest()
        seed = int.from_bytes(stable[:8], 'little')
        limit = t.get('limit', a.limit)
        for start in range(0, n, a.chunk):
            count = min(a.chunk, n-start)
            path = checkpoint_root/t['id']/f'{start:09d}.json'
            cfg = dict(task=t, start=start, games=count, seed=seed, limit=limit,
                       engine_sha256=fingerprint['engine_sha256'])
            if path.exists():
                checkpoint = json.loads(path.read_text(encoding='utf-8'))
                if checkpoint['config'] != cfg:
                    raise RuntimeError(f'Checkpoint configuration mismatch: {path}')
                data = checkpoint['result']
            else:
                raw = path.with_suffix('.raw.json')
                raw.parent.mkdir(parents=True, exist_ok=True)
                cmd = [str(engine), '--variant', t['variant'], '--games', str(count),
                       '--verify-every-step',
                       '--seed', str(seed), '--start', str(start), '--threads', str(a.threads),
                       '--limit', str(limit), '--white', str(t['white']), '--black', str(t['black']),
                       '--output', str(raw)] + t['extra']
                before = time.monotonic()
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                data = json.loads(raw.read_text(encoding='utf-8'))
                validate_chunk(data, cfg)
                atomic_json(path, dict(config=cfg, elapsed_seconds=time.monotonic()-before, result=data))
                raw.unlink()
                newly_run += count
            validate_chunk(data, cfg)
            chunks.append(data)
            completed += count
            elapsed = time.monotonic()-started
            rate = newly_run/elapsed if newly_run else 0
            eta = (total-completed)/rate if rate else None
            print(json.dumps(dict(suite=a.suite, task=t['id'], completed=completed, total=total,
                                  fraction=completed/total, games_per_second=round(rate, 1),
                                  eta_seconds=round(eta, 1) if eta is not None else None)), flush=True)
        from summarize import aggregate
        summaries.append(dict(task=t, seed=seed, result=aggregate(chunks)))
        filename = f'{a.suite}_diagnostic.json' if a.only else f'{a.suite}.json'
        atomic_json(a.results_dir/filename, dict(manifest=fingerprint, run_id=run_id,
                    complete=len(summaries)==len(expected), selected_complete=len(summaries)==len(tasks),
                    completed_tasks=len(summaries), total_tasks=len(expected),
                    results=summaries))
    print(f'Completed {a.suite}: {completed:,} games; results {a.results_dir}', flush=True)

if __name__ == '__main__':
    main()
