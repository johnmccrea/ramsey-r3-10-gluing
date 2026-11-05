#!/usr/bin/env python3
"""Step 2: check the gluer and the recursive driver against independent geng generation, graph for graph.
Every line must say MATCH.  Takes a few minutes."""
import os, subprocess, time, sys
HERE = os.path.dirname(os.path.abspath(__file__)); NG = os.path.join(HERE, "nauty")
def canon_set(cmd):
    out = subprocess.run(cmd + f" | {NG}/labelg -q 2>/dev/null | LC_ALL=C sort -u", shell=True,
                         capture_output=True, text=True, check=True).stdout.split()
    return set(out)
def geng(k, n, extra=""):
    return f"ALPHA_LT={k} {NG}/geng_a -tq {extra} {n}"
ok_all = True
# (a) single-level gluing from complete core lists, vs geng
for k, n in [(4, 8), (5, 11), (5, 12), (5, 13), (6, 12), (6, 15), (6, 16), (6, 17)]:
    t0 = time.time(); truth = canon_set(geng(k, n))
    parts = [f"{geng(k-1, n-d-1, f'-D{d}')} | {HERE}/glue {k} {d}" for d in range(1, k) if n - d - 1 >= 1]
    got = canon_set("{ " + "; ".join(parts) + "; }")
    ok = got == truth; ok_all &= ok
    print(f"glue   (3,{k},{n}): geng {len(truth):>7}  glue {len(got):>7}  {'MATCH' if ok else 'MISMATCH'}  ({time.time()-t0:.0f}s)", flush=True)
# (b) recursive driver (gluing at k=6 from geng k=5 cores, minimum-deficiency rule, edge windows), vs geng
for n, lo, hi in [(17, 0, 999), (16, 0, 999), (15, 28, 31), (15, 0, 999), (14, 0, 999), (13, 0, 999)]:
    t0 = time.time(); truth = canon_set(f"ALPHA_LT=6 {NG}/geng_a -tq {n} {lo}:{hi}")
    p = subprocess.run([sys.executable, "-W", "ignore", os.path.join(HERE, "driver.py"), "6", str(n), str(lo), str(hi)],
                       capture_output=True, text=True, env={**os.environ, "BASEK": "5"}).stdout
    path = [l.split("file: ")[1] for l in p.splitlines() if l.startswith("file: ")][0]
    got = set(open(path).read().split())
    ok = got == truth; ok_all &= ok
    print(f"driver (3,6,{n}) e in [{lo},{hi}]: geng {len(truth):>7}  driver {len(got):>7}  {'MATCH' if ok else 'MISMATCH'}  ({time.time()-t0:.0f}s)", flush=True)
print("ALL MATCH" if ok_all else "*** SOME MISMATCH -- stop and send the log to Claude ***")
