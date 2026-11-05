# Appendix A: approaches that failed, with their verification artifacts

All hashes are in `SHA256SUMS`. Python 3, NetworkX, python-sat (CaDiCaL 1.5.3), drat-trim.

## 1. Abelian Cayley exhaustive search
* `abelian_cayley_search_oct.log`: output of `search.py` (regenerated 2026-10-17 UTC, identical to the original run).
* Groups ℤ₄₀, ℤ₂×ℤ₂₀, ℤ₂²×ℤ₁₀: every inverse-closed, product-free connection set S with 4 ≤ |S| ≤ 9
  (2,882 / 5,600 / 20,804 sets). Best α = 10 in each group; no set gives α ≤ 9.
* Exact α by bitset branch-and-bound (`alpha_ge` in `search.py`).

## 2. Certified bounded-distance SAT result
**Claim.** No triangle-free graph on 39 vertices with α ≤ 9 lies within 12 edge flips of
`G39_s2.edgelist` (all 741 vertex pairs free). In fact the stronger formula is UNSAT: no
triangle-free graph with max degree ≤ 9 within 12 flips puts an edge inside each of the seed's
54 independent 10-sets. (Max degree ≤ 9 is forced by α ≤ 9, so it adds no assumption.)

* Formula: `G39_s2_radius12.cnf.gz` (DIMACS). Built by `certify_radius.py 12`:
  triangle clauses, per-vertex degree ≤ 9 (sequential counter), ≤ 12 flips from the seed (totalizer),
  one clause per independent 10-set of the seed.
* Proof: `G39_s2_radius12.proof.xz` (DRUP, 434 MB uncompressed), produced by CaDiCaL.
* Check: `drat-trim G39_s2_radius12.cnf G39_s2_radius12.proof` → `s VERIFIED` (see `cert12.log`).
* Trust base: drat-trim, plus the correctness of the encoder `certify_radius.py` (short, readable).
* Radius 10 was verified the same way. The patch-size × radius grid (uncertified solver runs) is in
  `patch_grid.jsonl`, from `patch_sat39.py`.
* Note: this run is on 39 vertices directly; no embedding into 40 vertices was used.

## 3. Edge-count DP
* `edge_lp_r3k.py`: self-contained single-vertex counting; `python3 edge_lp_r3k.py 10 40 40` → e ≥ 148.
* `edge_lp_published.py`: the same DP with Goedgebeur–Radziszowski (2013) exact e(3,9,n) values → e ≥ 159
  (published bound: 161).

## 4. Cross-family independence-complex homology
* `ind_homology.py`, `ind_rows.jsonl`: 132 graphs (circulants, bi-circulants, search and construction
  graphs) with α and β₀–β₁₁ of Ind(G) over 𝔽₂. Source of the "49 of 116 α ≥ 11 graphs have β₆ > 0"
  and "β₇ in α = 10 graphs" figures.

`extension_r310.py` holds shared helpers imported by several scripts.
