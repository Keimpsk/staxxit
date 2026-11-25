from math import comb
from random import Random
from collections import Counter
D=((1,0),(1,-1),(0,-1),(-1,0),(-1,1),(0,1))
def dist(p): return max(abs(p[0]),abs(p[1]),abs(sum(p)))
P=[(q,r) for q in range(-6,7) for r in range(-6,7) if dist((q,r))<=6]
I=set(p for p in P if dist(p)<=5)
O={}; p=(6,0); color=0
for dq,dr in ((-1,1),(-1,0),(0,-1),(1,-1),(1,0),(0,1)):
 for j in range(6):
  O[p]=2 if j==0 else color
  if j: color=1-color
  p=(p[0]+dq,p[1]+dr)
R={p:[[(p[0]+k*dq,p[1]+k*dr) for k in range(1,12) if dist((p[0]+k*dq,p[1]+k*dr))<=6] for dq,dr in D] for p in I}
N={p:[ray[0] for ray in R[p] if ray and ray[0] in I] for p in I}
def actions(b,c):
 caps=[]; moves=[]
 for p,s in b.items():
  if p not in I or s[-1]!=c: continue
  h=len(s)
  for ray in R[p]:
   for k,t in enumerate(ray[:h],1):
    if t in b:
     if k==h and t in I and b[t][-1]!=c: caps.append(('c',p,t,0))
     break
    if t in O:
     if k==h and O[t] in (c,2): moves.append(('e',p,t,0))
     break
    moves.append(('m',p,t,0))
  if h>11:
   for t in N[p]:
    if t not in b: moves.extend(('s',p,t,k) for k in range(1,h) if s[k-1]==c)
 return caps or moves
def apply(b,a):
 typ,p,t,k=a; s=b[p]
 if typ=='s': b[p],b[t]=s[:k],s[k:]
 else: b[t]=b.get(t,())+s; del b[p]
