# Symmetry runs (not claimed in the paper)

While building the gluing pipeline we ran our own SAT encodings on some of the automorphism cases
already settled by Chen and by Unsolved Lab: automorphisms of prime order 7 with 5 fixed points, and of
prime order p >= 11, for a (3,10;40)-graph with minimum degree at least 5. These replicate published
results, and not every run ended in an independently confirmed certificate, so the paper claims nothing
from them. They are here for transparency.

* `sym_sat.py`: the encoder as sent for independent review on Oct 27, 2026. Its docstring explains how
  a permutation of each cycle type (c cycles of length p, f fixed points) is fixed, and why that loses
  no generality.
* `sym_sat_oct20.py` and `batch40.sh`: the earlier version and the batch script that produced
  `batch40.log` on Oct 20. In that log, four proofs failed to verify and one case timed out; those
  cases were later re-run with the newer encoder.
* Status as of Nov 4, 2026: an independent reviewer (ChatGPT) confirmed 12 of the 14 configurations
  for p >= 11; (11,18) and (19,21) were not confirmed. The order-7 case (7,5) is also unclaimed.
