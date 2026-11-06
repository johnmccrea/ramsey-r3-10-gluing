# Neighbourhood gluing and a certified nonextension result for R(3,10)

> The paper is forthcoming on arXiv; this note will be replaced by its link.

Code for the paper *Neighbourhood Gluing and a Certified Nonextension Result for R(3,10)*
by John McCrea (2026). The data and certificates are on Zenodo:
[doi:10.5281/zenodo.23928054](https://doi.org/10.5281/zenodo.23928054).

**The result.** No (3,10;40)-graph has a vertex v of degree 7 for which G − N[v] has exactly 104
edges. Equivalently, none of the 39 (3,9;32,104)-graphs extends through a degree-7 vertex. Each of the
39 cases is refuted by a SAT solver (CaDiCaL 3.0.1) with a DRAT proof checked by `drat-trim`.

**Why 39 cases suffice.** Goedgebeur and Radziszowski counted exactly 39 isomorphism classes of
(3,9;32,104)-graphs. Our census contains 39 valid, pairwise non-isomorphic representatives, so it is the
whole class.

## What's here

| File | Role |
|---|---|
| `glue.c`, `prune_alpha.c`, `driver.py`, `edge_lp_r3k.py` | The neighbourhood gluer (after Goedgebeur and Radziszowski, 2013) |
| `gluer_README.md` | The gluer's own working notes, as used during the run |
| `build.sh` | Builds nauty 2.8.8, the gluer, CaDiCaL and drat-trim |
| `validate_all.py` | Reproduces published counts; every line must read MATCH |
| `ladder9.py` | Rebuilds the (3,9;32,104) census; must print 39, MATCH |
| `census_k9_n32_e104-104_D8_d4.g6` | The 39 graphs, identical up to isomorphism to the House of Graphs list. SHA-256: `0b02ea53233469cb288783c951d8b288fd8616810d034ff469048da904afcdbe` |
| `degree_interface.py` | The SAT encoding of the degree-7 extension problem |
| `close_entry_v2.py` | The certified-exclusion harness: solves, checks and audits all 39 cases |
| `regen_cnf.py` | Regenerates each certified formula and compares its hash with the run record |
| `TESTS.md` | Positive and negative controls for the harness |
| `split8/` | Scripts that split the degree-8 stage into 835 chunks, ran them on two machines and merged the results; `manifest.txt` fixes the chunks |
| `close_entry.py` | The first version of the closing harness (v1), superseded by `close_entry_v2.py`; kept for the record |
| `requirements.txt` | Python packages, pinning PySAT 1.9.dev16 (the formula hashes depend on it) |
| `PROVENANCE.txt`, `SHA256SUMS` | Where each production file came from, and every file's fingerprint |
| `appendix_a/` | Approaches that failed (paper, Appendix A), with their own README |
| `symmetry/` | Our runs on previously reported symmetry cases, not claimed in the paper; see its README |

## Setup

From the repository root, with Python 3:
```
python3 -m pip install -r requirements.txt
```
You also need `zstd` to unpack the Zenodo archives (Linux: the `zstd` package; macOS: `brew install zstd`),
and, to re-check the proofs, `drat-trim` at the commit we used:
```
git clone https://github.com/marijnheule/drat-trim.git
git -C drat-trim checkout 2e3b2dc0ecf938addbd779d42877b6ed69d9a985
make -C drat-trim drat-trim
```

## Checking the certificates (hours)

Download the Zenodo record and copy its files into the repository root. Run every command below
from there.

1. The deposit's `README.txt` gives the archive hashes and shows how to unpack the archives and
   re-check one proof. To re-check all 39 proofs, unpack the formulas and proofs as it describes, then
   run:

   ```
   for c in close_v2_run1/cores/*.cnf; do ./drat-trim/drat-trim "$c" "${c%.cnf}.drat" -t 1000000 | grep '^s '; done
   ```
   Each of the 39 lines must read `s VERIFIED`. This takes hours.
2. To check that each certified formula is exactly what the encoder produces from its graph, unpack
   the records archive and copy its `results.jsonl` next to the scripts:

   ```
   zstd -dc rung0_v2run1_records.tar.zst | tar -xf -
   cp close_v2_run1/results.jsonl .
   python3 regen_cnf.py census_k9_n32_e104-104_D8_d4.g6 results.jsonl
   ```
   It must end with `39 of 39 census graphs checked, 39 records match or reproduce, 0 problems -> ALL MATCH`.
   This takes about ten minutes. We have reproduced it on macOS (Python 3.9) and on Linux (Python
   3.13) with PySAT 1.9.dev16 from PyPI: the hashes depend on the PySAT version, not on the operating
   system or the Python version.

## Regenerating everything (days to weeks)

`build.sh` is the production script and is shipped unchanged, but it fetches the latest CaDiCaL and
drat-trim and an unpinned PySAT. To reproduce the toolchain recorded in each `run.json`, pin them
first, from the repository root:

```
git clone https://github.com/arminbiere/cadical.git && git -C cadical checkout rel-3.0.1
git clone https://github.com/marijnheule/drat-trim.git
git -C drat-trim checkout 2e3b2dc0ecf938addbd779d42877b6ed69d9a985
python3 -m pip install -r requirements.txt
```
`build.sh` then builds from these clones (skip the drat-trim lines if you already cloned it during
setup). nauty 2.8.8 is already pinned. The SHA-256 of each tool binary is recorded in each `run.json`.

Then:

```
./build.sh
python3 validate_all.py
python3 ladder9.py 0
python3 close_entry_v2.py cache/k9_n32_e104-104_D8_d4.g6 10 7 \
    --expect-count 39 --expect-m 32 --expect-e 104 --jobs 9 --out run1
python3 close_entry_v2.py cache/k9_n32_e104-104_D8_d4.g6 10 7 \
    --expect-count 39 --expect-m 32 --expect-e 104 --jobs 9 --out run1 --audit
```

`ladder9.py 0` runs the first closing harness (`close_entry.py`, about three hours) automatically after
it prints MATCH, before it returns, so it can look as if it has hung.

For scale: the whole census took about 11 days (21 October to 1 November 2026), of which the
degree-8 gluing stage, split across a Mac mini and a MacBook Air, took about six and a half days. The closing step took
about three hours on the Mac mini with nine jobs in parallel (`--jobs 9`; the default is one fewer than
the number of CPU cores). On a single Mac, from an empty cache, expect about two weeks for the census:
the degree-8 stage alone ran at about four chunks an hour on the Mac mini.

## Notes on the production run

* **Every production file is byte-for-byte what ran;** `regen_cnf.py`, `requirements.txt` and the
  READMEs were written afterwards. `SHA256SUMS` lists each file's fingerprint, and the closing-step
  files match the Zenodo deposit.
* **One step was done by hand.** After the gluer was stopped on 24 October, the list of 8,343
  23-vertex graphs that the degree-8 stage starts from was finished by hand, by the same merge that
  `driver.py` performs (`LC_ALL=C sort -m -u`). The result is byte-identical to what the driver would
  have produced, since that stage added no graphs.
* **A known weakness in `driver.py`.** Its pipelines (lines 82 and 111) don't use `pipefail`. A gluer
  crash is caught, because the driver parses each job's final summary, but a failure of `labelg` (or of
  `geng` in the base cases) could silently truncate a stage's output. The stages before degree 8 ran on
  this driver; each was checked against its published count, which would catch such a loss.
  The degree-8 stage ran through `split8/run_one.sh`, which does use `pipefail`. We ship `driver.py`
  unchanged because it is what ran; any fix will come as a separate, labelled change.

## How this was made

The work was directed by one non-mathematician collaborating with several AI systems; Claude wrote
most of the code. The paper's closing section describes how. Licence: MIT (code). The data and
certificates on Zenodo are CC BY 4.0.
