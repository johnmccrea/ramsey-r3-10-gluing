#!/usr/bin/env python3
"""
Betti numbers (over F_2) of the independence complex Ind(G) for triangle-free
40-vertex graphs from several families, to test whether "beta_6 > 0" tracks
alpha = 10 versus alpha >= 11 beyond the F_5-gain family.

Families:
  circ   - 9-regular circulants Cay(Z40, S), S product-free (edge-count matched)
  bicirc - Z20 bi-circulants (random triangle-free A, B, C), degree <= 9
  search - graphs produced by today's local searches / extensions
  struct - fibre-replacement, Ramsey-product, GQ line-cycle constructions
Usage: python3 ind_homology.py [n_circ] [n_bicirc]
"""
import itertools, json, random, sys, time
import networkx as nx, gudhi
from extension_r310 import alpha, indep_sets, popc

def bits(G):
    adj = [0] * 40
    for u, v in G.edges(): adj[u] |= 1 << v; adj[v] |= 1 << u
    return adj

def betti(G):
    st = gudhi.SimplexTree()
    for c in nx.find_cliques(nx.complement(G)):     # maximal independent sets
        st.insert(c)
    st.compute_persistence(homology_coeff_field=2, persistence_dim_max=True)
    b = st.betti_numbers()
    return b, st.num_simplices()

def row(fam, name, G):
    t0 = time.time()
    a = alpha(bits(G))
    b, ns = betti(G)
    b = list(b) + [0] * (12 - len(b))
    return dict(family=fam, name=name, alpha=a, edges=G.number_of_edges(),
                maxdeg=max(d for _, d in G.degree()), betti=b[:12], simplices=ns,
                secs=round(time.time() - t0, 1))

def circulants(n_want, seed=1):
    random.seed(seed); out = []
    pairs = [(d, 40 - d) for d in range(1, 20)] + [(20,)]
    seen = set()
    for _ in range(200000):
        r = random.randint(4, 5)
        comb = random.sample(pairs, r)
        S = sorted(set(x for p in comb for x in p))
        if len(S) != 9 or tuple(S) in seen: continue
        if any((a + b) % 40 in S for a in S for b in S): continue
        seen.add(tuple(S)); out.append(S)
        if len(out) >= n_want: break
    return out

def bicirculants(n_want, seed=2):
    import r310_candidates as rc
    random.seed(seed); out = []
    while len(out) < n_want:
        A, B = rc.random_sym_set(4), rc.random_sym_set(4)
        C = set(random.sample(range(20), random.randint(3, 5)))
        if not rc.bi_triangle_free(A, B, C): continue
        G = rc.bicirculant(A, B, C)
        if max(d for _, d in G.degree()) > 9 or G.number_of_edges() < 150: continue
        out.append((sorted(A), sorted(B), sorted(C), G))
    return out

if __name__ == "__main__":
    n_circ = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    n_bi = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    rows = []
    for S in circulants(n_circ):
        G = nx.circulant_graph(40, [d for d in S if d <= 20]); rows.append(row("circ", str(S), G))
        print(json.dumps(rows[-1]), flush=True)
    for A, B, C, G in bicirculants(n_bi):
        rows.append(row("bicirc", f"{A}|{B}|{C}", G)); print(json.dumps(rows[-1]), flush=True)
    files = {"search": ["protected_cycle_s3.edgelist", "protected_none_s3.edgelist", "protected_learned_s4.edgelist",
                        "protected_matching_s2.edgelist", "bicirc_best.edgelist", "G40_flip_ext.edgelist",
                        "geometric_polished.edgelist", "hybrid_best_s4.edgelist", "hybrid_best_s0.edgelist"],
             "struct": ["fibre_candidate.edgelist", "product_best.edgelist", "geometric_best.edgelist"]}
    for fam, fl in files.items():
        for f in fl:
            try:
                G = nx.read_edgelist(f, nodetype=int); G.add_nodes_from(range(40))
                rows.append(row(fam, f, G)); print(json.dumps(rows[-1]), flush=True)
            except FileNotFoundError:
                pass
