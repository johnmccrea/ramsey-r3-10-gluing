#!/usr/bin/env python3
"""
Recursive generator for (3,k;n,e)-graphs with e in [elo,ehi], degrees in [dmin,Dmax], by neighbourhood gluing.

Completeness argument (Goedgebeur-Radziszowski deficiency rule, v2):
  For a (3,k;n,e)-graph G and vertex u let Z(u) = sum of degrees of u's neighbours and
      g(u) = e - Z(u) - E(k-1, n-deg(u)-1)  >= 0      (G - N[u] is a (3,k-1)-graph with e - Z(u) edges),
  where E is the lower-bound table used throughout (published values, else the counting DP).
  sum_u g(u) = n*e - sum_u (deg(u)^2 + E(k-1, n-deg(u)-1)) <= GMAX, the maximum over degree sequences
  (degrees in [dmin, Dmax], sum 2e, e in [elo, ehi]), computed exactly by DP.  So a vertex v of minimum
  deficiency has g(v) <= GMAX // n, and with d = deg(v) its core H = G - N[v] has
      E(k-1, n-d-1) <= e(H) = E(k-1, n-d-1) + g(v) <= E(k-1, n-d-1) + GMAX // n ,
  Delta(H) <= Dmax and deg_H(c) >= dmin - d.  d = 0 is included (an isolated vertex can be the minimiser).
  Gluing every such H (glue ... etab=E-table: the gluer keeps only outputs in which v has minimum deficiency,
  ties allowed) therefore produces G; every glued output is a valid member of the target family.
Base case: geng (alpha-pruned) when k <= BASEK.

Lower bounds e(3,k,n) come from published values where available (Goedgebeur-Radziszowski 2013, Table 3)
and otherwise from the self-contained counting DP in ../edge_lp_r3k.py; weaker bounds only cost time.
"""
import os, sys, subprocess, time, functools, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import edge_lp_r3k as dp
NG = os.path.join(HERE, "nauty"); GLUE = os.path.join(HERE, "glue")
CACHE = os.path.join(HERE, "cache"); os.makedirs(CACHE, exist_ok=True)
R = {3: 6, 4: 9, 5: 14, 6: 18, 7: 23, 8: 28, 9: 36, 10: 41}
PUB = {7: {15: 15, 16: 20, 17: 25, 18: 30, 19: 37, 20: 44, 21: 51, 22: 60},
       8: {8: 1, 9: 2, 10: 3, 11: 4, 12: 5, 13: 6, 14: 7, 15: 10, 16: 13, 17: 16, 18: 20, 19: 25, 20: 30,
           21: 35, 22: 42, 23: 49, 24: 56, 25: 65, 26: 73, 27: 85},
       9: {25: 46, 26: 52, 27: 61, 28: 68, 29: 77, 30: 86, 31: 95, 32: 104, 33: 118, 34: 129, 35: 140}}
BASEK = int(os.environ.get("BASEK", "6"))
JOBS = int(os.environ.get("JOBS", str(os.cpu_count() or 1)))
VERBOSE = True

def emin(k, n):
    if n < k: return 0
    if n >= R[k]: return math.inf
    v = dp.E(k, n)
    return max(v, PUB.get(k, {}).get(n, 0))

def min_sumsq(n, s, lo, hi):
    """min sum of squares of n integers in [lo,hi] summing to s (inf if impossible)."""
    if s < n * lo or s > n * hi: return math.inf
    q, r = divmod(s, n)
    return (n - r) * q * q + r * (q + 1) ** 2

def gmax(k, n, elo, ehi, dmin, Dmax, Etab):
    """max over e in [elo,ehi] and degree sequences (degrees in [dmin,Dmax]) of the total deficiency
    n*e - sum_i n_i (i^2 + E(k-1,n-i-1)).  Exact DP over (vertices, degree sum)."""
    best = -math.inf
    f = {i: i * i + Etab[i] for i in range(dmin, Dmax + 1) if Etab[i] < math.inf}
    for e in range(elo, ehi + 1):
        dp = {0: 0}
        for _ in range(n):
            nd = {}
            for s_, val in dp.items():
                for i, fi in f.items():
                    t = s_ + i
                    if t > 2 * e: continue
                    v = val + fi
                    if v < nd.get(t, math.inf): nd[t] = v
            dp = nd
        if 2 * e in dp: best = max(best, n * e - dp[2 * e])
    return best

def log(*a):
    if VERBOSE: print(*a, file=sys.stderr, flush=True)

