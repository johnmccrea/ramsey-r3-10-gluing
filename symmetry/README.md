# Symmetry runs (not claimed in the paper)

While building the gluing pipeline we ran our own SAT encodings on some of the automorphism cases
already settled by Chen and by Unsolved Lab: automorphisms of prime order 7 with 5 fixed points, and of
prime order p >= 11, for a (3,10;40)-graph with minimum degree at least 5. These would replicate
published results, and not every run ended in a confirmed certificate, so the paper claims nothing from
them. They are here for transparency.

* `sym_sat.py`: the encoder in its later form. Its docstring explains how a permutation of each cycle
  type (c cycles of length p, f fixed points) is fixed, and why that loses no generality.
* `sym_sat_oct20.py` and `batch40.sh`: the earlier version and the batch script that produced
  `batch40.log` on October 20, 2026. That log shows the outcome of each case as run. Of the cases
  above, most proofs verified, four did not (marked `s NOT VERIFIED`), and one, (p, f) = (19, 21), timed
  out; the log also has exploratory runs for p = 3, 5 and 7 outside that scope, four of which timed
  out. Some cases were later re-run with the newer encoder and sent for an independent check, which
  was not completed; the logs of those re-runs are not included. We make no claim about any of these
  cases, including those that verified, such as (7, 5): they would only replicate published results.
* The scripts are as they ran, so they contain paths from the machine they ran on (`batch40.sh`
  changes into `/home/claude/sym`; `sym_sat_oct20.py` has a default `drat-trim` path). Set the
  `DRAT` environment variable (and, for `sym_sat.py`, `CADICAL`), or edit those lines, to run them
  elsewhere.
