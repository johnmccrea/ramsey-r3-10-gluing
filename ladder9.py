#!/usr/bin/env python3
"""
k = 9 ladder: generate (3,9;n,e) census entries on Daugherty-Ward-Ryan's map, check each count against
Goedgebeur-Radziszowski (2013) Table 14, and -- only after a MATCH -- close the entry for R(3,10):
no (3,10)-graph on 40 vertices has a vertex of degree d = 39 - n whose non-neighbourhood is one of these graphs.
Closing runs close_entry.py (degree-d interface SAT per core, DRAT proof checked by drat-trim).
Entries closed this way rely on the census being complete; the published count is the external check on that.
Results: ladder9.log (one line per step).  usage: python3 ladder9.py [rung indices...]
"""
import os, sys, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
RUNGS = [  # (n, e, published count, close as degree d of a 40-vertex (3,10)-graph?  None = calibration only)
    (32, 104, 39, 7),          # case 7, cheapest open entry (~35k (3,8)-cores to generate)
    (32, 105, 952, 7),         # case 7
    (35, 140, 1, None),        # C35 rediscovered from scratch (calibration; d would be 4 = our degree-4 lemma)
    (31, 95, 560, 8),          # case 8
    (31, 96, 35154, 8),        # case 8
]
only = set(sys.argv[1:])
with open(os.path.join(HERE, "ladder9.log"), "a") as log, open(os.path.join(HERE, "ladder9.trace"), "a") as tr:
    def out(line):
        print(line, flush=True); log.write(line + "\n"); log.flush()
    for i, (n, e, pub, d) in enumerate(RUNGS):
        if only and str(i) not in only: continue
        t0 = time.time()
        p = subprocess.run([sys.executable, "-W", "ignore", os.path.join(HERE, "driver.py"), "9", str(n), str(e), str(e)],
                           stdout=subprocess.PIPE, stderr=tr, text=True)
        lines = p.stdout.splitlines()
        first = lines[0] if lines else ""
        got = first.split(": ")[1].split(" graphs")[0] if " graphs" in first else "?"
        path = next((l.split("file: ")[1] for l in lines if l.startswith("file: ")), None)
        verdict = (f"FAILED (driver exit {p.returncode}, no count produced)" if got == "?" else
                   "MATCH" if got == str(pub) else "MISMATCH")
        out(f"rung {i}: (3,9;{n},{e})  ours {got}  published {pub}  {verdict}  {time.time()-t0:.0f}s  file {path}")
        if n == 35 and verdict == "MATCH":
            import networkx as nx
            G = nx.from_graph6_bytes(open(path).readline().strip().encode())
            out(f"rung {i}: isomorphic to C35(1,7,11,16): {nx.is_isomorphic(G, nx.circulant_graph(35, [1, 7, 11, 16]))}")
        if d is None or verdict != "MATCH": continue
        t1 = time.time()
        c = subprocess.run([sys.executable, "-W", "ignore", os.path.join(HERE, "close_entry.py"), path, "10", str(d)],
                           stdout=subprocess.PIPE, stderr=tr, text=True)
        summary = c.stdout.strip().splitlines()[-1] if c.stdout.strip() else f"FAILED (exit {c.returncode})"
        out(f"rung {i}: close (3,10;40) degree-{d} vertex with core (3,9;{n},{e}): {summary}  {time.time()-t1:.0f}s")
        if "EXTENSION FOUND" in c.stdout:
            out("*** A (3,10;40) EXTENSION WAS FOUND -- possible witness; stop and send ladder9.log to Claude ***")
