"""Hand-crafted rule tests, including deliberately small local test positions.

Local fixtures need not contain all 36 stones; generated complete games do.
"""
import sys
import os
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reference'))
from oracle import (State, POSITIONS, INNER, OUTER, DIRECTIONS, INDEX, legal,
                    apply, result, scores, key, assert_invariants, indexed)
from protocol_client import Cpp
import staxxit_analysis as legacy_core
import staxxit_variants as legacy


class Rules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cpp = Cpp(os.environ['STAXXIT_CPP']) if os.environ.get('STAXXIT_CPP') else None

    @classmethod
    def tearDownClass(cls):
        if cls.cpp: cls.cpp.close()

    def check_moves(self, state, variant):
        expected = set(legal(state, variant))
        actual = set(legacy.legal(state.board, state.reserve, state.side,
                                  'original' if variant == 'A' else 'new'))
        self.assertEqual(expected, actual)
        if self.cpp:
            response = self.cpp.query(state, variant)
            self.assertEqual({indexed(a) for a in expected}, {tuple(a) for a in response['moves']})
            self.assertEqual(result(state,variant), response['result'])
        return expected

    def check_result(self,state,variant,expected):
        self.assertEqual(result(state,variant),expected)
        old=legacy.result(state.board,state.reserve) if variant=='B' or not any(state.reserve) else None
        self.assertEqual({None:-1,'white':0,'black':1,'draw':2}[old],expected)
        if self.cpp:
            self.assertEqual(self.cpp.query(state,variant)['result'],expected)

    def test_geometry(self):
        self.assertEqual((len(POSITIONS), len(INNER), len(OUTER)), (127, 91, 36))
        self.assertEqual([list(OUTER.values()).count(c) for c in (0,1,2)], [15,15,6])
        self.assertEqual(INNER, legacy_core.I)
        self.assertEqual(OUTER, legacy_core.O)

    def test_first_move_center(self):
        for v in ('A','B'):
            self.assertEqual(self.check_moves(State(), v), {('p',None,(0,0),0)})

    def test_placement_neighbors_inner_empty_only(self):
        s = State({(5,0):(0,), (4,0):(1,)}, [17,17], 1)
        for v in ('A','B'):
            moves = self.check_moves(s,v)
            places = [a for a in moves if a[0]=='p']
            self.assertTrue(places)
            self.assertTrue(all(a[2] in INNER and a[2] not in s.board for a in places))
            self.assertIn(('p',None,(5,-1),0), moves)
            self.assertNotIn(('p',None,(6,0),0), moves)

    def test_empty_board_restart_ignores_escaped_stacks(self):
        s = State({(6,0):(0,1,0)}, [16,17], 0)
        for v in ('A','B'):
            self.assertEqual(self.check_moves(s,v), {('p',None,(0,0),0)})

    def test_capture_exact_distance_and_top_owner(self):
        s = State({(0,0):(1,0), (2,0):(0,1)}, [0,0], 0)
        for v in ('A','B'):
            self.assertEqual(self.check_moves(s,v), {('c',(0,0),(2,0),0)})
        apply(s, ('c',(0,0),(2,0),0))
        self.assertEqual(s.board[(2,0)], (0,1,1,0))
        self.assertEqual(s.side,1)

    def test_capture_too_near_blocks_ray(self):
        s = State({(0,0):(0,0), (1,0):(1,), (2,0):(1,)}, [0,0],0)
        moves = self.check_moves(s,'A')
        self.assertFalse(any(a[2] in ((1,0),(2,0),(3,0)) for a in moves))
        self.assertIn(('m',(0,0),(0,1),0),moves)

    def test_capture_too_far_not_legal(self):
        s = State({(0,0):(0,), (2,0):(1,)}, [0,0],0)
        self.assertNotIn(('c',(0,0),(2,0),0),self.check_moves(s,'B'))

    def test_own_stack_not_capture_or_crossed(self):
        s = State({(0,0):(0,0), (2,0):(1,0), (-4,0):(1,)}, [0,0],0)
        moves = self.check_moves(s,'A')
        self.assertFalse(any(a[1]==(0,0) and a[2] in ((2,0),(3,0)) for a in moves))

    def test_global_capture_duty(self):
        s = State({(0,0):(0,), (1,0):(1,), (-4,0):(0,)}, [0,0],0)
        for v in ('A','B'):
            self.assertEqual(self.check_moves(s,v), {('c',(0,0),(1,0),0)})

    def test_variant_a_placement_prohibits_capture(self):
        s = State({(0,0):(0,), (1,0):(1,)}, [17,17],0)
        self.assertTrue(all(a[0]=='p' for a in self.check_moves(s,'A')))
        s.reserve=[0,4]
        self.assertEqual(self.check_moves(s,'A'),set())

    def test_variant_b_reserve_allows_place_or_capture_only(self):
        s = State({(0,0):(0,), (1,0):(1,), (-4,0):(0,)*12}, [5,17],0)
        moves = self.check_moves(s,'B')
        self.assertEqual({a[0] for a in moves},{'p','c'})
        self.assertIn(('c',(0,0),(1,0),0),moves)

    def test_variant_b_empty_own_reserve_independent_of_opponent(self):
        s = State({(0,0):(0,), (4,0):(1,)}, [0,17],0)
        self.assertTrue(any(a[0]=='m' for a in self.check_moves(s,'B')))
        s.board[(1,0)]=(1,)
        self.assertEqual({a[0] for a in self.check_moves(s,'B')},{'c'})

    def test_variant_b_early_escape_and_split(self):
        s=State({(5,0):(0,),(-4,0):(1,)},[0,5],0)
        self.assertIn(('e',(5,0),(6,0),0),self.check_moves(s,'B'))
        s.board={(0,0):(0,)*12,(-4,0):(1,)}
        self.assertTrue(any(a[0]=='s' for a in self.check_moves(s,'B')))

    def test_move_distances_and_six_directions(self):
        s = State({(0,0):(1,0), (4,0):(1,)}, [0,0],0)
        moves = self.check_moves(s,'A')
        self.assertEqual({a[2] for a in moves},
                         {(d[0]*k,d[1]*k) for d in DIRECTIONS for k in (1,2)})

    def test_escape_color_neutral_exact_and_occupied(self):
        for target,color in OUTER.items():
            # A field directly inward along a corner direction or a ring edge.
            inward = next((p for p in INNER if any((p[0]+d[0],p[1]+d[1])==target
                                                   for d in DIRECTIONS)),None)
            if inward is None: continue
            for c in (0,1):
                s = State({inward:(c,)}, [0,0],c)
                moves=self.check_moves(s,'B')
                self.assertEqual(('e',inward,target,0) in moves,color in (c,2))
                s.board[target]=(c,)
                self.assertNotIn(('e',inward,target,0),self.check_moves(s,'B'))
        s=State({(4,0):(0,),(-4,0):(1,)},[0,0],0)
        self.assertNotIn(('e',(4,0),(6,0),0),self.check_moves(s,'A'))

    def test_escaped_stack_never_acts(self):
        s=State({(6,0):(0,),(-4,0):(1,)},[0,0],0)
        self.assertEqual(self.check_moves(s,'A'),set())

    def test_scoring_fields_before_stones(self):
        s=State({(6,0):(0,), (0,6):(0,),(-6,0):(0,)*10+(1,)},[0,0],0)
        for v in ('A','B'): self.check_result(s,v,0)

    def test_scoring_mixed_stack_all_stones_and_regular_draw(self):
        s=State({(6,0):(1,1,0),(-6,0):(1,1)},[0,0],0)
        self.assertEqual(scores(s),((1,3),(1,2)))
        for v in ('A','B'): self.check_result(s,v,0)
        s.board[(-6,0)]=(0,0,1)
        for v in ('A','B'): self.check_result(s,v,2)
        s.board[(-6,0)]=(0,0,0,1)
        for v in ('A','B'): self.check_result(s,v,1)

    def test_terminal_reserve_and_variant_a_phase_guard(self):
        s=State({(0,0):(1,)},[0,5],0)
        self.check_result(s,'A',-1)
        self.check_result(s,'B',2)
        s.reserve=[1,5]
        self.check_result(s,'B',-1)
        s.reserve=[0,0]
        self.check_result(s,'A',2)

    def test_split_threshold_and_both_top_colors(self):
        stack=(1,0,1,0,0,1,0,1,1,0,1,0)
        s=State({(0,0):stack,(4,0):(1,)},[0,0],0)
        splits=[a for a in self.check_moves(s,'A') if a[0]=='s']
        self.assertEqual(len(splits),6*sum(x==0 for x in stack[:-1]))
        for a in splits:
            child=s.copy(); apply(child,a)
            self.assertEqual(child.board[(0,0)][-1],0)
            self.assertEqual(child.board[a[2]][-1],0)
            self.assertEqual(child.board[(0,0)]+child.board[a[2]],stack)
            self.assertEqual(child.side,1)
        s.board[(0,0)]=stack[1:]
        self.assertFalse(any(a[0]=='s' for a in self.check_moves(s,'B')))

    def test_split_blocked_by_capture_duty_and_neighbors(self):
        s=State({(0,0):(0,)*12,(1,0):(0,), (2,0):(1,)},[0,0],0)
        self.assertEqual(self.check_moves(s,'A'),{('c',(1,0),(2,0),0)})
        del s.board[(2,0)]
        self.assertFalse(any(a[0]=='s' and a[2]==(1,0) for a in self.check_moves(s,'B')))

    def test_one_player_can_pass_without_regular_terminal_draw(self):
        # The white height-two stack cannot cross its six adjacent opponents.
        # This tests a pass, not a regular terminal result or a blocked game.
        board={(0,0):(0,0),(6,0):(0,)*16,(-6,0):(1,)*12}
        board.update({p:(1,) for p in DIRECTIONS})
        s=State(board,[0,0],0)
        assert_invariants(s)
        for v in ('A','B'):
            s.side=0
            self.check_result(s,v,-1)
            self.assertEqual(self.check_moves(s,v),set())
            s.side=1
            self.assertTrue(self.check_moves(s,v))

    def test_result_reserves_and_phase(self):
        s=State({(0,0):(0,)},[1,0],0)
        self.assertEqual(result(s,'A'),-1)
        self.assertEqual(result(s,'B'),2)
        s.reserve=[1,1]
        self.assertEqual(result(s,'B'),-1)
        s.reserve=[0,0]
        self.assertEqual(result(s,'A'),2)

    def test_result_lexicographic_outer_fields_then_all_stones(self):
        white=[p for p,v in OUTER.items() if v==0]
        black=[p for p,v in OUTER.items() if v==1]
        s=State({white[0]:(1,)*10+(0,), black[0]:(1,),black[1]:(1,)},[0,0])
        self.assertEqual(result(s,'A'),1)
        del s.board[black[1]]
        self.assertEqual(result(s,'A'),0)
        s.board[black[0]]=(0,)*10+(1,)
        self.assertEqual(result(s,'B'),2)
        self.assertEqual(scores(s),((1,11),(1,11)))

    def test_conservation_all_action_types(self):
        s=State(); assert_invariants(s)
        apply(s,('p',None,(0,0),0)); assert_invariants(s)
        apply(s,('p',None,(1,0),0)); assert_invariants(s)
        apply(s,('c',(0,0),(1,0),0)); assert_invariants(s)
        s=State({(0,0):(1,0)*6},[12,12],0)
        apply(s,('s',(0,0),(1,0),2)); assert_invariants(s)
        s=State({(5,0):(0,)},[17,18],0)
        apply(s,('e',(5,0),(6,0),0)); assert_invariants(s)

    def test_repetition_key_includes_order_reserve_turn_passes_outer(self):
        s=State({(0,0):(0,1)},[17,17],0)
        for change in ('order','reserve','side','passes','outer'):
            t=s.copy()
            if change=='order': t.board[(0,0)]=(1,0)
            if change=='reserve': t.reserve=[16,17]
            if change=='side': t.side=1
            if change=='passes': t.passes=1
            if change=='outer': t.board[(6,0)]=(0,)
            self.assertNotEqual(key(s),key(t))


if __name__=='__main__':
    unittest.main()
