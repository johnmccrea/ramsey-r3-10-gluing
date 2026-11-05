#!/usr/bin/env python3
"""
Degree-d interface SAT for (3,k,n)-graphs  (triangle-free, n vertices, alpha <= k-1).

Let v have degree d, N(v) = {x_1..x_d} (independent, since triangle-free), and let
H = G - N[v] be the core on n-d-1 vertices.  H is triangle-free with alpha(H) <= k-2
(else v + that set is independent).  Unknowns: A_i = N(x_i) ∩ V(H).
Constraints (exact, nothing else is free):
  * triangle-free:     each A_i is independent in H
  * max degree k-1:    |A_i| <= k-2 ;  every core vertex c lies in at most (k-1) - deg_H(c) of the A_i
  * alpha <= k-1:      an independent set avoiding v is T ⊆ N(v) plus I ⊆ H with I ∩ A_i = ∅ for
                       x_i in T.  So for every t = 1..d and every independent set I of H with
                       |I| = k - t, at most t-1 of the A_i may miss I
                       (independent sets through v are fine: alpha(H) <= k-2).
Given H, the formula is SAT iff some (3,k,n)-graph has a degree-d vertex whose core is H.
Usage:
  python3 degree_interface.py calibrate          # true decomposition of C35(1,7,11,16) must satisfy it
  python3 degree_interface.py run N K D          # core = unique (3,9,35)-graph when N-D-1 = 35
"""
import itertools, sys, subprocess, hashlib, time
import networkx as nx
from pysat.solvers import Cadical153
from pysat.card import CardEnc, EncType
from pysat.formula import IDPool, CNF

def popc(x): return bin(x).count("1")

def bits(G, nodes):
    pos = {v: i for i, v in enumerate(nodes)}; adj = [0] * len(nodes)
    for u, v in G.edges():
        if u in pos and v in pos: adj[pos[u]] |= 1 << pos[v]; adj[pos[v]] |= 1 << pos[u]
    return adj

def indep_sets_exact(adj, k):
    n = len(adj); full = (1 << n) - 1
    nadj = [(full ^ adj[i]) & ~(1 << i) for i in range(n)]
    out = []
    def rec(P, S, size):
        if size == k: out.append(S); return
        while P:
            if size + popc(P) < k: return
            v = (P & -P).bit_length() - 1; P &= ~(1 << v)
            rec(P & nadj[v], S | (1 << v), size + 1)
    rec(full, 0, 0); return out

def alpha(adj):
    k = 1
    while indep_sets_exact(adj, k + 1): k += 1   # fine for small alpha
    return k

def build_cnf(core_adj, k, d):
    m = len(core_adj); pool = IDPool(); cnf = CNF()
    a = {(i, c): pool.id(("a", i, c)) for i in range(d) for c in range(m)}
    for i in range(d):                                   # A_i independent in H
        for c in range(m):
            for c2 in range(c + 1, m):
                if core_adj[c] >> c2 & 1: cnf.append([-a[i, c], -a[i, c2]])
        cnf.extend(CardEnc.atmost([a[i, c] for c in range(m)], bound=k - 2, vpool=pool,
                                  encoding=EncType.seqcounter).clauses)
    for c in range(m):                                   # core degree cap
        room = (k - 1) - popc(core_adj[c])
        if room < 0: raise ValueError("core vertex already over degree")
        lits = [a[i, c] for i in range(d)]
        if room == 0: cnf.extend([[-l] for l in lits])
        elif room < d: cnf.extend(CardEnc.atmost(lits, bound=room, vpool=pool, encoding=EncType.seqcounter).clauses)
    counts = {}
    for t in range(2, d + 1):                            # t = 1 is automatic (alpha(H) <= k-2)
        size = k - t
        sets = indep_sets_exact(core_adj, size); counts[size] = len(sets)
        for S in sets:
            mem = [c for c in range(m) if S >> c & 1]
            # at most t-1 of the A_i miss S  <=>  every t-subset of indices has one A_i hitting S
            for T in itertools.combinations(range(d), t):
                cnf.append([a[i, c] for i in T for c in mem])
    return cnf, a, counts

def kalbfleisch():
    G = nx.circulant_graph(35, [1, 7, 11, 16]); return G

def calibrate():
    """The (3,9,35) graph itself, viewed around any vertex v (degree 8), must satisfy the
    (k=9, d=8) interface formula with its own core: positive control for the encoder."""
    G = kalbfleisch(); adj = bits(G, list(range(35)))
    assert sum(nx.triangles(G).values()) == 0
    print("C35(1,7,11,16): triangle-free, 8-regular:", set(d for _, d in G.degree()), " alpha =", alpha(adj))
    v = 0; Nv = sorted(G[v]); core = [u for u in range(35) if u != v and u not in Nv]
    cadj = bits(G, core)
    cnf, a, counts = build_cnf(cadj, 9, len(Nv))
    true = set()
    for i, x in enumerate(Nv):
        for ci, c in enumerate(core):
            if G.has_edge(x, c): true.add(a[i, ci])
    with Cadical153(bootstrap_with=cnf.clauses) as s:
        ok_true = s.solve(assumptions=[l if l in true else -l for l in a.values()])
        ok_any = s.solve()
    print(f"core = {len(core)} vertices, alpha(core) = {alpha(cadj)}; independent-set counts {counts}")
    print("true decomposition satisfies formula:", ok_true, "| formula SAT:", ok_any)
    return ok_true and ok_any

def run(n, k, d):
    m = n - d - 1
    assert (k, m) == (10, 35), "core must be the unique (3,9,35)-graph"
    H = kalbfleisch(); cadj = bits(H, list(range(35)))
    t0 = time.time()
    cnf, a, counts = build_cnf(cadj, k, d)
    print(f"(3,{k},{n}) degree-{d} interface over unique core C35(1,7,11,16): "
          f"{len(a)} interface vars, {len(cnf.clauses)} clauses; independent sets by size {counts}  ({time.time()-t0:.0f}s)")
    base = f"deg{d}_interface_n{n}"
    cnf.to_file(base + ".cnf")
    with Cadical153(bootstrap_with=cnf.clauses, with_proof=True) as s:
        res = s.solve()
        print("result:", "SAT (a degree-%d vertex is possible)" % d if res else "UNSAT (no degree-%d vertex)" % d)
        if res:
            m_ = set(l for l in s.get_model() if l > 0)
            print("A_i sizes:", [sum(1 for c in range(35) if a[i, c] in m_) for i in range(d)])
            return
        open(base + ".proof", "w").write("\n".join(s.get_proof()) + "\n")
    out = subprocess.run(["drat-trim-src/drat-trim", base + ".cnf", base + ".proof"], capture_output=True, text=True)
    print([l for l in out.stdout.splitlines() if l.startswith("s ")])
    for f in (base + ".cnf", base + ".proof"):
        print(f, hashlib.sha256(open(f, "rb").read()).hexdigest())

if __name__ == "__main__":
    if sys.argv[1] == "calibrate": print("CALIBRATION PASSED" if calibrate() else "CALIBRATION FAILED")
    else: run(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
