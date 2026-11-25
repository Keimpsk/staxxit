"""Find and verify reachable four-ply cycles without an artificial draw rule."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reference'))
from oracle import State, POSITIONS, legal, apply, result, key, indexed, stack_tokens, assert_invariants
from differential import Compare
from protocol_client import Cpp


def reversible_cycle(state,variant):
    first=[a for a in legal(state,variant) if a[0]=='m']
    for a in first:
        s1=state.copy(); apply(s1,a)
        if result(s1,variant)>=0: continue
        for b in (x for x in legal(s1,variant) if x[0]=='m'):
            s2=s1.copy(); apply(s2,b)
            if result(s2,variant)>=0: continue
            c=('m',a[2],a[1],0)
            if c not in legal(s2,variant): continue
            s3=s2.copy(); apply(s3,c)
            if result(s3,variant)>=0: continue
            d=('m',b[2],b[1],0)
            if d not in legal(s3,variant): continue
            s4=s3.copy(); apply(s4,d)
            if result(s4,variant)<0 and key(s4)==key(state):
                return [a,b,c,d]
    return None


def run(args):
    cpp=Cpp(args.cpp) if args.cpp else None
    compare=Compare(cpp)
    try:
        for variant in ('A','B'):
            rng=random.Random(args.seed)
            found=False
            for game in range(args.games):
                state=State(); trace=[]
                for turn in range(args.limit):
                    if result(state,variant)>=0: break
                    if not any(state.reserve):
                        cycle=reversible_cycle(state,variant)
                        if cycle:
                            # Replay from the initial position and verify every
                            # action, terminal check, and the exact full state.
                            check=State()
                            for action in trace:
                                assert result(check,variant)<0
                                if action is None:
                                    assert not compare.check(check,variant)
                                    check.side=1-check.side; check.passes+=1
                                    assert check.passes<2
                                else:
                                    check=compare.check(check,variant,action)
                            assert key(check)==key(state)
                            before=key(check)
                            for action in cycle:
                                assert result(check,variant)<0
                                check=compare.check(check,variant,action)
                            assert key(check)==before and result(check,variant)<0
                            full={'side':state.side,'reserve':state.reserve,'passes':state.passes,
                                  'board':stack_tokens(state)}
                            digest=hashlib.sha256(json.dumps(full,sort_keys=True).encode()).hexdigest()
                            data=dict(variant=variant,seed=args.seed,search_game=game,
                                      prefix=[None if a is None else indexed(a) for a in trace],
                                      cycle=[indexed(a) for a in cycle],
                                      cycle_start=full,cycle_end=full,
                                      identical_state_sha256=digest,
                                      checked_legal_from_initial_position=True,
                                      regular_terminal_in_cycle=False,
                                      consecutive_passes_in_cycle=0,
                                      cpp_verified=bool(cpp),
                                      note='Repeating this legal cycle forever is possible only without a repetition/turn-limit adjudication.')
                            if args.cpp:
                                data['executable_sha256']=hashlib.sha256(Path(args.cpp).read_bytes()).hexdigest()
                            out=Path(args.output)/f'cycle_witness_{variant}.json'
                            out.parent.mkdir(parents=True,exist_ok=True)
                            out.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
                            print(f'{variant}: legal witness, prefix={len(trace)}, cycle=4, game={game}, file={out}')
                            found=True; break
                    moves=legal(state,variant)
                    if moves:
                        action=rng.choice(sorted(moves,key=indexed))
                        apply(state,action); trace.append(action)
                    else:
                        state.side=1-state.side; state.passes+=1; trace.append(None)
                        if state.passes==2: break
                    assert_invariants(state)
                if found: break
            if not found:
                raise RuntimeError(f'No reachable cycle found for {variant}; this does not prove absence.')
    finally:
        if cpp: cpp.close()


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--cpp')
    p.add_argument('--seed',type=int,default=20261125)
    p.add_argument('--games',type=int,default=100)
    p.add_argument('--limit',type=int,default=536)
    p.add_argument('--output',default='analysis/results')
    run(p.parse_args())
