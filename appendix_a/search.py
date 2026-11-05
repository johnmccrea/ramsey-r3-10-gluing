import itertools, sys
from math import gcd
N=40
def alpha_ge(adj, k):
    # adj: list of int bitmasks; check independent set of size k exists (complement clique)
    n=len(adj); full=(1<<n)-1
    nadj=[(full ^ adj[i]) & ~(1<<i) for i in range(n)]
    best=[0]
    def rec(P, size):
        if size>best[0]: best[0]=size
        if size>=k: return True
        if size+bin(P).count('1')<k: return False
        while P:
            if size+bin(P).count('1')<k: return False
            v=(P&-P).bit_length()-1
            if rec(P & nadj[v], size+1): return True
            P&=~(1<<v)
        return False
    return rec(full,0)
def alpha(adj):
    k=1
    while alpha_ge(adj,k+1): k+=1
    return k
# Cayley graphs on abelian groups given as tuples of moduli
def group(mods):
    els=list(itertools.product(*[range(m) for m in mods]))
    idx={e:i for i,e in enumerate(els)}
    add=lambda a,b: tuple((x+y)%m for x,y,m in zip(a,b,mods))
    neg=lambda a: tuple((-x)%m for x,m in zip(a,mods))
    return els,idx,add,neg
def run(mods, maxdeg=9, mindeg=4):
    els,idx,add,neg=group(mods)
    zero=els[0]
    pairs=[];seen=set()
    for e in els[1:]:
        if e in seen: continue
        seen.add(e);seen.add(neg(e))
        pairs.append(tuple(sorted({e,neg(e)})))
    best=(99,None);count=0;hits=[]
    for r in range(1,len(pairs)+1):
        for comb in itertools.combinations(pairs,r):
            S=set(x for p in comb for x in p)
            d=len(S)
            if d>maxdeg: continue
            if d<mindeg: continue
            # triangle-free: no a,b in S with a+b in S
            if any(add(a,b) in S for a in S for b in S): continue
            count+=1
            adj=[0]*len(els)
            for i,g in enumerate(els):
                for s in S: adj[i]|=1<<idx[add(g,s)]
            if not alpha_ge(adj,10):
                hits.append(S); print("HIT",mods,sorted(S)); sys.stdout.flush()
            a=alpha(adj) if d>=7 else None
            if a is not None and a<best[0]: best=(a,sorted(S))
    print(mods,"sum-free sets tested:",count,"best alpha:",best,"hits:",len(hits))
if __name__=='__main__':
    for mods in [(40,),(2,20),(2,2,10)]:
        run(mods)
