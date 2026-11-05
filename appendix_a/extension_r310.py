#!/usr/bin/env python3
"""
One-vertex extension search: G39 (triangle-free, alpha <= 9)  ->  G40 = G39 + v.

EXTENSION CONDITION
  Adding v with neighbourhood S keeps the graph triangle-free iff S is independent.
  G40 has an independent 10-set iff some independent 9-set I of G39 has I ∩ S = ∅
  (then I + v is independent); G39 itself has none.  So
      v extends G39 to a (3,10)-graph  <=>  S is an INDEPENDENT TRANSVERSAL
                                           of the family of independent 9-sets of G39.
  (|S| <= 9 automatically, since S is independent in G39.)

PIPELINE
  1. obtain G39 with alpha <= 9: delete a vertex from an alpha = 10 graph on 40
     vertices and run triangle-free local search on 39 vertices (minimise the
     number of independent 10-sets);
  2. enumerate all independent 9-sets of G39;
  3. SAT (CaDiCaL): x_u = [u in S];  ~x_u | ~x_w for every edge;  OR_{u in I} x_u
     for every independent 9-set I.   SAT => a (3,10)-graph on 40 vertices;
  4. otherwise MaxSAT (RC2): hard independence, soft "I is hit"; the optimum is the
     fewest independent 10-sets any one-vertex extension of this G39 can have;
  5. bounded flips: starting from the best extension, allow at most B edge flips
     (triangle-free kept) to remove the remaining 10-sets.

Usage:  python3 extension_r310.py SEARCH_SECONDS FLIP_BUDGET FLIP_SECONDS [seed]
"""
import itertools, math, random, sys, time
import networkx as nx
from pysat.solvers import Cadical153
from pysat.examples.rc2 import RC2
from pysat.formula import WCNF

def popc(x): return bin(x).count("1")

def read(path, n):
    adj = [0] * n
    for line in open(path):
        u, v = map(int, line.split()); adj[u] |= 1 << v; adj[v] |= 1 << u
    return adj

def write(adj, path):
    n = len(adj)
    with open(path, "w") as fh:
        for u in range(n):
            for v in range(u + 1, n):
                if adj[u] >> v & 1: fh.write(f"{u} {v}\n")

def tri_count(adj):
    n = len(adj)
    return sum(popc(adj[u] & adj[v]) for u in range(n) for v in range(u + 1, n) if adj[u] >> v & 1) // 3

def indep_sets(adj, k, cap):
    n = len(adj); full = (1 << n) - 1
    nadj = [(full ^ adj[i]) & ~(1 << i) for i in range(n)]
    out = []
    def rec(P, size, S):
        if len(out) >= cap: return
        if size == k: out.append(S); return
        while P:
            if size + popc(P) < k: return
            v = (P & -P).bit_length() - 1; P &= ~(1 << v)
            rec(P & nadj[v], size + 1, S | (1 << v))
    rec(full, 0, 0); return out

def alpha(adj):
    k = 1
    while indep_sets(adj, k + 1, 1): k += 1
    return k

def delete_vertex(adj, v):
    keep = [u for u in range(len(adj)) if u != v]; pos = {u: i for i, u in enumerate(keep)}
    out = [0] * len(keep)
    for u in keep:
        for w in keep:
            if adj[u] >> w & 1: out[pos[u]] |= 1 << pos[w]
    return out

# ---------------- triangle-free local search (any n) ----------------
def local_search(adj, seconds, seed, K=10, temp=6.0, cap=4000, frozen=None, budget=None, ref=None):
    """Minimise #independent K-sets.  Moves keep triangle-free and degree <= 9.
    frozen: set of vertex pairs never touched; budget/ref: max Hamming distance to ref."""
    random.seed(seed); n = len(adj); adj = adj[:]
    frozen = frozen or set()
    def dist(a):
        return sum(popc(a[u] ^ ref[u]) for u in range(n)) // 2 if ref else 0
    sets = indep_sets(adj, K, cap); f = len(sets)
    best_f, best = f, adj[:]; t0 = time.time(); step = 0; tabu = {}
    while time.time() - t0 < seconds and best_f > 0 and sets:
        step += 1
        S = random.choice(sets); mem = [v for v in range(n) if S >> v & 1]
        u, v = random.sample(mem, 2)
        if (min(u, v), max(u, v)) in frozen: continue
        new = adj[:]; new[u] |= 1 << v; new[v] |= 1 << u; ok = True
        common = new[u] & new[v]
        while common and ok:
            w = (common & -common).bit_length() - 1; common &= common - 1
            opts = [a for a in (u, v) if (min(a, w), max(a, w)) not in frozen and tabu.get((min(a, w), max(a, w)), -1) < step]
            if not opts: ok = False; break
            a = random.choice(opts); new[a] &= ~(1 << w); new[w] &= ~(1 << a)
        for a in (u, v):
            while ok and popc(new[a]) > 9:
                cand = [w for w in range(n) if new[a] >> w & 1 and w not in (u, v) and (min(a, w), max(a, w)) not in frozen]
                if not cand: ok = False; break
                w = random.choice(cand); new[a] &= ~(1 << w); new[w] &= ~(1 << a)
        if not ok or (budget is not None and dist(new) > budget): continue
        nsets = indep_sets(new, K, cap); nf = len(nsets)
        if nf <= f or random.random() < math.exp(-(nf - f) / temp):
            adj, f, sets = new, nf, nsets; tabu[(min(u, v), max(u, v))] = step + 15
            if f < best_f:
                best_f, best = f, adj[:]
                print(f"    [{time.time()-t0:6.0f}s step {step}] independent {K}-sets = {f}", flush=True)
        if f > 2 * best_f + 150: adj, f = best[:], best_f; sets = indep_sets(adj, K, cap)
    return best, best_f

