from staxxit_analysis import I,O,N,actions,apply
from collections import Counter
from random import Random
import argparse,json
def legal(b,res,c,variant):
 if not res[c] and (variant=='new' or not any(res)): return actions(b,c)
 if not res[c]: return []
 active=set(b)&I
 places={t for p in active for t in N[p] if t not in b} if active else {(0,0)}
 a=[('p',None,t,0) for t in sorted(places)]
 if variant=='new': a += [x for x in actions(b,c) if x[0]=='c']
 return a
def step(b,res,c,a):
 if a[0]=='p': b[a[2]]=(c,); res[c]-=1
 else: apply(b,a)
def result(b,res):
 if not any(res[c]==0 and not any(p in I and s[-1]==c for p,s in b.items()) for c in (0,1)): return None
 scores=[(sum(s[-1]==c for p,s in b.items() if p in O),sum(len(s) for p,s in b.items() if p in O and s[-1]==c)) for c in (0,1)]
 return 'white' if scores[0]>scores[1] else 'black' if scores[1]>scores[0] else 'draw'
def game(rng,variant,limit=536):
 b={}; res=[18,18]; c=0; seen=Counter(); passes=0; counts=Counter(); choices=Counter(); turns=Counter(); first=None
 for turn in range(limit):
  key=(c,tuple(res),tuple(sorted(b.items()))); seen[key]+=1
  if seen[key]>=3: return 'repeat',turn,counts,choices,turns,first
  a=legal(b,res,c,variant); phase='reserve' if res[c] else 'full'; choices[phase]+=len(a); turns[phase]+=1
  if not a:
   passes+=1
   if passes==2: return 'blocked',turn+1,counts,choices,turns,first
  else:
   passes=0; move=rng.choice(a); counts[move[0]]+=1
   if phase=='reserve' and move[0]=='c': counts['early_capture']+=1
   step(b,res,c,move)
   if first is None and not res[c]: first=c
   assert all(sum(s.count(v) for s in b.values())+res[v]==18 for v in (0,1))
   end=result(b,res) if variant=='new' or not any(res) else None
   if end: return end,turn+1,counts,choices,turns,first
  c=1-c
 return 'limit',limit,counts,choices,turns,first
def run(n,variant,seed):
 rng=Random(seed); outcomes=Counter(); counts=Counter(); choices=Counter(); turns=Counter(); duration=0; firstwins=Counter()
 for _ in range(n):
  o,t,k,a,p,f=game(rng,variant); outcomes[o]+=1; duration+=t; counts.update(k); choices.update(a); turns.update(p)
  if f is not None: firstwins['first_empty']+=1; firstwins['won']+=o==('white' if f==0 else 'black')
 return dict(variant=variant,n=n,seed=seed,outcomes=outcomes,mean_turns=duration/n,actions=counts,choices=choices,turns=turns,first=firstwins)
if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--n',type=int,default=1000); p.add_argument('--seed',type=int,default=42); a=p.parse_args()
 print(json.dumps([run(a.n,v,a.seed) for v in ('original','new')],indent=2))
