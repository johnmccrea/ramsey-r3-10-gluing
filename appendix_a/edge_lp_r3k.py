#!/usr/bin/env python3
"""
Pure-counting lower bounds on e(3,k,n) = min #edges of a triangle-free graph on n
vertices with alpha < k  (a "(3,k,n)-graph"), by the classical degree-sequence argument.

For a (3,k,n)-graph G and a vertex v of degree d:
  * N(v) is independent           ->  d <= k-1
  * G_v = G - N[v] is a (3,k-1,n-d-1)-graph  ->  n-d-1 < R(3,k-1)
  * e(G_v) = e(G) - Z_v,  Z_v = sum of degrees over N(v)   (N(v) independent, no triangles)
Summing over v (sum_v Z_v = sum_u deg(u)^2):
      n*e - sum_u deg(u)^2 = sum_v e(G_v) >= sum_v E(k-1, n-deg(v)-1)
With n_d = #vertices of degree d and 2e = sum d*n_d this is
      sum_d n_d * ( n*d/2 - d^2 - E(k-1, n-d-1) ) >= 0 .
We minimise e over integer degree distributions (exact DP), recursively in k.
If no distribution is feasible, no (3,k,n)-graph exists (E = infinity).
Known values R(3,k) for k <= 9 are used only for the degree lower bound.
"""
import sys
from functools import lru_cache
R = {2: 3, 3: 6, 4: 9, 5: 14, 6: 18, 7: 23, 8: 28, 9: 36}
INF = float("inf")

@lru_cache(None)
def E(k, n):
    if n <= 0: return 0
    if k == 2: return 0 if n == 1 else (1 if n == 2 else INF)
    if k == 1: return INF
    best = INF
    dlo = max(0, n - R[k - 1]) if k - 1 in R else 0
    opts = []
    for d in range(dlo, min(k - 1, n - 1) + 1):
        sub = E(k - 1, n - d - 1)
        if sub == INF: continue
        w2 = n * d - 2 * d * d - 2 * sub          # 2 * weight
        opts.append((d, w2))
    if not opts: return INF
    # DP over vertices: state (count, total weight2, degree-sum parity) -> min degree sum
    dp = {(0, 0): 0}
    for _ in range(n):
        nd = {}
        for (W, par), s in dp.items():
            for d, w2 in opts:
                key = (W + w2, (par + d) % 2)
                if s + d < nd.get(key, INF): nd[key] = s + d
        # prune: keep best degree sum per (W, par); cap W range
        dp = nd
    for (W, par), s in dp.items():
        if W >= 0 and par == 0:
            best = min(best, s // 2)
    return best

if __name__ == "__main__":
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    lo = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    hi = int(sys.argv[3]) if len(sys.argv) > 3 else 41
    for n in range(lo, hi + 1):
        e = E(k, n); ub = n * (k - 1) // 2
        print(f"e(3,{k},{n}) >= {e}   (max possible {ub}){'   <-- contradiction: no graph' if e == INF or e > ub else ''}")
