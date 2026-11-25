"""Compare legacy Python and C++ against an independent coordinate oracle.

Each reachable trajectory uses oracle moves and a Python Random seed. RNGs do
not need to agree across implementations. Complete move sets, every transition,
and terminal outcomes must agree. Synthetic states improve rare split coverage.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'reference'))
from oracle import (State, POSITIONS, INNER, OUTER, legal, apply, result, key,
                    indexed, stack_tokens, assert_invariants)
import staxxit_variants as legacy
from protocol_client import Cpp


class Compare:
    def __init__(self, cpp=None):
        self.cpp = cpp
        self.states = self.transitions = 0
        self.actions = Counter()

    def check(self, state, variant, action=None):
        assert_invariants(state)
        moves = legal(state,variant)
        canonical = {indexed(a) for a in moves}
        assert len(canonical)==len(moves), 'Duplicate oracle move'
        old_moves = legacy.legal(state.board,state.reserve,state.side,
                                 'original' if variant=='A' else 'new')
        assert canonical=={indexed(a) for a in old_moves}, 'Legacy Python legal mismatch'
        assert len(old_moves)==len(canonical), 'Duplicate Python move'
        expected_result = result(state,variant)
        old_result = legacy.result(state.board,state.reserve) if variant=='B' or not any(state.reserve) else None
        assert expected_result=={None:-1,'white':0,'black':1,'draw':2}[old_result], 'Legacy Python result mismatch'
        response=self.cpp.query(state,variant,action) if self.cpp else None
        if response:
            assert canonical=={tuple(a) for a in response['moves']}, 'C++ legal mismatch'
            assert len(response['moves'])==len(canonical), 'Duplicate C++ move'
            assert expected_result==response['result'], 'C++ result mismatch'
        self.states+=1
        if action is None:
            return moves
        assert indexed(action) in canonical
        child=state.copy()
        apply(child,action)
        assert_invariants(child)
        old_board=state.board.copy(); old_res=state.reserve.copy()
        legacy.step(old_board,old_res,state.side,action)
        assert old_board==child.board and old_res==child.reserve, 'Legacy Python transition mismatch'
        if response:
            assert response['state']==stack_tokens(child), 'C++ transition stack mismatch'
            assert response['res']==child.reserve, 'C++ transition reserve mismatch'
            assert response['side']==child.side, 'C++ transition side mismatch'
            assert response['applied_result']==result(child,variant), 'C++ transition result mismatch'
        self.transitions+=1
        self.actions[action[0]]+=1
        return child


def synthetic(rng):
    reserve=[rng.randrange(19),rng.randrange(19)]
    stones=[0]*(18-reserve[0])+[1]*(18-reserve[1])
    rng.shuffle(stones)
    board={}
    if stones:
        nstacks=rng.randint(1,min(len(stones),30))
        cuts=[0]+sorted(rng.sample(range(1,len(stones)),nstacks-1))+[len(stones)]
        for lo,hi in zip(cuts,cuts[1:]):
            stack=tuple(stones[lo:hi])
            candidates=[p for p in POSITIONS if p not in board and
                        (p in INNER or OUTER[p] in (2,stack[-1]))]
            board[rng.choice(candidates)]=stack
    return State(board,reserve,rng.randrange(2))


def run(args):
    start=time.perf_counter(); rng=random.Random(args.seed)
    cpp=Cpp(args.cpp) if args.cpp else None
    compare=Compare(cpp); outcomes={}; saved_state=None; variant='A'
    try:
        for variant in ('A','B'):
            counts=Counter()
            for game in range(args.games):
                state=State(); seen=Counter()
                for turn in range(args.limit):
                    saved_state=state.copy()
                    terminal=result(state,variant)
                    if terminal>=0:
                        compare.check(state,variant)
                        counts[('white','black','draw')[terminal]]+=1
                        break
                    seen[key(state)]+=1
                    if seen[key(state)]>=3:
                        counts['repeat']+=1; break
                    moves=legal(state,variant)
                    if not moves:
                        compare.check(state,variant)
                        state.passes+=1; state.side=1-state.side
                        if state.passes==2:
                            counts['blocked']+=1; break
                    else:
                        action=rng.choice(sorted(moves,key=indexed))
                        state=compare.check(state,variant,action)
                        if result(state,variant)>=0:
                            compare.check(state,variant)
                            counts[('white','black','draw')[result(state,variant)]]+=1
                            break
                else:
                    counts['limit']+=1
            outcomes[variant]=dict(counts)
        for _ in range(args.synthetic):
            saved_state=synthetic(rng)
            for variant in ('A','B'):
                moves=compare.check(saved_state,variant)
                # In particular exercise rare high-stack splits and escapes.
                kinds={}
                for action in moves:
                    kinds.setdefault(action[0],action)
                for action in kinds.values():
                    compare.check(saved_state,variant,action)
    except Exception:
        if saved_state is not None:
            Path(args.output).parent.mkdir(parents=True,exist_ok=True)
            Path(args.output).with_name('validation_failure.json').write_text(json.dumps({
                'variant':variant,'side':saved_state.side,'res':saved_state.reserve,
                'passes':saved_state.passes,'state':stack_tokens(saved_state)},indent=2))
        raise
    finally:
        if cpp: cpp.close()
    report=dict(status='passed',seed=args.seed,games_per_variant=args.games,
                synthetic_states=args.synthetic,turn_limit=args.limit,
                compared_states=compare.states,compared_transitions=compare.transitions,
                action_coverage=dict(compare.actions),outcomes=outcomes,
                cpp_requests=cpp.requests if cpp else 0,
                elapsed_seconds=time.perf_counter()-start,
                note='Validation sample only; not a baseline simulation result.')
    if args.cpp:
        report['executable_sha256']=hashlib.sha256(Path(args.cpp).read_bytes()).hexdigest()
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--cpp',help='Path to compiled C++ executable; omit for Python-only audit')
    parser.add_argument('--games',type=int,default=1000)
    parser.add_argument('--synthetic',type=int,default=10000)
    parser.add_argument('--seed',type=int,default=20261125)
    parser.add_argument('--limit',type=int,default=536)
    parser.add_argument('--output',default='analysis/results/validation.json')
    run(parser.parse_args())
