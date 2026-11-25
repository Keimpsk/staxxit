"""Format-boundary checks against the simulator's documented .staxxit v1.

The separate TypeScript integration check exercises the real parseReplay.
These tests isolate coordinate/action mapping, preservation and result labels.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import export_simulator_replays as exporter
from validate_gallery import derive_metrics, mix, snapshot, validate_trace
from oracle import State, INDEX, POSITIONS, apply, legal

DATE = '2026-11-25T12:00:00Z'


def opening_trace():
    """A legal B opening fixture, not a claimed random simulation result."""
    cfg = dict(variant='B', seed='0', start=0, games=1, limit=3,
               white=0, black=0, white_policy=0, black_policy=0,
               white_escape_first=False, black_escape_first=False,
               white_schedule=[-1]*3, black_schedule=[-1]*3)
    state = State()
    states, frames, moves = [state.copy()], [snapshot(state, 0)], []
    actions = [('p', None, (0, 0), 0), ('p', None, (1, 0), 0),
               ('c', (0, 0), (1, 0), 0)]
    for ply, action in enumerate(actions, 1):
        kind, origin, target, cut = action
        moves.append(dict(ply=ply, side=state.side, t=kind,
                          p=-1 if origin is None else INDEX[origin], q=INDEX[target], k=cut,
                          legal_count=len(legal(state, 'B')),
                          source_height=1 if origin is None else len(state.board[origin]),
                          target_height=len(state.board.get(target, ())),
                          placement_strategy=0 if kind=='p' else -1))
        apply(state, action)
        states.append(state.copy())
        frames.append(snapshot(state, ply))
    trace = dict(schema='staxxit.trace.v1', config=cfg, game_id=0,
                 initial_rng_state=str(mix(mix(0))), outcome=5, termination='limit',
                 regular=False, censored=True, moves=moves, snapshots=frames,
                 metrics=derive_metrics(states, moves, 'B'))
    validate_trace(trace)
    return trace


class SimulatorExport(unittest.TestCase):
    def test_all_board_indices_have_canonical_coordinates(self):
        self.assertEqual(exporter.coordinate(INDEX[(0, 0)]), '0,0')
        self.assertEqual(exporter.coordinate(0), '-6,0')
        self.assertEqual(exporter.coordinate(126), '6,0')
        self.assertEqual([exporter.coordinate(i) for i in range(127)],
                         [f'{q},{r}' for q,r in POSITIONS])
        for invalid in (-1, 127, '63', 63.5, True):
            with self.subTest(index=invalid), self.assertRaises((ValueError, TypeError)):
                exporter.coordinate(invalid)

    def test_every_action_kind_and_bottom_split_height(self):
        p, q = INDEX[(0,0)], INDEX[(1,0)]
        for symbol, kind in [('m','move'),('c','capture'),('e','exit')]:
            self.assertEqual(exporter.convert_move(dict(t=symbol, side=1, p=p, q=q, k=0)),
                             dict(player='B', kind=kind, **{'from':'0,0', 'to':'1,0'}))
        self.assertEqual(exporter.convert_move(dict(t='p', side=0, p=-1, q=p, k=0)),
                         dict(player='W', kind='place', to='0,0'))
        self.assertEqual(exporter.convert_move(dict(t='s', side=0, p=p, q=q, k=7)),
                         dict(player='W', kind='split', h1=7, **{'from':'0,0', 'to':'1,0'}))
        self.assertEqual(exporter.convert_move(dict(t='x', side=1, p=-1, q=-1, k=0)),
                         dict(player='B', kind='pass'))

    def test_opening_capture_and_experimental_rules(self):
        trace = opening_trace()
        before = deepcopy(trace)
        replay = exporter.convert_trace(trace, date=DATE)
        self.assertEqual(trace, before, 'Export mutated the archived source')
        self.assertEqual(replay['version'], 1)
        self.assertEqual(replay['variant'], 'B')
        self.assertEqual(replay['date'], DATE)
        self.assertEqual(replay['rules'], dict(allowPass=True,endOnTwoPasses=True,
                                              threefold=True,restartAtCenter=True))
        self.assertEqual(replay['initial'], dict(board={}, current='W',piecesLeft=dict(W=18,B=18)))
        expected = [dict(player='W', kind='place', to='0,0'),
                    dict(player='B', kind='place', to='1,0'),
                    dict(player='W', kind='capture', **{'from':'0,0','to':'1,0'})]
        self.assertEqual([{k:v for k,v in move.items() if k!='comment'} for move in replay['moves']], expected)
        self.assertNotIn('result', replay, 'A study move limit is not a simulator draw or resignation')
        self.assertNotIn('resignedBy', replay)
        self.assertTrue(replay['moves'][-1].get('comment'), 'Move-limit stop should remain visible in replay')

    def test_result_label_mapping_is_not_research_reclassification(self):
        # Isolate serialization: the independent trajectory checker is stubbed
        # only in this metadata test. Production exports must validate normally.
        expected = {0:dict(winner='W',ending='regular'), 1:dict(winner='B',ending='regular'),
                    2:dict(winner='draw',ending='regular'), 3:dict(winner='draw',ending='repetition'),
                    4:dict(winner=None,ending='blocked'), 5:None}
        for outcome, result in expected.items():
            trace = opening_trace()
            trace['outcome'] = outcome
            trace['termination'] = ('white','black','draw','repeat','blocked','limit')[outcome]
            with self.subTest(outcome=outcome), patch.object(exporter, 'validate_trace', return_value=trace['metrics']):
                replay = exporter.convert_trace(trace, date=DATE)
            if result is None: self.assertNotIn('result', replay)
            else: self.assertEqual(replay['result'], result)
            self.assertEqual(trace['outcome'], outcome)
            self.assertNotIn('resignedBy', replay)

    def test_invalid_archived_action_rejected_before_export(self):
        broken = opening_trace()
        broken['moves'][0]['q'] = 0
        with self.assertRaises(ValueError): exporter.convert_trace(broken, date=DATE)

    def test_actual_archives_are_small_complete_and_unmodified(self):
        seen, split_count, outcomes = 0, 0, set()
        for family in ('gallery','gallery_long'):
            folder = HERE/'results'/family
            catalog = json.loads((folder/'catalog.json').read_text(encoding='utf-8'))
            for entry in catalog['games']:
                file = folder/entry['trace_file']
                original = file.read_bytes()
                trace = json.loads(original)
                replay = exporter.convert_trace(trace, date=DATE)
                self.assertEqual(len(replay['moves']), len(trace['moves']))
                self.assertLessEqual(len(replay['moves']), 20000)
                self.assertLessEqual(len(json.dumps(replay,ensure_ascii=False).encode('utf-8')), 5_000_000)
                self.assertEqual(file.read_bytes(), original)
                for source, target in zip(trace['moves'], replay['moves']):
                    if source['t']=='s':
                        split_count += 1
                        self.assertEqual(target['h1'], source['k'])
                    if 'comment' in target: self.assertLessEqual(len(target['comment']), 2000)
                    if target['kind']=='pass': self.assertEqual(set(target)-{'comment'}, {'player','kind'})
                outcomes.add(trace['outcome'])
                seen += 1
        self.assertEqual(seen, 55)
        self.assertGreater(split_count, 0)
        self.assertTrue({0,1,3,5}.issubset(outcomes))


if __name__=='__main__': unittest.main()
