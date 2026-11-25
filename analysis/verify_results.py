"""Independent integrity audit of the seven completed study suites.

Does not import the research runner or its aggregation code. Every integer
counter is checked and independently re-summed from the checkpoint files.
Subset audits cannot write a final 'passed' status.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
PLAN = {'baseline': (2, 1_000_000), 'matrix': (288, 10_000),
        'phased': (144, 10_000), 'policies': (36, 10_000),
        'escape': (4, 10_000), 'adaptive': (8, 100_000),
        'sensitivity': (8, 100_000)}
SCALARS = ('games', 'turns', 'passes', 'center_resets', 'early_capture',
           'early_escape', 'conservation_checks')
SHAPES = {'outcomes': (6,), 'actions': (5,), 'phase_turns': (2,),
          'phase_choices': (2,), 'placement_phase_turns': (3,),
          'placement_phase_choices': (3,), 'source_heights': (37,),
          'max_heights': (37,), 'first_empty': (3, 6),
          'actions_by_player': (2, 5), 'early_capture_by_player': (2,),
          'early_escape_by_player': (2,)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    def invalid(value):
        raise ValueError(f'Non-finite JSON constant {value}: {path}')
    return json.loads(Path(path).read_text(encoding='utf-8'), parse_constant=invalid)


def canonical(value):
    return json.dumps(value, sort_keys=True)


def add(left, right):
    if isinstance(left, list):
        require(isinstance(right, list) and len(left) == len(right), 'Sum shape mismatch')
        return [add(a, b) for a, b in zip(left, right)]
    return left + right


def integer_shape(value, shape, label):
    if shape:
        require(isinstance(value, list) and len(value) == shape[0], f'{label}: invalid shape')
        for i, item in enumerate(value):
            integer_shape(item, shape[1:], f'{label}[{i}]')
    else:
        require(type(value) is int and value >= 0, f'{label}: expected nonnegative integer')


def validate_counters(r, variant, limit):
    for field in SCALARS:
        integer_shape(r[field], (), field)
    for field, shape in SHAPES.items():
        integer_shape(r[field], shape, field)
    integer_shape(r['duration'], (limit + 1,), 'duration')
    n = r['games']
    actions = sum(r['actions'])
    require(n > 0, 'Empty result')
    require(sum(r['outcomes']) == n, 'Outcome sum != games')
    require(sum(r['duration']) == n, 'Duration sum != games')
    require(r['outcomes'][5] <= r['duration'][limit], 'Turn-limit outcomes lack corresponding limit-length games')
    require(sum(r['max_heights']) == n, 'Maximum-height histogram != games')
    require(sum(map(sum, r['first_empty'])) == n, 'First-empty sum != games')
    require([sum(row[c] for row in r['first_empty']) for c in range(6)] == r['outcomes'],
            'First-empty outcome columns != outcomes')
    require(r['turns'] == actions + r['passes'], 'Turns != actions + passes')
    require(r['turns'] == sum(i*x for i, x in enumerate(r['duration'])),
            'Turns != weighted duration histogram')
    require(r['conservation_checks'] == actions + n, 'Missing per-action/final conservation checks')
    require([sum(row[c] for row in r['actions_by_player']) for c in range(5)] == r['actions'],
            'Per-player action totals != action totals')
    require(sum(r['early_capture_by_player']) == r['early_capture'],
            'Per-player early captures != early captures')
    require(sum(r['early_escape_by_player']) == r['early_escape'],
            'Per-player early escapes != early escapes')
    require(r['early_capture'] <= r['actions'][2], 'Early captures exceed captures')
    require(r['early_escape'] <= r['actions'][4], 'Early escapes exceed escapes')
    for side in (0, 1):
        require(r['actions_by_player'][side][0] <= 18*n, 'A player placed more than 18 stones/game')
        require(r['early_capture_by_player'][side] <= r['actions_by_player'][side][2],
                'Player early captures exceed player captures')
        require(r['early_escape_by_player'][side] <= r['actions_by_player'][side][4],
                'Player early escapes exceed player escapes')
    require(sum(r['phase_turns']) == r['turns'], 'Phase turn totals != turns')
    require(sum(r['placement_phase_turns']) == r['phase_turns'][0], 'Placement-stage turns != reserve turns')
    require(sum(r['placement_phase_choices']) == r['phase_choices'][0], 'Placement-stage choices != reserve choices')
    require(sum(r['phase_choices']) >= actions, 'Fewer legal choices than performed actions')
    require(sum(r['source_heights']) == sum(r['actions'][1:]), 'Source-height sample count != non-placement actions')
    require(r['source_heights'][0] == r['max_heights'][0] == r['duration'][0] == 0,
            'Unexpected zero-height/zero-duration sample')
    require(r['center_resets'] <= r['actions'][0], 'Center resets exceed placements')
    require(r['center_resets'] == 0, 'Unexpected center reset in a complete game from the legal initial state')
    if 'depth_n' in r:
        integer_shape(r['depth_n'], (limit + 1,), 'depth_n')
        require(sum(r['depth_n']) == r['turns'] + n, 'Depth visit samples != turns + terminal leaves')
    if variant == 'A':
        require(r['early_capture'] == r['early_escape'] == r['center_resets'] == 0,
                'Variant A contains an early capture/escape or a center reset')
        if limit >= 36:
            require(r['actions'][0] == 36*n, 'Variant A did not place all 36 stones/game')
            require(r['actions_by_player'][0][0] == r['actions_by_player'][1][0] == 18*n,
                    'Variant A placements per player != 18/game')
            require(r['first_empty'][0] == r['outcomes'] and
                    not any(r['first_empty'][1]) and not any(r['first_empty'][2]),
                    'Variant A first exhausted reserve should always be white')


def expected_tasks(suite, manifest):
    champions, schedules = manifest['champions'], manifest['schedules']
    for variant in 'AB':
        require(type(champions[variant]) is int and 0 <= champions[variant] < 12,
                'Champion strategy outside 0..11')
        schedule = schedules[variant].split(',')
        require(len(schedule) == 3 and all(x.isdigit() and 0 <= int(x) < 12 for x in schedule),
                'Invalid three-stage schedule')
    def task(v, w=0, b=0, extra=None, tag=None, limit=None):
        result = dict(id=f'{suite}_{v}_{tag or f"w{w:02d}_b{b:02d}"}',
                      suite=suite, variant=v, white=w, black=b, extra=extra or [])
        if limit is not None: result['limit'] = limit
        return result
    if suite == 'baseline':
        return [task(v) for v in 'AB']
    if suite == 'matrix':
        return [task(v, w, b) for v in 'AB' for w in range(12) for b in range(12)]
    if suite == 'phased':
        result = []
        for v in 'AB':
            champion = champions[v]
            for stage in range(3):
                for candidate in range(12):
                    schedule = [champion]*3
                    schedule[stage] = candidate
                    for color in ('white', 'black'):
                        result.append(task(v, champion, champion,
                            [f'--{color}-schedule', ','.join(map(str, schedule))],
                            f'phase{stage}_candidate{candidate:02d}_{color}'))
        return result
    if suite == 'policies':
        return [task('B', champions['B'], champions['B'],
                     ['--white-policy', str(w), '--black-policy', str(b)], f'wp{w}_bp{b}')
                for w in range(6) for b in range(6)]
    if suite == 'escape':
        return [task('B', champions['B'], champions['B'],
                     (['--white-escape-first'] if w else []) + (['--black-escape-first'] if b else []),
                     f'we{w}_be{b}') for w in range(2) for b in range(2)]
    if suite == 'adaptive':
        return [task(v, champions[v], champions[v],
                     (['--white-schedule', schedules[v]] if w else []) +
                     (['--black-schedule', schedules[v]] if b else []), f'wa{w}_ba{b}')
                for v in 'AB' for w in range(2) for b in range(2)]
    if suite == 'sensitivity':
        return [task(v, tag=f'limit{limit}', limit=limit)
                for v in 'AB' for limit in (128, 256, 1024, 2048)]
    raise ValueError(suite)


def engine_options(task):
    result = dict(white_policy=0, black_policy=0, white_escape_first=False,
                  black_escape_first=False, white_schedule=[-1, -1, -1],
                  black_schedule=[-1, -1, -1])
    tokens = iter(task['extra'])
    for option in tokens:
        name = option.removeprefix('--').replace('-', '_')
        require(name in result, f'Unrecognized task option: {option}')
        if name.endswith('_escape_first'):
            result[name] = True
        elif name.endswith('_schedule'):
            result[name] = list(map(int, next(tokens).split(',')))
        else:
            result[name] = int(next(tokens))
    result['tree_estimator_valid'] = (
        task['white'] == task['black'] == 0 and
        result['white_policy'] == result['black_policy'] == 0 and
        not result['white_escape_first'] and not result['black_escape_first'] and
        result['white_schedule'] == result['black_schedule'] == [-1, -1, -1])
    return result


def verify_suite(suite, args, provenance):
    path = args.results_dir / f'{suite}.json'
    data = read(path)
    manifest = data['manifest']
    require(manifest['suite'] == suite, 'Manifest suite mismatch')
    require(manifest['games_per_task'] == PLAN[suite][1], 'Games/task differs from required study plan')
    require(type(manifest['chunk']) is int and manifest['chunk'] > 0, 'Invalid chunk size')
    require(manifest['limit'] == 536, 'Primary study limit differs from 536')
    for field, value in provenance.items():
        require(manifest[field] == value, f'{field}: artifact differs from current final file')
    run_id = hashlib.sha256(canonical(manifest).encode()).hexdigest()[:16]
    require(data['run_id'] == run_id, 'Fingerprint run_id mismatch')
    expected = expected_tasks(suite, manifest)
    require(len(expected) == PLAN[suite][0], 'Internal task-plan mismatch')
    require(data['complete'] is True and data['selected_complete'] is True, 'Suite not complete')
    require(data['completed_tasks'] == data['total_tasks'] == len(expected) == len(data['results']),
            'Completed/total/result task counts differ')
    expected_by_id = {t['id']: t for t in expected}
    ids = [x['task']['id'] for x in data['results']]
    require(len(ids) == len(set(ids)), 'Duplicate result task ID')
    require(set(ids) == set(expected_by_id), 'Missing/unexpected task combinations')
    require(manifest['selected_task_ids'] == [t['id'] for t in expected], 'Manifest selected tasks differ from full plan')
    checkpoint_root = args.checkpoint_dir / run_id
    raw_manifest = read(checkpoint_root / 'manifest.json')
    for field, value in manifest.items():
        require(raw_manifest[field] == value, f'Checkpoint manifest differs: {field}')
    require(raw_manifest['tasks'] == expected, 'Checkpoint task plan mismatch')
    game_total = chunks_total = 0
    for item in data['results']:
        t, r = item['task'], item['result']
        require(t == expected_by_id[t['id']], f"Task configuration mismatch: {t['id']}")
        limit = t.get('limit', manifest['limit'])
        try:
            validate_counters(r, t['variant'], limit)
            n = manifest['games_per_task']
            require(r['games'] == n, 'Aggregated game count mismatch')
            seed = int.from_bytes(hashlib.sha256(f"{manifest['seed']}:{t['id']}".encode()).digest()[:8], 'little')
            require(item['seed'] == seed, 'Task seed derivation mismatch')
            expected_paths = [f'{start:09d}.json' for start in range(0, n, manifest['chunk'])]
            task_dir = checkpoint_root / t['id']
            require(sorted(p.name for p in task_dir.glob('*.json')) == expected_paths,
                    'Missing, extra or overlapping checkpoint chunks')
            aggregate = {}
            fields = list(SCALARS) + list(SHAPES) + ['duration'] + (['depth_n'] if 'depth_n' in r else [])
            for start in range(0, n, manifest['chunk']):
                count = min(manifest['chunk'], n-start)
                checkpoint = read(task_dir / f'{start:09d}.json')
                cfg = dict(task=t, start=start, games=count, seed=seed, limit=limit,
                           engine_sha256=provenance['engine_sha256'])
                require(checkpoint['config'] == cfg, 'Checkpoint configuration differs from task')
                raw = checkpoint['result']
                validate_counters(raw, t['variant'], limit)
                require(raw['schema'] == 2, 'Unexpected raw engine schema')
                for field, value in (('games', count), ('seed', seed), ('start', start),
                                     ('limit', limit), ('variant', t['variant']),
                                     ('white', t['white']), ('black', t['black'])):
                    require(raw[field] == value, f'Raw engine config mismatch: {field}')
                for field, value in engine_options(t).items():
                    require(raw[field] == value, f'Raw policy/schedule config mismatch: {field}')
                for field in fields:
                    aggregate[field] = raw[field] if field not in aggregate else add(aggregate[field], raw[field])
                require(type(checkpoint['elapsed_seconds']) in (int, float) and
                        math.isfinite(checkpoint['elapsed_seconds']) and checkpoint['elapsed_seconds'] >= 0,
                        'Invalid chunk elapsed time')
                chunks_total += 1
            for field in fields:
                require(aggregate[field] == r[field], f'Independent checkpoint sum differs: {field}')
            require(r['chunks'] == len(expected_paths), 'Aggregated chunk count mismatch')
            require(r['tree_estimator_valid'] == engine_options(t)['tree_estimator_valid'],
                    'Aggregated tree-estimator validity flag differs from task')
            game_total += n
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError(f"{t['id']}: {error}") from error
    require(game_total == PLAN[suite][0]*PLAN[suite][1], 'Suite total games differ from plan')
    return dict(status='passed', tasks=len(expected), games=game_total,
                independently_summed_chunks=chunks_total, run_id=run_id,
                artifact_sha256=sha(path), checkpoint_manifest_sha256=sha(checkpoint_root/'manifest.json'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path, default=HERE/'results')
    parser.add_argument('--checkpoint-dir', type=Path, default=HERE/'checkpoints')
    parser.add_argument('--engine', type=Path, default=HERE/'build'/'staxxit.exe')
    parser.add_argument('--suites', nargs='+', choices=list(PLAN), default=list(PLAN))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--recorded-runner-commit', default='3ae6a1de7c9fa2b3cade991709381915fdeef2d5',
                        help='Immutable Git version of the runner that generated the published study')
    parser.add_argument('--use-current-runner', action='store_true',
                        help='Verify a fresh reproduction generated by the current maintenance runner')
    args = parser.parse_args()
    require(len(args.suites) == len(set(args.suites)), 'Duplicate suite selection')
    full = set(args.suites) == set(PLAN)
    def git(*tokens):
        return subprocess.check_output(['git', *tokens], cwd=HERE.parent)
    recorded_commit = git('rev-parse', '--verify', args.recorded_runner_commit+'^{commit}').decode().strip()
    recorded_blob = git('show', recorded_commit+':analysis/run_study.py')
    recorded_runner_hash = hashlib.sha256(recorded_blob).hexdigest()
    provenance = dict(engine_sha256=sha(args.engine), source_sha256=sha(HERE/'staxxit.cpp'),
                      runner_sha256=sha(HERE/'run_study.py') if args.use_current_runner else recorded_runner_hash)
    runner_versions = dict(recorded_commit=recorded_commit,
                           verification_mode='current' if args.use_current_runner else 'published',
                           recorded_git_blob=git('rev-parse', recorded_commit+':analysis/run_study.py').decode().strip(),
                           recorded_runner_sha256=recorded_runner_hash,
                           current_maintenance_runner_sha256=sha(HERE/'run_study.py'),
                           note='Published manifests must match the immutable production runner; subsequent checkpoint-maintenance code is recorded separately.')
    suites, errors = {}, []
    for suite in args.suites:
        try:
            suites[suite] = verify_suite(suite, args, provenance)
            print(f"{suite}: passed, {suites[suite]['tasks']} tasks, {suites[suite]['games']:,} games", flush=True)
        except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
            suites[suite] = dict(status='failed', error=str(error))
            errors.append(f'{suite}: {error}')
            print(f'{suite}: FAILED: {error}', flush=True)
    status = 'failed' if errors else ('passed' if full else 'partial_pass')
    report = dict(status=status, all_required_suites_checked=full,
                  checked_at_utc=datetime.now(timezone.utc).isoformat(),
                  required_tasks=sum(n for n, _ in PLAN.values()),
                  required_games=sum(n*g for n, g in PLAN.values()),
                  verified_tasks=sum(s.get('tasks', 0) for s in suites.values()),
                  verified_games=sum(s.get('games', 0) for s in suites.values()),
                  center_resets_zero_hypothesis_checked=True,
                  provenance=provenance, runner_versions=runner_versions,
                  verifier_sha256=sha(__file__), suites=suites, errors=errors,
                  scope='Integer counters, complete task grids, final engine/source/runner hashes, and independent checkpoint reaggregation; not a proof of strategic optimality.')
    output = args.output or args.results_dir/('integrity.json' if full else 'integrity_partial.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix+'.tmp')
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    os.replace(temporary, output)
    print(f'{status}: {report["verified_games"]:,} verified games; {output}', flush=True)
    if errors: raise SystemExit(1)


if __name__ == '__main__':
    main()
