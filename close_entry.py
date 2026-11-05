#!/usr/bin/env python3
"""
Close a census entry: given ALL (3,k-1; m, e)-graphs (a census file) and d = n - 1 - m, decide for every core H
whether some (3,k; n)-graph has a vertex of degree d whose non-neighbourhood is exactly H.
For each core: degree-d interface CNF (degree_interface.build_cnf: A_i = N(x_i) ∩ H independent, degree caps,
and every independent (k-t)-set of H missed by at most t-1 of the A_i), solved by command-line CaDiCaL with the
DRAT proof streamed to disk, then checked by drat-trim.
  UNSAT + 's VERIFIED' for every core  =>  the entry is closed (given the census is complete).
  SAT  => the extension is decoded and verified as a full (3,k;n)-graph: a WITNESS.  Reported loudly.
usage: python3 close_entry.py CENSUS.g6 k d [JOBS]     (results appended to close_<name>.log; resumable)
"""
import os, sys, subprocess, hashlib, itertools, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import networkx as nx
import degree_interface as di
CADICAL = os.environ.get("CADICAL", os.path.join(HERE, "cadical", "build", "cadical"))
DRAT = os.environ.get("DRAT", os.path.join(HERE, "drat-trim", "drat-trim"))

def one(job):
    idx, g6, k, d, wdir = job
    H = nx.from_graph6_bytes(g6.encode()); m = H.number_of_nodes()
    adj = di.bits(H, list(range(m)))
    try:
        cnf, a, counts = di.build_cnf(adj, k, d)
    except ValueError as ex:                      # a core vertex already exceeds max degree k-1
        return f"{idx} {g6} TRIVIAL ({ex})"
    base = os.path.join(wdir, f"c{idx}")
    cnf.to_file(base + ".cnf")
    rc = subprocess.run([CADICAL, "-q", base + ".cnf", base + ".proof"], capture_output=True, text=True)
    if rc.returncode == 10:                       # SAT: decode and verify a full graph
        model = set(int(x) for line in rc.stdout.splitlines() if line.startswith("v") for x in line.split()[1:] if int(x) > 0)
        n = m + d + 1; G = nx.Graph(); G.add_nodes_from(range(n)); G.add_edges_from(H.edges())
        for i in range(d):
            G.add_edge(n - 1, m + i)
            for c in range(m):
                if a[i, c] in model: G.add_edge(m + i, c)
        gadj = di.bits(G, list(range(n)))
        ok = sum(nx.triangles(G).values()) == 0 and not di.indep_sets_exact(gadj, k)
        out = nx.to_graph6_bytes(G, header=False).decode().strip()
        return f"{idx} {g6} SAT verified_witness={ok} {out}"
    if rc.returncode != 20:
        return f"{idx} {g6} FAILED cadical exit {rc.returncode}"
    chk = subprocess.run([DRAT, base + ".cnf", base + ".proof"], capture_output=True, text=True).stdout
    verdict = "VERIFIED" if "s VERIFIED" in chk else "NOT_VERIFIED"
    if verdict == "VERIFIED":
        h = hashlib.sha256(open(base + ".cnf", "rb").read()).hexdigest()[:16]
        for f in (base + ".cnf", base + ".proof"): os.remove(f)    # keep only the hash; re-derivable from the core
        return f"{idx} {g6} UNSAT VERIFIED cnf_sha256_16={h} clauses={len(cnf.clauses)}"
    return f"{idx} {g6} UNSAT NOT_VERIFIED (cnf/proof kept)"

def main():
    census, k, d = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    jobs = int(sys.argv[4]) if len(sys.argv) > 4 else max(1, (os.cpu_count() or 2) - 1)
    name = os.path.basename(census).rsplit(".", 1)[0] + f"_k{k}_d{d}"
    log = os.path.join(HERE, f"close_{name}.log"); wdir = os.path.join(HERE, "work_close", name); os.makedirs(wdir, exist_ok=True)
    done = set()
    if os.path.exists(log):
        for line in open(log):
            p = line.split()
            if len(p) > 2 and (p[2] in ("TRIVIAL", "SAT") or "UNSAT VERIFIED" in line): done.add(int(p[0]))
    cores = [l.strip() for l in open(census) if l.strip()]
    todo = [(i, g, k, d, wdir) for i, g in enumerate(cores) if i not in done]
    print(f"{name}: {len(cores)} cores, {len(done)} already done, {len(todo)} to run, {jobs} jobs", flush=True)
    counts = {"UNSAT VERIFIED": 0, "TRIVIAL": 0, "SAT": 0, "OTHER": 0}
    with open(log, "a") as fl, cf.ProcessPoolExecutor(jobs) as ex:
        for res in ex.map(one, todo, chunksize=4):
            fl.write(res + "\n"); fl.flush()
            key = "UNSAT VERIFIED" if "UNSAT VERIFIED" in res else "TRIVIAL" if "TRIVIAL" in res else "SAT" if " SAT " in res else "OTHER"
            counts[key] += 1
            if key == "SAT": print("*** EXTENSION FOUND:", res, flush=True)
            if key == "OTHER": print("*** CHECK:", res, flush=True)
    total = {"UNSAT VERIFIED": 0, "TRIVIAL": 0, "SAT": 0, "OTHER": 0}
    for line in open(log):
        key = "UNSAT VERIFIED" if "UNSAT VERIFIED" in line else "TRIVIAL" if "TRIVIAL" in line else "SAT" if " SAT " in line else "OTHER"
        total[key] += 1
    closed = total["UNSAT VERIFIED"] + total["TRIVIAL"] == len(cores) and total["SAT"] == 0 and total["OTHER"] == 0
    print(f"{name}: {total}  ->  {'ENTRY CLOSED (every core refuted, all proofs verified)' if closed else 'NOT CLOSED'}", flush=True)

if __name__ == "__main__":
    main()
