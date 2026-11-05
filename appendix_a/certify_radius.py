#!/usr/bin/env python3
"""
Produce an independently checkable UNSAT certificate for:
  "No triangle-free graph on 39 vertices with max degree <= 9 lies within R edge flips of
   G39_s2 and destroys all 54 independent 10-sets of G39_s2."
(Max degree <= 9 is forced by alpha <= 9, so it is no extra assumption for a witness.)
Hence: no 39-vertex triangle-free graph with alpha <= 9 lies within R flips of G39_s2.
Writes  G39_s2_radiusR.cnf  (DIMACS)  and  G39_s2_radiusR.proof  (DRUP), checked with drat-trim.
Usage: python3 certify_radius.py R
"""
import itertools, sys, subprocess, hashlib
from pysat.solvers import Cadical153
from pysat.card import CardEnc, EncType
from pysat.formula import IDPool, CNF
from extension_r310 import read, indep_sets

R = int(sys.argv[1]); n = 39
seed = read("G39_s2.edgelist", n)
tens = indep_sets(seed, 10, 10**6); assert len(tens) == 54
pool = IDPool(); cnf = CNF()
e = {(u, v): pool.id((u, v)) for u in range(n) for v in range(u + 1, n)}
E = lambda u, v: e[min(u, v), max(u, v)]
for a, b, c in itertools.combinations(range(n), 3):              # triangle-free
    cnf.append([-E(a, b), -E(a, c), -E(b, c)])
for v in range(n):                                                # degree <= 9
    cnf.extend(CardEnc.atmost([E(v, w) for w in range(n) if w != v], bound=9, vpool=pool,
                              encoding=EncType.seqcounter).clauses)
diff = [(-E(u, v) if seed[u] >> v & 1 else E(u, v)) for (u, v) in e]
cnf.extend(CardEnc.atmost(diff, bound=R, vpool=pool, encoding=EncType.totalizer).clauses)  # <= R flips
for S in tens:                                                    # every seed 10-set gets an edge
    mem = [v for v in range(n) if S >> v & 1]
    cnf.append([E(a, b) for a, b in itertools.combinations(mem, 2)])
base = f"G39_s2_radius{R}"
cnf.to_file(base + ".cnf")
with Cadical153(bootstrap_with=cnf.clauses, with_proof=True) as s:
    res = s.solve()
    print("SAT solver result:", "SAT (claim false)" if res else "UNSAT")
    if res: sys.exit(1)
    with open(base + ".proof", "w") as fh:
        fh.write("\n".join(s.get_proof()) + "\n")
for f in (base + ".cnf", base + ".proof", "G39_s2.edgelist"):
    print(f, hashlib.sha256(open(f, "rb").read()).hexdigest())
out = subprocess.run(["drat-trim-src/drat-trim", base + ".cnf", base + ".proof"], capture_output=True, text=True)
print("\n".join(l for l in out.stdout.splitlines() if l.startswith("s ") or "VERIFIED" in l or "verified" in l.lower()))