def gen(k, n, elo, ehi, Dmax, dmin=0, depth=0):
    """Return path of a file of canonical graph6: all (3,k;n,e) graphs, elo<=e<=ehi, degrees in [dmin,Dmax]."""
    Dmax = min(Dmax, k - 1, n - 1)
    dmin = max(dmin, n - R[k - 1] if (k - 1) in R else 0, 0)
    elo = max(elo, emin(k, n), (n * dmin + 1) // 2); ehi = min(ehi, n * Dmax // 2)
    key = f"k{k}_n{n}_e{elo}-{ehi}_D{Dmax}_d{dmin}"
    path = os.path.join(CACHE, key + ".g6")
    if os.path.exists(path): return path
    ind = "  " * depth; t0 = time.time()
    if elo > ehi or dmin > Dmax:
        open(path, "w").close(); return path
    if k <= BASEK or n <= k:
        cmd = f"ALPHA_LT={k} {NG}/geng_a -tq -d{dmin} -D{Dmax} {n} {elo}:{ehi} | {NG}/labelg -q 2>/dev/null | LC_ALL=C sort -u > {path}.tmp"
        subprocess.run(cmd, shell=True, check=True); os.replace(path + ".tmp", path)
        log(f"{ind}geng  {key}: {sum(1 for _ in open(path))} graphs ({time.time()-t0:.1f}s)")
        return path
    # G&R deficiency rule: g(u) = e - Z(u) - E(k-1, n-deg(u)-1) >= 0 and sum_u g(u) = n*e - sum_u (deg^2 + E(..)),
    # which the degree sequence bounds by GMAX.  Glue around a vertex v of minimum deficiency: g(v) <= GMAX // n,
    # so its core has e(H) = E(k-1, n-d-1) + g(v) edges.  The gluer enforces "v has minimum deficiency" exactly.
    Etab = {dx: emin(k - 1, n - dx - 1) for dx in range(0, Dmax + 1)}
    gb = gmax(k, n, elo, ehi, dmin, Dmax, Etab) // n
    etab_arg = "etab=" + ",".join("x" if Etab[dx] == math.inf else str(Etab[dx]) for dx in range(0, Dmax + 1))
    raw = path + ".raw"; open(raw, "w").close()
    log(f"{ind}glue  {key}: deficiency bound {gb}")
    parts = []
    for d in range(dmin, Dmax + 1):          # d = 0 included: an isolated vertex can have minimum deficiency
        m = n - d - 1
        if m < 1 or Etab[d] == math.inf: continue
        hlo = max(Etab[d], elo - d * Dmax); hhi = min(Etab[d] + gb, ehi - d * max(dmin, 1))
        if hlo > hhi: continue
        cores = gen(k - 1, m, hlo, hhi, Dmax, max(0, dmin - d), depth + 1)
        nc = int(subprocess.run(f"wc -l < {cores}", shell=True, capture_output=True, text=True).stdout.strip() or 0)
        if nc == 0: continue
        t1 = time.time()
        J = max(1, min(JOBS, nc // 50 or 1))
        # stream the core file into J chunk files (round robin), never holding it in memory
        outs = [open(f"{raw}.in{j}", "w") for j in range(J)]
        with open(cores) as fc:
            for i, line in enumerate(fc): outs[i % J].write(line)
        for o in outs: o.close()
        args = f"{GLUE} {k} {d} {etab_arg} maxdeg={Dmax} mindeg={dmin} mine={elo} maxe={ehi}"
        procs = [subprocess.Popen(f"{args} < {raw}.in{j} 2> {raw}.err{j} | {NG}/labelg -q 2>/dev/null | LC_ALL=C sort -u > {raw}.out{j}",
                                  shell=True) for j in range(J)]
        for p in procs:
            p.wait()
            if p.returncode != 0: raise RuntimeError(f"glue pipeline failed ({p.returncode})")
        emitted = sum(int(open(f"{raw}.err{j}").read().split(", ")[1].split()[0]) for j in range(J))
        subprocess.run(f"LC_ALL=C sort -m -u {raw}.out* {raw} -o {raw}.merged && mv {raw}.merged {raw}", shell=True, check=True)
        for j in range(J):
            for suf in ("in", "out", "err"): os.remove(f"{raw}.{suf}{j}")
        parts.append(d)
        log(f"{ind}  d={d}: {nc} cores (3,{k-1};{m},{hlo}..{hhi}) -> {emitted} glued, {J} jobs ({time.time()-t1:.1f}s)")
    os.replace(raw, path)                      # raw is already canonical, sorted and duplicate-free
    log(f"{ind}=> {key}: {sum(1 for _ in open(path))} graphs ({time.time()-t0:.1f}s)")
    return path

if __name__ == "__main__":
    k, n, elo, ehi = map(int, sys.argv[1:5])
    Dmax = int(sys.argv[5]) if len(sys.argv) > 5 else k - 1
    dmin = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    p = gen(k, n, elo, ehi, Dmax, dmin)
    import collections
    cnt = collections.Counter()
    for line in open(p):
        s = line.strip(); import networkx as nx
        cnt[nx.from_graph6_bytes(s.encode()).number_of_edges()] += 1
    print(f"(3,{k};{n},e) with {elo}<=e<={ehi}, degrees in [{dmin},{Dmax}]: {sum(cnt.values())} graphs; by e: {dict(sorted(cnt.items()))}")
    print("file:", p)
