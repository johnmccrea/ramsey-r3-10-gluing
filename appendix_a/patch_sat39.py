#!/usr/bin/env python3
"""
Corrected SAT patch search (CEGAR) on a 39-vertex near-miss, target alpha <= 9.

Fixes relative to the failed configuration:
  1. phases initialised to the SEED graph (solver's default guess is the seed, not "no edge");
  2. Hamming radius r: at most r edge flips from the seed (cardinality constraint);
  3. many lazy clauses per round (up to BATCH independent 10-sets per candidate);
  4. patch = a hitting set of all the seed's independent 10-sets, grown by coverage
     (a patch missing some 10-set is trivially hopeless: that set is frozen independent).
Outcomes are reported only as  SAT (verified graph) / UNSAT within (patch, r) / TIMEOUT.
Usage: python3 patch_sat39.py SEED_EDGELIST PATCH_SIZE RADIUS(-1 = unbounded) SECONDS
"""
import itertools, sys, time, json
import networkx as nx
from pysat.solvers import Cadical153
from pysat.card import CardEnc, EncType
from pysat.formula import IDPool
from extension_r310 import read, indep_sets, tri_count, alpha, popc, write

def greedy_patch(adj, tens, k):
    n = len(adj); rem = list(tens); P = []
    while rem:
        v = max((u for u in range(n) if u not in P), key=lambda u: sum(1 for s in rem if s >> u & 1))
        P.append(v); rem = [s for s in rem if not s >> v & 1]
    hit = len(P)
    cover = sorted(range(n), key=lambda u: -sum(1 for s in tens if s >> u & 1))
    for u in cover:
        if len(P) >= k: break
        if u not in P: P.append(u)
    return sorted(P), hit

def main(path, k, r, seconds, batch=300):
    seed = read(path, 39); n = 39; K = 10
    tens = indep_sets(seed, K, 10**6)
    P, hit = greedy_patch(seed, tens, k)
    if len(P) > k:
        return dict(k=k, r=r, outcome="INFEASIBLE_PATCH", note=f"hitting set needs {hit} > {k}")
    Pset = set(P)
    pool = IDPool()
    e = {}
    for u in range(n):
        for v in range(u + 1, n):
            e[u, v] = pool.id((u, v))
    E = lambda u, v: e[min(u, v), max(u, v)]
    s = Cadical153()
    free = [(u, v) for (u, v) in e if u in Pset or v in Pset]
    for (u, v) in e:
        if u not in Pset and v not in Pset:
            s.add_clause([E(u, v) if seed[u] >> v & 1 else -E(u, v)])
    for a, b, c in itertools.combinations(range(n), 3):
        if a in Pset or b in Pset or c in Pset:
            s.add_clause([-E(a, b), -E(a, c), -E(b, c)])
    for v in range(n):
        lits = [E(v, w) for w in range(n) if w != v]
        for cl in CardEnc.atmost(lits, bound=9, vpool=pool, encoding=EncType.seqcounter).clauses: s.add_clause(cl)
    if r >= 0:
        diff = [(-E(u, v) if seed[u] >> v & 1 else E(u, v)) for (u, v) in free]
        for cl in CardEnc.atmost(diff, bound=r, vpool=pool, encoding=EncType.totalizer).clauses: s.add_clause(cl)
    s.set_phases([E(u, v) if seed[u] >> v & 1 else -E(u, v) for (u, v) in e])
    for S in tens:                                     # seed's own 10-sets, known up front
        mem = [v for v in range(n) if S >> v & 1]
        s.add_clause([E(a, b) for a, b in itertools.combinations(mem, 2)])
    t0 = time.time(); it = 0; added = len(tens); trace = []
    while time.time() - t0 < seconds:
        it += 1
        if not s.solve():
            return dict(k=k, r=r, patch=P, hit=hit, outcome="UNSAT", iters=it, clauses=added,
                        secs=round(time.time() - t0, 1), trace=trace[-5:])
        m = s.get_model(); pos = set(l for l in m if l > 0)
        adj = [0] * n
        for (u, v), x in e.items():
            if x in pos: adj[u] |= 1 << v; adj[v] |= 1 << u
        sets = indep_sets(adj, K, batch)
        flips = sum(popc(adj[u] ^ seed[u]) for u in range(n)) // 2
        trace.append((it, len(sets), flips))
        if not sets:
            assert tri_count(adj) == 0
            a = alpha(adj); out = f"G39_patchsat_k{k}_r{r}.edgelist"; write(adj, out)
            G = nx.Graph(); G.add_nodes_from(range(n))
            G.add_edges_from((u, v) for u in range(n) for v in range(u + 1, n) if adj[u] >> v & 1)
            return dict(k=k, r=r, patch=P, hit=hit, outcome="SAT", alpha=a, flips=flips,
                        nx_triangles=sum(nx.triangles(G).values()) // 3, edges=G.number_of_edges(),
                        iters=it, clauses=added, secs=round(time.time() - t0, 1), file=out)
        for S in sets:
            mem = [v for v in range(n) if S >> v & 1]
            s.add_clause([E(a, b) for a, b in itertools.combinations(mem, 2)]); added += 1
    return dict(k=k, r=r, patch=P, hit=hit, outcome="TIMEOUT", iters=it, clauses=added,
                secs=round(time.time() - t0, 1), trace=trace[-5:])

if __name__ == "__main__":
    res = main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]))
    print(json.dumps(res), flush=True)
