"""Independently replay saved Staxxit games with the coordinate-based oracle.

No C++ move generator, collector or gallery merger is imported. Selection
metrics are recomputed from the complete state trajectory, including every
ordered stack and all 36 stones.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/'reference'))
from oracle import (State, INNER, INDEX, POSITIONS, OUTER, apply, assert_invariants,
                    indexed, key, legal, result, scores, stack_tokens)

OUTCOMES = ('white', 'black', 'draw', 'repeat', 'blocked', 'limit')
MASK = (1 << 64)-1


def require(condition, message):
    if not condition:
        raise ValueError(message)


def mix(value):
    value = (value+0x9e3779b97f4a7c15) & MASK
    value = ((value^(value >> 30))*0xbf58476d1ce4e5b9) & MASK
    value = ((value^(value >> 27))*0x94d049bb133111eb) & MASK
    return value^(value >> 31)


def control(state):
    heights, counts = [0, 0], [0, 0]
    for p, stack in state.board.items():
        if p in INNER:
            heights[stack[-1]] += len(stack)
            counts[stack[-1]] += 1
    return heights, counts


def snapshot(state, ply):
    heights, counts = control(state)
    return dict(ply=ply, side=state.side, reserve=state.reserve[:], passes=state.passes,
                stacks=stack_tokens(state), scores=[list(x) for x in scores(state)],
                controlled=heights, active_stacks=counts)


def compare_snapshot(actual, state, ply):
    expected = snapshot(state, ply)
    for name, value in expected.items():
        require(actual.get(name) == value, f'Ply {ply}: snapshot {name} differs from independent replay')
    try:
        assert_invariants(state)
    except AssertionError as error:
        raise ValueError(f'Ply {ply}: 18+18 stone/outer-colour invariant failed') from error


def winning_strategy(config, player):
    if player not in (0, 1):
        return None
    color = 'white' if player == 0 else 'black'
    if any(x >= 0 for x in config[color+'_schedule']):
        return None
    return config[color]


def derive_metrics(states, moves, variant):
    """Recompute all witnesses; scores/material are descriptive, not minimax."""
    offers, comeback_score, comeback_material = [None]*2, [None]*2, [None]*2
    offer_ranks, score_ranks, material_ranks = [None]*2, [None]*2, [None]*2
    for i in range(len(moves)-2):
        a, b, c = moves[i:i+3]
        if a['t'] not in ('p', 'm') or b['t'] != 'c' or c['t'] != 'c':
            continue
        if not (a['side'] == c['side'] != b['side'] and a['q'] == b['q'] == c['q']):
            continue
        player = a['side']
        after_offer = states[i+1]
        offered = len(after_offer.board[POSITIONS[a['q']]])
        attacker = len(after_offer.board[POSITIONS[b['p']]])
        rank = (attacker, offered, -a['ply'])
        if offer_ranks[player] is None or rank > offer_ranks[player]:
            offer_ranks[player] = rank
            offers[player] = dict(ply=a['ply'], offered_height=offered, attacker_height=attacker)
    # Only positions in which play can genuinely continue can be a comeback
    # witness. In particular, a winner may have no active material at the end.
    for ply, state in enumerate(states):
        if any(state.reserve) or result(state, variant) >= 0:
            continue
        sc = scores(state)
        heights, _ = control(state)
        for player in (0, 1):
            opponent = 1-player
            if sc[player] < sc[opponent]:
                fields = sc[opponent][0]-sc[player][0]
                stones = sc[opponent][1]-sc[player][1]
                rank = (fields, stones, -ply)
                if score_ranks[player] is None or rank > score_ranks[player]:
                    score_ranks[player] = rank
                    comeback_score[player] = dict(ply=ply, field_deficit=fields, stone_deficit=stones)
            deficit = heights[opponent]-heights[player]
            if sc[player] == sc[opponent] and deficit >= 6:
                rank = (deficit, -ply)
                if material_ranks[player] is None or rank > material_ranks[player]:
                    material_ranks[player] = rank
                    comeback_material[player] = dict(ply=ply, deficit=deficit)
    return dict(turns=len(moves), captures=sum(x['t']=='c' for x in moves),
                max_height=max((len(s) for state in states for s in state.board.values()), default=0),
                final_scores=[list(x) for x in scores(states[-1])], offers=offers,
                comeback_score=comeback_score, comeback_material=comeback_material)


def validate_trace(trace):
    require(trace.get('schema') == 'staxxit.trace.v1', 'Unknown trace schema')
    cfg = trace['config']
    variant, limit = cfg['variant'], cfg['limit']
    require(variant in ('A', 'B') and type(limit) is int and limit > 0, 'Invalid variant or limit')
    require(type(cfg['seed']) is str and cfg['seed'].isdecimal(), 'Seed must be an exact decimal string')
    require(type(trace['initial_rng_state']) is str and trace['initial_rng_state'].isdecimal(),
            'Initial RNG state must be an exact decimal string')
    seed, game_id = int(cfg['seed']), trace['game_id']
    require(type(game_id) is int and 0 <= game_id <= MASK and 0 <= seed <= MASK, 'Invalid 64-bit identity')
    require(int(trace['initial_rng_state']) == mix(seed^mix(game_id)), 'Incorrect per-game RNG state')
    actions, saved = trace['moves'], trace['snapshots']
    require(0 < len(actions) <= limit, 'Invalid observed duration')
    require(len(saved) == len(actions)+1, 'Trace must include initial and every resulting snapshot')
    state = State()
    states = [state.copy()]
    seen = Counter()
    compare_snapshot(saved[0], state, 0)
    outcome = None
    for i, move in enumerate(actions):
        ply = i+1
        require(outcome is None, f'Ply {ply}: action after termination')
        seen[key(state)] += 1
        require(seen[key(state)] < 3, f'Ply {ply}: action after third repetition')
        require(result(state, variant) == -1, f'Ply {ply}: action after regular end')
        choices = legal(state, variant)
        require(move['ply'] == ply and move['side'] == state.side, f'Ply {ply}: invalid turn identity')
        require(move['legal_count'] == len(choices), f'Ply {ply}: incorrect legal-choice count')
        if not choices:
            require(move['t'] == 'x', f'Ply {ply}: missing forced pass')
            require(move['p'] == move['q'] == -1 and move['k'] == 0, f'Ply {ply}: invalid pass coordinates')
            require(move['source_height'] == move['target_height'] == 0 and move['placement_strategy'] == -1,
                    f'Ply {ply}: invalid pass metadata')
            state.passes += 1
            state.side = 1-state.side
            if state.passes == 2:
                outcome = 4
        else:
            p, q = move['p'], move['q']
            require(type(p) is int and type(q) is int and -1 <= p < 127 and 0 <= q < 127,
                    f'Ply {ply}: invalid board indices')
            action = (move['t'], None if p == -1 else POSITIONS[p], POSITIONS[q], move['k'])
            require(action in choices, f'Ply {ply}: action not legal under independent oracle')
            origin = 1 if p == -1 else len(state.board.get(POSITIONS[p], ()))
            target = len(state.board.get(POSITIONS[q], ()))
            require(move['source_height'] == origin and move['target_height'] == target,
                    f'Ply {ply}: incorrect pre-action stack heights')
            strategy = -1
            if move['t'] == 'p':
                color = 'white' if state.side == 0 else 'black'
                stage = (18-state.reserve[state.side])//6
                strategy = cfg[color+'_schedule'][stage]
                if strategy < 0:
                    strategy = cfg[color]
            require(move['placement_strategy'] == strategy, f'Ply {ply}: incorrect placement-strategy label')
            apply(state, action)
            terminal = result(state, variant)
            if terminal >= 0:
                outcome = terminal
        compare_snapshot(saved[ply], state, ply)
        states.append(state.copy())
    if outcome is None:
        if len(actions) == limit:
            outcome = 5
        else:
            seen[key(state)] += 1
            require(seen[key(state)] >= 3, 'Trace stopped without terminal condition')
            outcome = 3
    require(type(trace['outcome']) is int and trace['outcome'] == outcome, 'Incorrect game outcome')
    require(trace['termination'] == OUTCOMES[outcome], 'Incorrect terminal reason')
    expected = derive_metrics(states, actions, variant)
    require(trace['metrics'] == expected, 'Stored descriptive metrics differ from independent trajectory calculation')
    return expected


def eligible_selections(trace):
    """All category claims legitimately supported by this one trajectory."""
    metrics, winner, cfg = trace['metrics'], trace['outcome'], trace['config']
    turns = metrics['turns']
    out = [dict(category='longest_observed', player=-1, strategy=-1, rank=[turns]),
           dict(category='most_captures', player=-1, strategy=-1, rank=[metrics['captures']]),
           dict(category='tallest_stack', player=-1, strategy=-1, rank=[metrics['max_height']])]
    if winner <= 2:
        out.append(dict(category='longest_regular', player=-1, strategy=-1, rank=[turns]))
    if winner not in (0, 1):
        return out
    out.append(dict(category='shortest_won', player=winner, strategy=-1, rank=[-turns]))
    fixed = winning_strategy(cfg, winner)
    if fixed is not None:
        own, enemy = metrics['final_scores'][winner], metrics['final_scores'][1-winner]
        out.append(dict(category='best_strategy', player=winner, strategy=fixed,
                        rank=[own[0]-enemy[0], own[1]-enemy[1], -turns]))
    witness = metrics['offers'][winner]
    if witness is not None:
        out.append(dict(category='tactical_offer', player=winner, strategy=-1,
                        rank=[witness['attacker_height'], witness['offered_height']]))
    witness = metrics['comeback_score'][winner]
    if witness is not None:
        out.append(dict(category='comeback_score', player=winner, strategy=-1,
                        rank=[witness['field_deficit'], witness['stone_deficit'], -witness['ply']]))
    witness = metrics['comeback_material'][winner]
    if witness is not None:
        out.append(dict(category='comeback_material', player=winner, strategy=-1,
                        rank=[witness['deficit'], -witness['ply']]))
    return out


def selection_key(selection):
    # player is a property of the winning example, not a separate record slot.
    return selection['category'], selection['strategy']


def best_from_traces(traces):
    best = {}
    for trace in traces:
        for claim in eligible_selections(trace):
            claim = dict(claim, game_id=trace['game_id'])
            slot = selection_key(claim)
            old = best.get(slot)
            if old is None or claim['rank'] > old['rank'] or (claim['rank'] == old['rank'] and claim['game_id'] < old['game_id']):
                best[slot] = claim
    return best


def validate_catalog(catalog, all_traces=None):
    """Replay every saved game and recompute selections from saved/all games.

    With all_traces, tests establish true extrema within a complete small batch.
    Without them, validation proves legality, truthful ranks and consistency
    among the retained candidates; it does not pretend discarded games exist.
    """
    require(catalog.get('schema') == 'staxxit.records.v1', 'Unknown records schema')
    traces = catalog['games']
    indexed_traces = {}
    turns = 0
    for trace in traces:
        require(trace['config'] == catalog['config'], 'Catalog/trace configuration mismatch')
        game_id = trace['game_id']
        require(game_id not in indexed_traces, 'Duplicate game identity in catalog')
        require(catalog['config']['start'] <= game_id < catalog['config']['start']+catalog['config']['games'],
                'Saved game is outside sampled ID range')
        turns += validate_trace(trace)['turns']
        indexed_traces[game_id] = trace
    reported = {}
    referenced = set()
    for claim in catalog['selections']:
        slot = selection_key(claim)
        require(slot not in reported, 'Duplicate category slot in catalog')
        require(claim['game_id'] in indexed_traces, 'Selection references missing trace')
        trace = indexed_traces[claim['game_id']]
        eligible = eligible_selections(trace)
        base_claim = {k:claim[k] for k in ('category', 'player', 'strategy', 'rank')}
        require(base_claim in eligible, 'Selection rank/eligibility differs from trajectory')
        reported[slot] = {k:claim[k] for k in ('category', 'player', 'strategy', 'rank', 'game_id')}
        referenced.add(claim['game_id'])
    require(referenced == set(indexed_traces), 'Catalog retains unreferenced or missing games')
    candidates = traces if all_traces is None else all_traces
    expected = best_from_traces(candidates)
    require(reported == expected, 'Category extrema or deterministic ID ties are inconsistent')
    return dict(status='passed', traces=len(traces), selections=len(reported), replayed_turns=turns,
                exhaustive_sample=all_traces is not None)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local_path(root, relative):
    path = (root/relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError('Gallery path escapes its own directory') from error
    return path


def task_seed(base_seed, task_id):
    text = f'staxxit.gallery.v1:{base_seed}:{task_id}'
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], 'little')


def check_study_config(cfg, task, manifest):
    require(cfg['variant'] == task['variant'] and cfg['white'] == task['white'] and cfg['black'] == task['black'],
            'Trace/experiment strategy identity mismatch')
    require(cfg['seed'] == str(task_seed(manifest['seed'], task['id'])) and cfg['limit'] == manifest['limit'],
            'Trace/experiment seed or limit mismatch')
    require(cfg['white_policy'] == cfg['black_policy'] == 0, 'Unexpected reserve policy in gallery study')
    require(cfg['white_escape_first'] is False and cfg['black_escape_first'] is False,
            'Unexpected escape preference in gallery study')
    require(cfg['white_schedule'] == cfg['black_schedule'] == [-1]*3, 'Unexpected mixed placement schedule')
    # A later engine version can describe optional early-only escape flags.
    # Historical traces omit them; neither representation may enable them in
    # this fixed, uniformly moving sampling population.
    require(all(value is False for name,value in cfg.items() if 'early' in name and 'escape' in name),
            'Unexpected early-only escape preference in gallery study')


def validate_gallery(path, checkpoint_dir=None, source_commit=None, engine=None):
    path = Path(path)
    root = path.parent
    data = json.loads(path.read_text(encoding='utf-8'))
    require(data.get('schema') == 'staxxit.gallery.v1' and data.get('complete') is True,
            'Unknown or incomplete gallery')
    manifest = data['manifest']
    require(manifest.get('complete') is True, 'Incomplete gallery manifest')
    board_file = local_path(root, data['board_file'])
    require(sha(board_file) == data['board_sha256'], 'Board geometry checksum mismatch')
    board = json.loads(board_file.read_text(encoding='utf-8'))
    require(board['schema'] == 'staxxit.board.v1' and board['coordinates'] == 'axial' and
            board['stack_order'] == 'bottom-to-top', 'Unknown board representation')
    expected_cells = [dict(index=i, q=p[0], r=p[1], outer=OUTER.get(p,-1)) for i,p in enumerate(POSITIONS)]
    require(board['cells'] == expected_cells, 'Saved board geometry/outer colours differ from independent oracle')
    tasks = {x['id']:x for x in manifest['tasks']}
    require(len(tasks) == len(manifest['tasks']) == manifest['completed_tasks'], 'Duplicate or incomplete study tasks')
    require(manifest['games'] == sum(t['games'] for t in tasks.values()), 'Incorrect sampled game total')
    require(manifest['best_strategy_population'] == 'balanced matrix only', 'Unexpected best-strategy population')
    require(all(t['family'] in ('matrix','baseline') and t['variant'] in ('A','B') for t in tasks.values()),
            'Unknown study family or variant')
    for task in tasks.values():
        target = manifest['matrix_games_per_cell'] if task['family']=='matrix' else manifest['baseline_games_per_variant']
        require(task['games'] == target and target > 0, 'Unequal task sample sizes')
    for variant in ('A', 'B'):
        expected = {(w,b) for w in range(12) for b in range(12)} if manifest['matrix_games_per_cell'] else set()
        matrix_tasks = [t for t in tasks.values() if t['variant']==variant and t['family']=='matrix']
        actual = {(t['white'], t['black']) for t in matrix_tasks}
        require(actual == expected, 'Unbalanced strategy population')
        require(len(matrix_tasks) == len(expected), 'Duplicate ordered strategy cell')
        baseline = [t for t in tasks.values() if t['variant']==variant and t['family']=='baseline']
        require(len(baseline) == bool(manifest['baseline_games_per_variant']), 'Missing/duplicate baseline task')
        require(all(t['white'] == t['black'] == 0 for t in baseline), 'Nonrandom baseline placement policy')
    traces = {}
    replayed = 0
    for entry in data['games']:
        file_id = entry['file_id']
        require(file_id not in traces, 'Duplicate gallery game/file identity')
        file = local_path(root, entry['trace_file'])
        require(sha(file) == entry['sha256'], 'Saved trace checksum mismatch')
        require(local_path(root, entry['markdown_file']).is_file(), 'Missing readable game dossier')
        trace = json.loads(file.read_text(encoding='utf-8'))
        require(trace['game_id'] == entry['game_id'], 'Catalog/trace game identity mismatch')
        require(entry['task_id'] in tasks, 'Unknown task identity')
        cfg, task = trace['config'], tasks[entry['task_id']]
        check_study_config(cfg, task, manifest)
        require(0 <= trace['game_id'] < task['games'], 'Game index outside study population')
        require(cfg['start'] <= trace['game_id'] < cfg['start']+cfg['games'], 'Game index outside recorded chunk')
        replayed += validate_trace(trace)['turns']
        traces[file_id] = dict(trace=trace, entry=entry)
    selected = {}
    referenced = set()
    for claim in data['selections']:
        require(claim['file_id'] in traces, 'Selection references missing game')
        info = traces[claim['file_id']]
        trace, entry = info['trace'], info['entry']
        require(all(claim[k] == entry[k] for k in ('task_id','game_id','trace_file','markdown_file')),
                'Selection identity differs from saved game')
        require(claim['variant'] == trace['config']['variant'], 'Selection variant mismatch')
        require(claim['family'] == tasks[claim['task_id']]['family'], 'Selection population family mismatch')
        require({k:claim[k] for k in ('category','player','strategy','rank')} in eligible_selections(trace),
                'Untruthful final selection rank or eligibility')
        require(claim['category'] != 'best_strategy' or claim['family'] == 'matrix',
                'Baseline game used as a strategy-population record')
        slot = (claim['variant'], *selection_key(claim))
        require(slot not in selected, 'Duplicate final category slot')
        selected[slot] = {k:claim[k] for k in ('category','player','strategy','rank','game_id','task_id','family','variant')}
        referenced.add(claim['file_id'])
    require(referenced == set(traces), 'Unreferenced or missing final game dossier')
    # Check truthful rankings also against other retained games, even when local
    # checkpoint archives are unavailable in a downloaded repository checkout.
    retained_best = {}
    for info in traces.values():
        trace, task = info['trace'], tasks[info['entry']['task_id']]
        merge_gallery_candidates(retained_best, trace, task)
    require(selected == retained_best, 'Final records are not maximal even among retained games')
    report = dict(status='passed', traces=len(traces), selections=len(selected), replayed_turns=replayed,
                  sampled_games=manifest['games'], tasks=len(tasks), checkpoint_merge_checked=False)
    if checkpoint_dir is not None:
        audit = audit_checkpoints(Path(checkpoint_dir)/manifest['run_id'], tasks, manifest, selected, root)
        report.update(audit)
        report['source_provenance'] = verify_source_provenance(manifest, source_commit, engine)
    report['catalog_sha256'] = sha(path)
    return report


def verify_source_provenance(manifest, source_commit, engine):
    require(set(manifest['sources']) == {'staxxit.cpp','game_records.hpp'}, 'Unexpected archived engine-source set')
    if source_commit:
        commit = subprocess.check_output(['git','rev-parse','--verify',source_commit+'^{commit}'], cwd=HERE.parent).decode().strip()
        actual = {name:hashlib.sha256(subprocess.check_output(['git','show',commit+':analysis/'+name], cwd=HERE.parent)).hexdigest()
                  for name in manifest['sources']}
    else:
        commit = None
        actual = {name:sha(HERE/name) for name in manifest['sources']}
    require(actual == manifest['sources'], 'Source hashes differ from archived experiment')
    if engine is not None:
        require(sha(engine) == manifest['engine_sha256'], 'Executable hash differs from archived experiment')
    return dict(source_commit=commit, source_sha256=actual, executable_checked=engine is not None,
                engine_sha256=manifest['engine_sha256'])


def merge_gallery_candidates(best, trace, task, claims=None):
    for original in eligible_selections(trace) if claims is None else claims:
        if original['category'] == 'best_strategy' and task['family'] != 'matrix':
            continue
        claim = {k:original[k] for k in ('category','player','strategy','rank')}
        claim.update(game_id=trace['game_id'], task_id=task['id'], family=task['family'], variant=task['variant'])
        slot = (task['variant'], *selection_key(claim))
        old = best.get(slot)
        if old is None or claim['rank'] > old['rank'] or (claim['rank'] == old['rank'] and
                (claim['task_id'], claim['game_id']) < (old['task_id'], old['game_id'])):
            best[slot] = claim


def audit_checkpoints(checkpoint_root, tasks, manifest, final_selected, results_root):
    # Reuse the earlier independent counter checker, never the simulation
    # collector or its merger. It contains no C++ engine decisions.
    from verify_results import SCALARS, SHAPES, add, validate_counters
    fields = (*SCALARS, *SHAPES, 'duration')
    statistics = json.loads((results_root/'statistics.json').read_text(encoding='utf-8'))
    require(statistics['complete'] is True and statistics['manifest'] == manifest, 'Statistics/catalog manifests differ')
    summaries = {x['task']['id']:x for x in statistics['results']}
    require(set(summaries) == set(tasks), 'Missing task statistics')
    expected_records, chunks, sampled, candidate_traces = {}, 0, 0, 0
    for task in tasks.values():
        combined = {}
        expected_files = {f'{start:09d}.json.gz' for start in range(0, task['games'], manifest['chunk'])}
        folder = checkpoint_root/task['id']
        require({f.name for f in folder.glob('*.json.gz')} == expected_files, 'Missing or extra checkpoint chunks')
        for start in range(0, task['games'], manifest['chunk']):
            count = min(manifest['chunk'], task['games']-start)
            file = folder/f'{start:09d}.json.gz'
            payload = json.loads(gzip.decompress(file.read_bytes()))
            seed = str(task_seed(manifest['seed'], task['id']))
            expected_config = dict(task=task, seed=seed, start=start, games=count, limit=manifest['limit'],
                                   engine_sha256=manifest['engine_sha256'])
            require(payload['config'] == expected_config, 'Checkpoint experiment configuration mismatch')
            batch, stats = payload['records'], payload['statistics']
            require(batch['schema'] == 'staxxit.records.v1', 'Unknown checkpoint records schema')
            check_study_config(batch['config'], task, manifest)
            require(batch['config']['start'] == start and batch['config']['games'] == count, 'Checkpoint record range mismatch')
            require(stats['games'] == count and stats['seed'] == int(seed) and stats['start'] == start,
                    'Checkpoint statistics range or seed mismatch')
            validate_counters(stats, task['variant'], manifest['limit'])
            for field in fields:
                combined[field] = stats[field] if field not in combined else add(combined[field], stats[field])
            # Candidate metrics are checked for internally truthful ranks here.
            # Full state-oracle replay is performed above for every final game;
            # exhaustive small-sample tests independently calibrate the collector.
            candidates = {x['game_id']:x for x in batch['games']}
            require(len(candidates) == len(batch['games']), 'Duplicate checkpoint game identity')
            for trace in candidates.values():
                require(trace['config'] == batch['config'], 'Checkpoint trace/config mismatch')
                require(start <= trace['game_id'] < start+count, 'Checkpoint game index outside its range')
                candidate_traces += 1
            recomputed = best_from_traces(candidates.values())
            actual = {selection_key(x):x for x in batch['selections']}
            require(actual == recomputed, 'Checkpoint category selection/rank inconsistency')
            for claim in batch['selections']:
                trace = candidates[claim['game_id']]
                merge_gallery_candidates(expected_records, trace, task, [claim])
            chunks += 1
            sampled += count
        r = summaries[task['id']]['result']
        validate_counters(r, task['variant'], manifest['limit'])
        require(all(combined[name] == r[name] for name in fields), 'Independent task statistic sum mismatch')
    require(chunks == manifest['chunks'] and sampled == manifest['games'], 'Study checkpoint/sample total mismatch')
    require(final_selected == expected_records, 'Global extrema/tie selection differs from independent checkpoint merge')
    return dict(checkpoint_merge_checked=True, verified_chunks=chunks, checkpoint_candidate_traces=candidate_traces,
                independently_summed_games=sampled,
                checkpoint_scope='Every integer aggregate and category merge; full oracle replay for final dossiers, not all discarded or retained chunk candidates.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--checkpoint-dir', type=Path, default=HERE/'checkpoints'/'gallery')
    p.add_argument('--artifacts-only', action='store_true', help='Replay saved dossiers without requiring uncommitted checkpoint archives')
    p.add_argument('--source-commit', help='Read archived engine/header bytes from an immutable Git commit after later source changes')
    p.add_argument('--engine', type=Path, help='Optional original executable for byte-identical provenance verification')
    a = p.parse_args()
    data = json.loads(a.input.read_text(encoding='utf-8'))
    if data.get('schema') == 'staxxit.trace.v1':
        metrics = validate_trace(data)
        report = dict(status='passed', traces=1, replayed_turns=metrics['turns'])
    elif data.get('schema') == 'staxxit.records.v1':
        report = validate_catalog(data)
    elif data.get('schema') == 'staxxit.gallery.v1':
        report = validate_gallery(a.input, None if a.artifacts_only else a.checkpoint_dir, a.source_commit, a.engine)
    else:
        raise ValueError('Unknown trace/catalog/gallery schema')
    report.update(input_sha256=sha(a.input), validator_sha256=sha(__file__))
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
