#!/usr/bin/env python3
"""
Exhaustive SAT for triangle-free graphs on n vertices with alpha <= a that are invariant under a prescribed
permutation sigma of prime order p with c cycles of length p and f = n - c*p fixed points.

Any graph with an automorphism of prime order p is isomorphic to one invariant under such a sigma for some f
(relabel so the automorphism has this standard form).  So: UNSAT for every admissible f  <=>  no such graph
has an automorphism of order p.

Variables: one per orbit of vertex pairs under <sigma>.  Constraints (all implied by the problem):
  T  triangle-free (every triple, mapped to orbit variables)
  X  max degree <= a (alpha <= a forces it: a neighbourhood is independent) ; optional min degree
  A  alpha <= a, added lazily: for each independent (a+1)-set S found, the clause "some pair in S is an edge"
     for S and all its images under sigma.
UNSAT runs write the final CNF, re-solve it from scratch (command-line CaDiCaL streams the DRAT proof to disk;
pysat fallback), and check the proof with drat-trim.
Usage: python3 sym_sat.py n a p f seconds [mindeg=D] [regular=D] [noproof]
"""
import itertools, sys, time, subprocess, os
import networkx as nx
from pysat.solvers import Cadical153
from pysat.card import CardEnc, EncType
from pysat.formula import IDPool, CNF

CADICAL = os.environ.get("CADICAL", os.path.join(os.path.dirname(os.path.abspath(__file__)), "cadical", "build", "cadical"))
DRAT = os.environ.get("DRAT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "drat-trim", "drat-trim"))
n, a, p, f, secs = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5])
opts = dict(o.split("=") if "=" in o else (o, "1") for o in sys.argv[6:])
c = (n - f) // p; assert c * p + f == n and c >= 0
def sig(v):  # cycles (i,j) = i*p + j -> (i, j+1); fixed points c*p .. n-1
    if v >= c * p: return v
    i, j = divmod(v, p); return i * p + (j + 1) % p
# orbit variables for pairs
pool = IDPool(); orb = {}
for u, w in itertools.combinations(range(n), 2):
    if (u, w) in orb: continue
    x, y = u, w; var = pool.id(("o", u, w))
    for _ in range(p):
        orb[min(x, y), max(x, y)] = var; x, y = sig(x), sig(y)
E = lambda u, w: orb[min(u, w), max(u, w)]
nvar = len(set(orb.values()))
cnf = CNF(); seen = set()
def add(cl):
    key = tuple(sorted(set(cl)))
    if key in seen: return
    seen.add(key); cnf.append(list(key))
for x, y, z in itertools.combinations(range(n), 3):
    if E(x, y) in (E(x, z), E(y, z)) or E(x, z) == E(y, z):
        add([-E(x, y), -E(x, z), -E(y, z)]); continue
    add([-E(x, y), -E(x, z), -E(y, z)])
reps = [i * p for i in range(c)] + list(range(c * p, n))   # one vertex per vertex-orbit (degrees are constant on orbits)
mindeg = int(opts.get("mindeg", 0)); reg = int(opts.get("regular", 0))
for v in reps:
    lits = [E(v, w) for w in range(n) if w != v]
    # a pair inside one orbit can appear twice in v's list (v~sigma^j v and v~sigma^-j v share a variable);
    # cardinality must count neighbours, so keep duplicates (each occurrence is a distinct neighbour).
    aux = []
    for l in lits:
        t = pool.id(("dup", v, len(aux))); aux.append(t); cnf.append([-t, l]); cnf.append([t, -l])
    hi = reg if reg else a
    cnf.extend(CardEnc.atmost(aux, bound=hi, vpool=pool, encoding=EncType.seqcounter).clauses)
    lo = reg if reg else mindeg
    if lo: cnf.extend(CardEnc.atleast(aux, bound=lo, vpool=pool, encoding=EncType.seqcounter).clauses)
if reg and reg == a and "noD" not in opts:
    # d-regular with alpha = d: every N(v) is a maximum independent set, hence dominating -> diameter 2.
    # One clause per pair orbit (representative u in reps).
    done = set()
    for u in reps:
        for w in range(n):
            if w == u or E(u, w) in done: continue
            done.add(E(u, w)); ps = []
            for x in range(n):
                if x in (u, w): continue
                pv = pool.id(("p", u, w, x)); ps.append(pv)
                cnf.append([-pv, E(u, x)]); cnf.append([-pv, E(w, x)])
            cnf.append([E(u, w)] + ps)
def lexgeq(A, B, tag):
    """clauses for A >=_lex B (lists of literals, same length)."""
    prev = None
    for j, (x, y) in enumerate(zip(A, B)):
        if x == y: continue
        cnf.append([x, -y] + ([-prev] if prev else []))
        eq = pool.id(("lx", tag, j))
        cnf.append([-eq, -x, y]); cnf.append([-eq, x, -y])
        if prev: cnf.append([-eq, prev])
        cnf.append([eq, x, y] + ([-prev] if prev else [])); cnf.append([eq, -x, -y] + ([-prev] if prev else []))
        prev = eq
if c >= 2 and "nosb" not in opts:
    # Normaliser symmetry breaking (valid: these relabellings commute with sigma, map sigma-invariant
    # solutions to sigma-invariant solutions, and every orbit contains a representative satisfying both):
    #  (1) rotate each cycle i >= 1 so its connection vector to vertex 0, x_i = (E(0, ip+delta))_delta, is
    #      lexicographically maximal among its rotations;
    #  (2) order cycles 1..c-1 by x_i, non-increasing.  (Rotation choice depends only on x_i, so (2) after (1).)
    vec = {i: [E(0, i * p + dl) for dl in range(p)] for i in range(1, c)}
    for i in range(1, c):
        for r in range(1, p):
            lexgeq(vec[i], vec[i][r:] + vec[i][:r], ("rot", i, r))
    for i in range(1, c - 1):
        lexgeq(vec[i], vec[i + 1], ("ord", i))
