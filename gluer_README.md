# Gluing pipeline v3: calibration ladder, k = 9 census entries, and entry closing

## v3 (Oct 21, evening): closing entries on the Daugherty–Ward–Ryan map

Daugherty, Ward & Ryan (Zenodo 22945442) reduce every remaining case of R(3,10) to 79 census entries
(3,9;n,e). None is publicly available as actual graphs.

**`ladder9.py`** does two things for each target entry:
1. **Generates it** and checks the count against Goedgebeur–Radziszowski 2013, Table 14.
2. **Only after a MATCH, closes it.** `close_entry.py` runs the degree-d attachment SAT check on every graph
   (the method of our degree-4 and degree-5 lemmas). The DRAT proof is streamed to disk and checked by drat-trim.

**Rungs.**

| Rung | Entry | Published | Purpose |
|---|---|---|---|
| 0 | (3,9;32,104) | 39 | close for degree 7 |
| 1 | (3,9;32,105) | 952 | close for degree 7 |
| 2 | (3,9;35,140) | 1 | C₃₅ rediscovered from scratch |
| 3 | (3,9;31,95) | 560 | close for degree 8 |
| 4 | (3,9;31,96) | 35,154 | close for degree 8 |

**Controls passed in Claude's container.**
* **Positive.** C₃₅'s own core extends, and the rebuilt graph is isomorphic to C₃₅.
* **Replay.** The degree-4 lemma comes back UNSAT VERIFIED.
* **Negative.** The 62 (3,8;26,73) graphs must all be refuted as 35-vertex extensions, since C₃₅ is unique and its
  cores have 76 edges. All finished cores so far are UNSAT VERIFIED.
* **k = 9 generation.** (3,9;24,40) = 2, matching the published count.

**Run on the Mini.** Do this after the main ladder's current rung finishes, and stop the main ladder first so the
two don't compete for cores. It is resumable.
```
nohup caffeinate -i python3 ladder9.py 0 1 > /dev/null 2>&1 &
```
`ladder9.log` gets one line per step. A line containing `EXTENSION FOUND` means stop and send it to Claude
immediately.


## What changed in v2 (Oct 21)

**The rule for choosing the root vertex.** v1 glued around the vertex whose neighbours have the largest total
degree. v2 uses Goedgebeur–Radziszowski's deficiency rule: g(u) = e − Z(u) − e(3,k−1,n−deg(u)−1). The degree
sequence bounds the sum of g over all vertices, so some vertex v has g(v) ≤ that bound / n. Its core then has at
most e(3,k−1,·) + g(v) edges. The gluer enforces "v has minimum deficiency" exactly.

For rung 1 the effect is large:

| | Core graphs |
|---|---|
| v1 | 1,182,810,746 (the 36.7 GB file); the driver was killed loading them |
| v2 | about 183,409 |

**Other changes.**
* Published e(3,7,n) lower bounds are used. Three of them are confirmed by our own runs.
* Core lists are streamed from disk, never loaded whole.
* Duplicates are removed inside each parallel job (`glue | labelg | sort -u`), then the jobs are merged, so the
  raw files stay small.
* The ladder reports **FAILED** (with the exit code) when a rung produces no count. **MISMATCH** now means a
  wrong count only.

**Verified in Claude's container before shipping.**
* geng graph-for-graph checks (3,6;13–17): all MATCH.
* Published counts:

| Case | Count | Note |
|---|---|---|
| (3,7;22) | 191 | per-edge counts 1/6/30/60/59/25/10, exact |
| (3,7;20,44–45) | 494 | |
| (3,8;26,73) | **62** | 21 min on 2 CPUs |

* Intermediate lists: (3,7;21,51–52) = 74, (3,7;19,37–38) = 428 and (3,7;21,51–53) = 791, all matching G&R's
  table.

**Installing next to v1.** Unpack into a new folder, e.g. `~/gluing2`. v1's cache keys use different edge
windows, so v2 starts with a fresh cache. Once v2 is running, the old `~/gluing` cache (82 GB) can be deleted.


**What this is.** A re-implementation of the Goedgebeur–Radziszowski "neighbourhood gluing" method. It generates
complete lists of triangle-free graphs with no large independent set ((3,k;n,e)-graphs). This is the census
tool Angeltveit used, which we could not find published. It is the route to the 30-vertex cores of the
9-regular case of R(3,10).

**Trust chain.**
* `glue.c` is checked graph for graph against nauty's `geng`, an independent generator, on every case small
  enough for geng.
* The ladder below then checks it against published counts that geng cannot reach.
* Nothing is aimed at the open problem until every rung matches.

## Steps

1. **Build.** About 1 minute. It needs a C compiler (Xcode command-line tools) and python3.
   ```
   ./build.sh
   ```
   It fetches nauty 2.8.8 (McKay & Piperno, public), builds it, and compiles `glue`. The last line should
   read `smoke test (3,5,13) = 1 (expect 1)`.

2. **Validate.** A few minutes. Every line must say MATCH, ending with `ALL MATCH`.
   ```
   python3 validate_all.py | tee validate.log
   ```
   If anything says MISMATCH, stop and send `validate.log` to Claude.

3. **Run the ladder.** Long: hours to days. It runs in the background, uses all cores, and resumes from
   `./cache` if interrupted.
   ```
   nohup python3 ladder.py > /dev/null 2>&1 &
   ```
   Progress goes to `ladder.log` (one line per rung, `MATCH` or `MISMATCH`, with time) and `ladder.trace`
   (detail).
   * The rungs run in order; to run particular rungs only, use `python3 ladder.py 0 2`.
   * Rung 0, all 191 (3,7,22)-graphs, has already matched in Claude's container (in 16 min on 2 CPUs).
   * Rung 9 (216,151 graphs) is the stretch rung: the edge count of C₃₅'s core.

## What to send back to Claude
* `validate.log`, `ladder.log`, and the tail of `ladder.trace`.
* The machine's core count and memory.
* A note if `./cache` grows past about 20 GB. It holds every intermediate list; the 10-rung run should
  stay well below that.

## Files
| File | Purpose |
|---|---|
| `glue.c` | The gluing step: given a core H, every way to attach a vertex v and its neighbours. Its header gives the exact constraints. |
| `driver.py` | Recursion with edge windows. Its header gives the completeness argument (v2): glue around a vertex of minimum deficiency. |
| `prune_alpha.c` | geng hook that discards a graph as soon as it has an independent set of size k. Used as ground truth and as the base case. |
| `edge_lp_r3k.py` | Self-contained lower bounds on e(3,k,n). Published values are used where known. |

Published targets: Goedgebeur & Radziszowski, *New computational upper bounds for Ramsey numbers R(3,k)*,
EJC 20(1) (2013) P30, Tables 12–13.