# ---------------- extension: SAT / MaxSAT ----------------
def extension_sat(adj39, nine):
    n = len(adj39); x = lambda u: u + 1
    s = Cadical153()
    for u in range(n):
        for w in range(u + 1, n):
            if adj39[u] >> w & 1: s.add_clause([-x(u), -x(w)])
    for I in nine: s.add_clause([x(u) for u in range(n) if I >> u & 1])
    if s.solve():
        return [u for u in range(n) if s.get_model()[u] > 0]
    return None

def extension_maxsat(adj39, nine):
    n = len(adj39); x = lambda u: u + 1
    w = WCNF()
    for u in range(n):
        for v in range(u + 1, n):
            if adj39[u] >> v & 1: w.append([-x(u), -x(v)])
    for I in nine: w.append([x(u) for u in range(n) if I >> u & 1], weight=1)
    with RC2(w) as rc:
        m = rc.compute(); return [u for u in range(n) if m[u] > 0], rc.cost

def add_vertex(adj39, S):
    n = len(adj39); adj = adj39[:] + [0]
    for u in S: adj[u] |= 1 << n; adj[n] |= 1 << u
    return adj

def report(adj, label):
    degs = sorted({popc(a) for a in adj}); a = alpha(adj)
    print(f"  {label}: n={len(adj)} edges={sum(popc(r) for r in adj)//2} degrees={degs} "
          f"triangles={tri_count(adj)} alpha={a} (exact) #indep {a}-sets={len(indep_sets(adj, a, 10**6))}")
    G = nx.Graph(); G.add_nodes_from(range(len(adj)))
    G.add_edges_from((u, v) for u in range(len(adj)) for v in range(u + 1, len(adj)) if adj[u] >> v & 1)
    assert sum(nx.triangles(G).values()) == 0
    return a

if __name__ == "__main__":
    search_s = float(sys.argv[1]); budget = int(sys.argv[2]); flip_s = float(sys.argv[3])
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    src = sys.argv[5] if len(sys.argv) > 5 else "protected_cycle_s3.edgelist"
    G40 = read(src, 40)
    tens = indep_sets(G40, 10, 10**6)
    v0 = max(range(40), key=lambda v: sum(1 for s in tens if s >> v & 1))
    adj39 = delete_vertex(G40, v0)
    print(f"STEP 1: {src} minus vertex {v0}: independent 10-sets left = {len(indep_sets(adj39, 10, 10**6))}")
    adj39, f = local_search(adj39, search_s, seed)
    a39 = report(adj39, "G39 after search")
    write(adj39, f"G39_s{seed}.edgelist")
    if a39 > 9:
        print("  could not reach alpha <= 9 on 39 vertices; extension step skipped"); sys.exit()
    nine = indep_sets(adj39, 9, 10**7)
    print(f"STEP 2: independent 9-sets of G39: {len(nine)}")
    S = extension_sat(adj39, nine)
    if S is not None:
        G = add_vertex(adj39, S); print(f"STEP 3: SAT -- independent transversal S={S}")
        report(G, "G40"); write(G, f"G40_ext_s{seed}.edgelist"); sys.exit()
    print("STEP 3: UNSAT -- no independent set of G39 meets every independent 9-set "
          "(no pure one-vertex extension exists)")
    S, cost = extension_maxsat(adj39, nine)
    G = add_vertex(adj39, S)
    print(f"STEP 4: MaxSAT optimum: best S={S} (|S|={len(S)}) misses {cost} of {len(nine)} 9-sets")
    report(G, "best pure extension")
    write(G, f"G40_pure_s{seed}.edgelist")
    print(f"STEP 5: repair with at most {budget} edge flips")
    G2, f2 = local_search(G, flip_s, seed + 100, budget=budget, ref=G)
    report(G2, f"after <= {budget} flips")
    write(G2, f"G40_flip_s{seed}.edgelist")
