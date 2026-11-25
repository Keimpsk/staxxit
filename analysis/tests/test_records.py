"""Independent collector metrics and full recorded-game regression tests."""
from __future__ import annotations
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from validate_gallery import (best_from_traces, derive_metrics, selection_key,
                              check_study_config, task_seed, validate_catalog,
                              validate_trace, winning_strategy)
from oracle import State, INDEX, OUTER, apply, scores


def ongoing(white=6, black=12):
    # Deliberately local metric fixtures; complete traces validate all 36 stones.
    return State({(-2, 0): (0,)*white, (1, 0): (1,)*black}, [0, 0])


class Metrics(unittest.TestCase):
    def test_material_threshold_and_exact_score_equality(self):
        s = ongoing()
        metrics = derive_metrics([s], [], 'B')
        self.assertEqual(metrics['comeback_material'], [dict(ply=0, deficit=6), None])
        s = ongoing(7, 12)
        self.assertEqual(derive_metrics([s], [], 'B')['comeback_material'], [None, None])
        s = ongoing()
        own, enemy = next(p for p,c in OUTER.items() if c==0), next(p for p,c in OUTER.items() if c==1)
        s.board[own], s.board[enemy] = (0,), (1, 1)
        metrics = derive_metrics([s], [], 'B')
        self.assertEqual(metrics['comeback_material'], [None, None])
        self.assertEqual(metrics['comeback_score'][0], dict(ply=0, field_deficit=0, stone_deficit=1))

    def test_no_terminal_or_stock_comeback_witness(self):
        s = State({(0, 0): (1,)*12}, [0, 0])
        self.assertEqual(derive_metrics([s], [], 'B')['comeback_material'], [None, None])
        s = ongoing()
        s.reserve = [1, 0]
        self.assertEqual(derive_metrics([s], [], 'B')['comeback_material'], [None, None])

    def test_worst_deficit_and_earliest_tie(self):
        s = ongoing(6, 12)
        t = ongoing(5, 13)
        result = derive_metrics([s, t, t.copy()], [], 'B')
        self.assertEqual(result['comeback_material'][0], dict(ply=1, deficit=8))

    def test_offer_requires_immediate_capture_and_recapture_same_field(self):
        state = State({(-2, 0): (0, 0), (1, 0): (1,)}, [1, 0])
        states = [state.copy()]
        s = state.copy()
        path = [('p', None, (0, 0), 0), ('c', (1, 0), (0, 0), 0), ('c', (-2, 0), (0, 0), 0)]
        moves = []
        for i, a in enumerate(path):
            moves.append(dict(ply=i+1, side=s.side, t=a[0], p=-1 if a[1] is None else INDEX[a[1]], q=INDEX[a[2]], k=a[3]))
            apply(s, a)
            states.append(s.copy())
        metrics = derive_metrics(states, moves, 'B')
        self.assertEqual(metrics['offers'], [dict(ply=1, offered_height=1, attacker_height=1), None])
        self.assertEqual(metrics['captures'], 2)
        self.assertEqual(metrics['max_height'], 4)
        altered = deepcopy(moves)
        altered[2]['t'] = 'm'
        self.assertEqual(derive_metrics(states, altered, 'B')['offers'], [None, None])

    def test_fixed_winning_strategy_ignores_opponent_schedule(self):
        cfg = dict(white=8, black=6, white_schedule=[-1]*3, black_schedule=[8, 8, 6])
        self.assertEqual(winning_strategy(cfg, 0), 8)
        self.assertIsNone(winning_strategy(cfg, 1))

    def test_study_defaults_reject_hidden_policy_and_early_escape_changes(self):
        task, manifest = dict(id='baseline_A', variant='A', white=0, black=0), dict(seed=2026112501, limit=536)
        cfg = dict(variant='A', white=0, black=0, seed=str(task_seed(manifest['seed'],task['id'])),
                   limit=536, white_policy=0, black_policy=0, white_escape_first=False,
                   black_escape_first=False, white_schedule=[-1]*3, black_schedule=[-1]*3)
        check_study_config(cfg, task, manifest)
        for name, value in [('white_policy', 1), ('black_escape_first',True),
                            ('white_schedule',[8,8,6]), ('white_early_escape_only',True)]:
            with self.subTest(setting=name), self.assertRaises(ValueError):
                check_study_config(dict(cfg,**{name:value}), task, manifest)


class EngineRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        value = os.environ.get('STAXXIT_GALLERY_CPP')
        if not value:
            raise unittest.SkipTest('Set STAXXIT_GALLERY_CPP for recorder/replay integration tests')
        cls.cpp = str(Path(value).resolve())

    def run_batch(self, root, variant, games, start=0, threads=1, recorded=True):
        name = f'{variant}_{start}_{games}_{threads}_{recorded}'
        statistics, records = Path(root)/(name+'.stats.json'), Path(root)/(name+'.records.json')
        command = [self.cpp, '--variant', variant, '--seed', '20261125', '--limit', '536',
                   '--games', str(games), '--start', str(start), '--threads', str(threads),
                   '--verify-every-step', '--output', str(statistics)]
        if recorded:
            command += ['--records', str(records)]
        subprocess.run(command, check=True, capture_output=True, text=True)
        return json.loads(statistics.read_text(encoding='utf-8')), (json.loads(records.read_text(encoding='utf-8')) if recorded else None)

    def test_recording_preserves_games_and_thread_chunk_selection(self):
        fields = ('games', 'turns', 'passes', 'center_resets', 'early_capture', 'early_escape',
                  'conservation_checks', 'outcomes', 'actions', 'actions_by_player',
                  'early_capture_by_player', 'early_escape_by_player', 'phase_turns', 'phase_choices',
                  'placement_phase_turns', 'placement_phase_choices', 'source_heights', 'max_heights',
                  'first_empty', 'duration', 'depth_n')
        with tempfile.TemporaryDirectory() as tmp:
            for variant in ('A', 'B'):
                off, _ = self.run_batch(tmp, variant, 1000, recorded=False)
                on, serial = self.run_batch(tmp, variant, 1000)
                parallel_stats, parallel = self.run_batch(tmp, variant, 1000, threads=4)
                for name in fields:
                    self.assertEqual(off[name], on[name], name)
                    self.assertEqual(on[name], parallel_stats[name], name)
                self.assertEqual(serial, parallel, 'Collector depends on thread scheduling')
                validate_catalog(serial)
                replay_file = Path(tmp)/'replayed_selected.json'
                for trace in serial['games']:
                    command = [self.cpp, '--variant', variant, '--seed', '20261125', '--limit', '536',
                               '--replay', str(trace['game_id']), '--output', str(replay_file)]
                    subprocess.run(command, check=True, capture_output=True, text=True)
                    regenerated = json.loads(replay_file.read_text(encoding='utf-8'))
                    self.assertEqual(regenerated, trace, 'Replay game identity does not regenerate exact archived trajectory')
                _, left = self.run_batch(tmp, variant, 500, threads=2)
                _, right = self.run_batch(tmp, variant, 500, start=500, threads=3)
                expected = best_from_traces(left['games']+right['games'])
                actual = {selection_key(x):x for x in serial['selections']}
                self.assertEqual(actual, expected, 'Collector merge depends on chunk boundaries')
                reference = os.environ.get('STAXXIT_REFERENCE_CPP', str(HERE/'build'/'staxxit.exe'))
                if Path(reference).is_file():
                    result = subprocess.run([reference, '--variant', variant, '--seed', '20261125',
                        '--limit', '536', '--games', '1000', '--threads', '2', '--verify-every-step'],
                        check=True, capture_output=True, text=True)
                    original = json.loads(result.stdout)
                    for name in fields:
                        self.assertEqual(original[name], on[name], 'Original engine parity: '+name)

    def test_selection_matches_exhaustive_replay_of_small_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            for variant in ('A', 'B'):
                _, catalog = self.run_batch(tmp, variant, 48, threads=4)
                traces = []
                file = Path(tmp)/'single.json'
                for game_id in range(48):
                    command = [self.cpp, '--variant', variant, '--seed', '20261125', '--limit', '536',
                               '--replay', str(game_id), '--output', str(file)]
                    subprocess.run(command, check=True, capture_output=True, text=True)
                    trace = json.loads(file.read_text(encoding='utf-8'))
                    validate_trace(trace)
                    traces.append(trace)
                validate_catalog(catalog, all_traces=traces)

    def test_optional_early_escape_flag_survives_recording_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp)/'probe.json'
            base = [self.cpp, '--variant', 'B', '--seed', '20261125', '--limit', '536']
            subprocess.run(base+['--replay','0','--output',str(file)], check=True, capture_output=True, text=True)
            probe = json.loads(file.read_text(encoding='utf-8'))
            if 'white_early_escape_first' not in probe['config']:
                self.skipTest('Historical archive binary predates optional early-only escape metadata')
            catalog_file, stats_file = Path(tmp)/'records.json', Path(tmp)/'stats.json'
            command = base+['--games','1000','--white-early-escape-first','--verify-every-step',
                            '--records',str(catalog_file),'--output',str(stats_file)]
            subprocess.run(command, check=True, capture_output=True, text=True)
            catalog = json.loads(catalog_file.read_text(encoding='utf-8'))
            self.assertIs(catalog['config']['white_early_escape_first'], True)
            self.assertIs(catalog['config']['black_early_escape_first'], False)
            validate_catalog(catalog)
            for trace in catalog['games']:
                subprocess.run(base+['--white-early-escape-first','--replay',str(trace['game_id']),
                                     '--output',str(file)], check=True, capture_output=True, text=True)
                self.assertEqual(json.loads(file.read_text(encoding='utf-8')), trace)

    def test_short_replays_and_corruption_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            for variant in ('A', 'B'):
                file = Path(tmp)/f'{variant}.json'
                command = [self.cpp, '--variant', variant, '--seed', '20261125', '--limit', '1',
                           '--replay', '7', '--output', str(file)]
                subprocess.run(command, check=True, capture_output=True, text=True)
                trace = json.loads(file.read_text(encoding='utf-8'))
                self.assertEqual(validate_trace(trace)['turns'], 1)
                for mutation in ('stone', 'score', 'outcome', 'action', 'metric', 'seed'):
                    broken = deepcopy(trace)
                    if mutation == 'stone': broken['snapshots'][-1]['stacks'][INDEX[(0, 0)]] = '1'
                    elif mutation == 'score': broken['snapshots'][-1]['scores'][0][0] = 1
                    elif mutation == 'outcome': broken['outcome'] = 0
                    elif mutation == 'action': broken['moves'][0]['q'] = 0
                    elif mutation == 'metric': broken['metrics']['captures'] = 1
                    else: broken['initial_rng_state'] = '0'
                    with self.subTest(variant=variant, mutation=mutation), self.assertRaises(ValueError):
                        validate_trace(broken)


if __name__ == '__main__':
    unittest.main()
