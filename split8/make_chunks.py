#!/usr/bin/env python3
"""split8/make_chunks.py <n23 list> [cores_per_chunk=10] [seed=20261024]
Shuffle the d=8 cores (fixed seed, so slow cores spread out) and write chunks/c0000.g6 ...
Coverage anchor: manifest.txt records N, the sha256 of the sorted core list, and per-chunk line counts;
merge.sh re-derives the same hash from the chunk files and refuses to merge if it differs."""
import sys, os, random, hashlib
src = sys.argv[1]; per = int(sys.argv[2]) if len(sys.argv) > 2 else 10
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 20261024
here = os.path.dirname(os.path.abspath(__file__))
cores = [l.strip() for l in open(src) if l.strip()]
assert len(cores) == len(set(cores)), "duplicate cores in input"
srt = sorted(cores)
h = hashlib.sha256(("\n".join(srt) + "\n").encode()).hexdigest()
random.Random(seed).shuffle(cores)
os.makedirs(os.path.join(here, "chunks"), exist_ok=False)
nch = (len(cores) + per - 1) // per
with open(os.path.join(here, "manifest.txt"), "w") as m:
    m.write(f"source {src}\nN {len(cores)}\nsorted_sha256 {h}\nper_chunk {per}\nseed {seed}\nchunks {nch}\n")
    for c in range(nch):
        part = cores[c * per:(c + 1) * per]
        with open(os.path.join(here, "chunks", f"c{c:04d}.g6"), "w") as f:
            f.write("\n".join(part) + "\n")
        m.write(f"c{c:04d} {len(part)}\n")
print(f"N={len(cores)} chunks={nch} per={per} sorted_sha256={h}")
