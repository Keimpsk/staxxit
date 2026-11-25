"""Independent whole-game/statistics audit for the uniform C++ baseline.

The RNG and move ordering are matched deliberately, so terminal adjudications,
histograms and integer counters can be compared exactly, beyond protocol tests.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'reference'))
from oracle import State, INNER, DIRECTIONS, INDEX, distance, legal, apply, result, key, assert_invariants

MASK=(1<<64)-1


def mix(x):
    x=(x+0x9e3779b97f4a7c15)&MASK
    x=((x^(x>>30))*0xbf58476d1ce4e5b9)&MASK
    x=((x^(x>>27))*0x94d049bb133111eb)&MASK
    return x^(x>>31)


class RNG:
    def __init__(self,seed): self.x=seed
    def next(self):
        value=mix(self.x)
        self.x=(self.x+0x9e3779b97f4a7c15)&MASK
        return value
    def bounded(self,n):
        threshold=((-n)&MASK)%n
        while True:
            value=self.next()
            if value>=threshold: return value%n


def move_order(a):
    kind,p,q,k=a
    if kind=='p': return (-1,INDEX[q],0)
    n=distance(p,q)
    direction=((q[0]-p[0])//n,(q[1]-p[1])//n)
    return (INDEX[p],DIRECTIONS.index(direction),100+k if kind=='s' else n)


def empty_stats(limit):
    return dict(games=0,turns=0,passes=0,center_resets=0,early_capture=0,early_escape=0,
                conservation_checks=0,outcomes=[0]*6,actions=[0]*5,phase_turns=[0]*2,
                actions_by_player=[[0]*5 for _ in range(2)],
                early_capture_by_player=[0]*2,early_escape_by_player=[0]*2,
                phase_choices=[0]*2,placement_phase_turns=[0]*3,placement_phase_choices=[0]*3,
                source_heights=[0]*37,max_heights=[0]*37,first_empty=[[0]*6 for _ in range(3)],
                duration=[0]*(limit+1),depth_n=[0]*(limit+1))


def python_games(variant,n,seed,start,limit):
    stats=empty_stats(limit)
    for game_id in range(start,start+n):
        s=State(); rng=RNG(mix(seed^mix(game_id))); seen=Counter()
        first=None; outcome=5; length=0; maxheight=0
        for turn in range(limit):
            seen[key(s)]+=1
            if seen[key(s)]>=3:
                outcome=3; break
            moves=sorted(legal(s,variant),key=move_order)
            phase=0 if s.reserve[s.side] else 1
            stats['phase_turns'][phase]+=1
            stats['phase_choices'][phase]+=len(moves)
            if phase==0:
                stage=(18-s.reserve[s.side])//6
                stats['placement_phase_turns'][stage]+=1
                stats['placement_phase_choices'][stage]+=len(moves)
            stats['depth_n'][turn]+=1
            stats['turns']+=1; length+=1
            if not moves:
                stats['passes']+=1; s.passes+=1
                if s.passes==2:
                    outcome=4; break
                s.side=1-s.side
                continue
            action=moves[rng.bounded(len(moves))]
            kind,p,q,k=action
            stats['actions']['pmcse'.index(kind)]+=1
            stats['actions_by_player'][s.side]['pmcse'.index(kind)]+=1
            if kind=='p' and turn>0 and not INNER.intersection(s.board): stats['center_resets']+=1
            if kind=='c' and phase==0: stats['early_capture']+=1
            if kind=='e' and s.reserve[1-s.side]>0: stats['early_escape']+=1
            if kind=='c' and phase==0: stats['early_capture_by_player'][s.side]+=1
            if kind=='e' and s.reserve[1-s.side]>0: stats['early_escape_by_player'][s.side]+=1
            if p is not None:
                stats['source_heights'][len(s.board[p])]+=1
                maxheight=max(maxheight,len(s.board[p]))
            else: maxheight=max(maxheight,1)
            active=s.side
            apply(s,action)
            maxheight=max(maxheight,len(s.board[q]))
            if first is None and s.reserve[active]==0: first=active
            assert_invariants(s)
            stats['conservation_checks']+=1
            terminal=result(s,variant)
            if terminal>=0:
                outcome=terminal; break
        stats['depth_n'][length]+=1
        assert_invariants(s)
        stats['conservation_checks']+=1; stats['games']+=1
        stats['outcomes'][outcome]+=1; stats['duration'][length]+=1
        stats['max_heights'][maxheight]+=1
        stats['first_empty'][2 if first is None else first][outcome]+=1
    return stats


def cpp_games(args,variant,n,start,threads,limit):
    command=[str(Path(args.cpp).resolve()),'--variant',variant,'--games',str(n),
             '--seed',str(args.seed),'--start',str(start),'--threads',str(threads),
             '--limit',str(limit),'--verify-every-step']
    run=subprocess.run(command,text=True,capture_output=True,check=True)
    return json.loads(run.stdout)


def check_equal(expected,actual):
    for field,value in expected.items():
        assert value==actual[field], f'Full-game counter mismatch: {field}; Python={value}, C++={actual[field]}'


def run(args):
    started=time.perf_counter(); checks=[]
    for variant in ('A','B'):
        expected=python_games(variant,args.games,args.seed,0,args.limit)
        actual=cpp_games(args,variant,args.games,0,1,args.limit)
        check_equal(expected,actual)
        parallel=cpp_games(args,variant,args.games,0,4,args.limit)
        check_equal(expected,parallel)
        mid=args.games//2
        left=cpp_games(args,variant,mid,0,2,args.limit)
        right=cpp_games(args,variant,args.games-mid,mid,2,args.limit)
        for field,value in expected.items():
            def add(a,b):
                return [add(x,y) for x,y in zip(a,b)] if isinstance(a,list) else a+b
            assert value==add(left[field],right[field]), f'Batch resume mismatch: {field}'
        # Explicitly force the configurable limit to exercise censored outcomes.
        short=python_games(variant,10,args.seed,0,1)
        check_equal(short,cpp_games(args,variant,10,0,2,1))
        assert short['outcomes'][5]==10
        checks.append(dict(variant=variant,games=args.games,integer_fields=list(expected),
                           exact_full_game_comparison=True,thread_counts=[1,4],
                           start_offset_batches=[mid,args.games-mid],forced_limit_test=True,
                           outcomes=expected['outcomes'],conservation_checks=expected['conservation_checks']))
    report=dict(status='passed',seed=args.seed,limit=args.limit,checks=checks,
                elapsed_seconds=time.perf_counter()-started,
                executable_sha256=hashlib.sha256(Path(args.cpp).read_bytes()).hexdigest(),
                note='Audit sample, not the research baseline. RNG and move order match C++ to compare entire games exactly.')
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--cpp',required=True)
    parser.add_argument('--games',type=int,default=1000)
    parser.add_argument('--seed',type=int,default=20261125)
    parser.add_argument('--limit',type=int,default=536)
    parser.add_argument('--output',default='analysis/results/validation_runner.json')
    run(parser.parse_args())
