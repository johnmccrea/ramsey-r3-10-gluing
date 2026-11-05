# close_entry_v2.1: tests run by Claude-Main, Nov 1 2026 (cloud container; CaDiCaL 3.0.1, drat-trim)

Fixes for ChatGPT's three v2 blockers, each re-run as an attack:
- Fake checker that prints "s VERIFIED" but exits 7: REFUSED at start-up acceptance.
- Fake checker that prints "c trivial UNSAT / s VERIFIED" and exits 1: REFUSED (our own unit propagation does not
  refute the acceptance formula).
- Proof deleted after success, then resume: detected (0 already done), core re-solved; old record counted as an error.
- CNF altered after success, then resume: detected, re-solved.
- python -O with an invalid census: REFUSED ("census: 1 cores, expected 2"). All safety checks now use require().
Also: acceptance tests now run in binary proof mode (production) and text mode; drat-trim transcript kept and
hashed per core; Python, networkx, PySAT and platform versions recorded; --audit re-runs drat-trim on every stored
proof before the verdict.

A finding from reading drat-trim's source (main(), drat-trim.c): it exits 0 only after a full verification; when
the formula is refuted by unit propagation alone ("c trivial UNSAT") it prints "s VERIFIED" yet exits 1; and its
timeout and out-of-memory paths call exit(0) without printing "s VERIFIED". Hence the rule: require the
"s VERIFIED" line AND (exit 0, OR "c trivial UNSAT" with exit 1 confirmed by our own unit propagation).

Controls (unchanged from v2), small census of all (3,4;8)-graphs from nauty geng (3 graphs, e = 10, 11, 12):
- Positive: (3,5;13), d = 4, core e = 10: SAT_WITNESS; decoded graph independently re-checked (13 vertices,
  triangle-free, alpha 4). PASS.
- Negative: (3,5;14), d = 5, each core: UNSAT_VERIFIED (trivial UNSAT path), ENTRY CLOSED. PASS (R(3,5) = 14).
- Resume with --audit: skips intact cores, re-checks proofs, ENTRY CLOSED. PASS.
- Different census in the same output directory: REFUSED. PASS.