useP = "noproof" not in opts
# The search solver logs NO proof: the certificate comes from a fresh re-solve of the final CNF (below),
# so an in-memory proof here would only cost RAM.
s = Cadical153(bootstrap_with=cnf.clauses, with_proof=False)
tag = f"n{n}_a{a}_p{p}_f{f}" + (f"_reg{reg}" if reg else "") + (f"_min{mindeg}" if mindeg else "")
print(f"[{tag}] {c} cycles of length {p} + {f} fixed; {nvar} orbit variables, {len(cnf.clauses)} clauses", flush=True)
t0 = time.time(); c0 = time.process_time(); rounds = lazy = 0; result = None; K = a + 1
# v4: the budget is CPU seconds of this process (the in-process SAT solver), so sleep or a closed lid cannot spend it
while time.process_time() - c0 < secs:
    rounds += 1
    if not s.solve(): result = "UNSAT"; break
    m = set(l for l in s.get_model() if l > 0)
    adj = [0] * n
    for (u, w), var in orb.items():
        if var in m: adj[u] |= 1 << w; adj[w] |= 1 << u
    full = (1 << n) - 1; nadj = [(full ^ adj[i]) & ~(1 << i) for i in range(n)]; sets = []
    def rec(P, S, size):
        if len(sets) >= 200: return
        if size == K: sets.append(S); return
        while P:
            if size + bin(P).count("1") < K: return
            v = (P & -P).bit_length() - 1; P &= ~(1 << v)
            rec(P & nadj[v], S | (1 << v), size + 1)
    rec(full, 0, 0)
    if not sets: result = "SAT"; break
    for S in sets:
        mem = [v for v in range(n) if S >> v & 1]
        for _ in range(p):
            cl = [E(x, y) for x, y in itertools.combinations(mem, 2)]
            key = tuple(sorted(set(cl)))
            if key not in seen:
                seen.add(key); s.add_clause(list(key)); cnf.append(list(key)); lazy += 1
            mem = [sig(v) for v in mem]
    if rounds % 20 == 0: print(f"  [{time.time()-t0:6.0f}s] round {rounds}, lazy clauses {lazy}", flush=True)
el = time.time() - t0
if result == "SAT":
    G = nx.Graph(); G.add_nodes_from(range(n)); G.add_edges_from((u, w) for (u, w), var in orb.items() if var in m)
    degs = sorted(set(d for _, d in G.degree()))
    g6 = nx.to_graph6_bytes(G, header=False).decode().strip()
    open(f"{tag}.g6", "w").write(g6 + "\n")
    extra = ""
    if n == 35: extra = f"; isomorphic to C35(1,7,11,16): {nx.is_isomorphic(G, nx.circulant_graph(35, [1, 7, 11, 16]))}"
    print(f"[{tag}] SAT in {el:.1f}s ({rounds} rounds, {lazy} lazy): degrees {degs}, edges {G.number_of_edges()}, "
          f"triangles {sum(nx.triangles(G).values())//3}{extra}\n{g6}", flush=True)
elif result == "UNSAT":
    # Certificate: re-solve the exact final CNF (base + every lazy clause) from scratch with a fresh solver,
    # so the DRUP proof refers to precisely the clauses in the written file; then check with drat-trim.
    s.delete(); del seen                       # free the search solver before the re-solve
    with open(tag + ".cnf", "w") as fh:        # stream the final CNF to disk
        nv = max(abs(l) for cl in cnf.clauses for l in cl)
        fh.write(f"p cnf {nv} {len(cnf.clauses)}\n")
        for cl in cnf.clauses: fh.write(" ".join(map(str, sorted(set(cl)))) + " 0\n")
    if not useP: print(f"[{tag}] UNSAT in {el:.1f}s ({rounds} rounds, {lazy} lazy); no proof logged"); sys.exit()
    clauses = cnf.clauses; del cnf
    t1 = time.time()
    if os.path.exists(CADICAL):
        # command-line CaDiCaL streams its (binary DRAT) proof straight to disk: no proof in RAM
        rc = subprocess.run([CADICAL, "-q", tag + ".cnf", tag + ".proof"], capture_output=True, text=True).returncode
        if rc == 10: print(f"[{tag}] *** INCONSISTENCY: incremental UNSAT but fresh solve SAT ***", flush=True); sys.exit(1)
        if rc != 20: print(f"[{tag}] FAILED: cadical exit code {rc}", flush=True); sys.exit(1)
        how = "cadical-cli"
    else:
        with Cadical153(bootstrap_with=[sorted(set(cl)) for cl in clauses], with_proof=True) as s2:
            if s2.solve(): print(f"[{tag}] *** INCONSISTENCY: incremental UNSAT but fresh solve SAT ***", flush=True); sys.exit(1)
            open(tag + ".proof", "w").write("\n".join(s2.get_proof()) + "\n")
        how = "pysat"
    del clauses
    out = subprocess.run([DRAT, tag + ".cnf", tag + ".proof"], capture_output=True, text=True).stdout
    print(f"[{tag}] UNSAT in {el:.1f}s ({rounds} rounds, {lazy} lazy); fresh re-solve ({how}) {time.time()-t1:.1f}s; drat-trim:",
          [l for l in out.splitlines() if l.startswith("s ")], flush=True)
else:
    print(f"[{tag}] TIMEOUT after {time.process_time()-c0:.0f} CPU-s ({el:.0f}s wall; {rounds} rounds, {lazy} lazy)", flush=True)
