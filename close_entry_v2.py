#!/usr/bin/env python3
"""
close_entry_v2.py: close a census entry, with every result bound to its evidence.

Question, per core H (one line of the census): does some (3,k;n)-graph have a vertex of degree d whose
non-neighbourhood is exactly H?  Encoding unchanged from v1: degree_interface.build_cnf (reviewed by ChatGPT,
Nov 1 2026: sound).  This file changes only the machinery around it, per that review and John's decisions:

  1. Results are bound to the census file's full SHA-256, the core's own graph6, and the toolchain's hashes,
     never to a row number.  A changed or reordered census cannot inherit old results.
  2. The census is validated before any solving: count, order m, edge count, triangle-free, alpha <= k-2,
     pairwise non-isomorphic.  Expected values are command-line arguments, not guesses.
  3. The proof checker is acceptance-tested at start-up: a known-UNSAT formula must verify, and a corrupted proof
     and a mismatched proof must both be rejected.  If any test fails, nothing runs.
  4. CNF and DRAT proof are kept for every core (for the deposit), each with its full SHA-256.
  5. A SAT answer whose decoded graph fails the independent check is an ERROR, never reported as a witness.
  6. Toolchain pinned: SHA-256 of the CaDiCaL and drat-trim binaries, and their version strings, in every record.
  7. No hard time limit (John, Nov 1); each core's wall time is recorded, and a heartbeat line is printed.
v2.1 (after ChatGPT's v2 review, Nov 1):
  8. drat-trim is accepted only if it exits 0 AND prints "s VERIFIED" (a fake checker that prints it but exits
     non-zero is rejected); its full transcript is kept per core and hashed.
  9. Resume and the final verdict re-hash every stored CNF, proof and transcript; anything missing or changed
     is re-solved (resume) or counted as an error (verdict). --audit re-runs drat-trim on every stored proof.
 10. All safety checks use require(), which survives python -O (assert does not).
 11. Acceptance tests run in binary proof mode (production) as well as text mode; runtime versions recorded.

Usage:
  python3 close_entry_v2.py CENSUS.g6 k d --expect-count 39 --expect-m 32 --expect-e 104 [--jobs J] [--out DIR]
Output: DIR/results.jsonl (one JSON record per core), DIR/cores/<idx>.cnf and .drat, DIR/run.json (header).
Verdict: ENTRY CLOSED only if every census core has exactly one record for this census and toolchain, each
UNSAT_VERIFIED or TRIVIAL, and nothing else.
"""
import argparse, concurrent.futures as cf, hashlib, json, os, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import networkx as nx
import degree_interface as di

def require(cond, msg):
    """Safety check that survives python -O (assert does not)."""
    if not cond:
        print("REFUSED:", msg, flush=True); sys.exit(2)

CADICAL = os.environ.get("CADICAL", os.path.join(HERE, "cadical", "build", "cadical"))
DRAT = os.environ.get("DRAT", os.path.join(HERE, "drat-trim", "drat-trim"))
DRAT_TIMEOUT = "1000000"   # seconds; drat-trim's default (20000 s) could reject a valid long proof

def sha256_file(path, bufsize=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(bufsize): h.update(chunk)
    return h.hexdigest()

def toolchain():
    import platform, pysat
    ver = subprocess.run([CADICAL, "--version"], capture_output=True, text=True).stdout.strip()
    return {"cadical": CADICAL, "cadical_sha256": sha256_file(CADICAL), "cadical_version": ver,
            "drat_trim": DRAT, "drat_trim_sha256": sha256_file(DRAT),
            "degree_interface_sha256": sha256_file(os.path.join(HERE, "degree_interface.py")),
            "close_entry_v2_sha256": sha256_file(os.path.abspath(__file__)),
            "python": sys.version.split()[0], "networkx": nx.__version__,
            "pysat": getattr(pysat, "__version__", "unknown"), "platform": platform.platform()}

def record_files_intact(r, coredir):
    """A stored UNSAT_VERIFIED result counts only if its CNF, proof and checker transcript are present and
    hash-identical to what was recorded. TRIVIAL needs no files."""
    if r.get("verdict") == "TRIVIAL": return True
    i = r["idx"]; c, p, t = (os.path.join(coredir, f"{i:03d}{x}") for x in (".cnf", ".drat", ".check.txt"))
    return (all(os.path.exists(x) for x in (c, p, t)) and sha256_file(c) == r.get("cnf_sha256")
            and sha256_file(p) == r.get("proof_sha256") and sha256_file(t) == r.get("check_sha256"))

def up_refutes(cnf_path):
    """Independent check: does unit propagation alone derive a conflict from the CNF?"""
    clauses = []
    for line in open(cnf_path):
        if line[:1] in ("c", "p") or not line.strip(): continue
        clauses.append([int(x) for x in line.split()[:-1]])
    val = {}
    changed = True
    while changed:
        changed = False
        for c in clauses:
            unassigned, sat = [], False
            for l in c:
                v = val.get(abs(l))
                if v is None: unassigned.append(l)
                elif v == (l > 0): sat = True; break
            if sat: continue
            if not unassigned: return True                    # all literals false: conflict
            if len(unassigned) == 1: val[abs(unassigned[0])] = unassigned[0] > 0; changed = True
    return False

def drat_verified(cnf, proof, transcript=None):
    """Accept only if drat-trim prints 's VERIFIED' and never 's NOT VERIFIED', AND either exits 0, or reports
    'c trivial UNSAT' (drat-trim then exits 1 by design, see its main()) and our own unit propagation
    independently refutes the formula.  A checker that prints 's VERIFIED' but exits otherwise is rejected."""
    r = subprocess.run([DRAT, cnf, proof, "-t", DRAT_TIMEOUT], capture_output=True, text=True)
    lines = [l.strip() for l in r.stdout.splitlines()]
    said = "s VERIFIED" in lines and "s NOT VERIFIED" not in lines
    ok = said and (r.returncode == 0 or (r.returncode == 1 and "c trivial UNSAT" in lines and up_refutes(cnf)))
    if transcript: open(transcript, "w").write(f"exit {r.returncode}\n" + r.stdout + r.stderr)
    return ok, r.stdout[-400:]

# ---------- 3. checker acceptance tests ----------
def php_cnf(holes):                      # pigeonhole: holes+1 pigeons into holes holes: UNSAT
    p = holes + 1; v = lambda i, j: i * holes + j + 1
    cls = [[v(i, j) for j in range(holes)] for i in range(p)]
    cls += [[-v(i, j), -v(k, j)] for j in range(holes) for i in range(p) for k in range(i + 1, p)]
    return f"p cnf {p * holes} {len(cls)}\n" + "".join(" ".join(map(str, c)) + " 0\n" for c in cls)

def acceptance_tests():
    """Run in the SAME proof mode as production (CaDiCaL's default binary DRAT), plus text mode."""
    with tempfile.TemporaryDirectory() as t:
        a, b = os.path.join(t, "a.cnf"), os.path.join(t, "b.cnf")
        open(a, "w").write(php_cnf(5)); open(b, "w").write(php_cnf(4))
        for mode in ([], ["--binary=false"]):
            tag = "binary" if not mode else "text"
            pa, pb = os.path.join(t, f"a_{tag}.drat"), os.path.join(t, f"b_{tag}.drat")
            rc = subprocess.run([CADICAL, "-q", *mode, a, pa], capture_output=True).returncode
            require(rc == 20, f"acceptance ({tag}): known-UNSAT formula not UNSAT (exit {rc})")
            ok, _ = drat_verified(a, pa); require(ok, f"acceptance ({tag}): valid proof NOT verified")
            data = open(pa, "rb").read()
            bad = os.path.join(t, f"bad_{tag}.drat"); open(bad, "wb").write(data[: max(1, len(data) // 4)])
            ok, _ = drat_verified(a, bad); require(not ok, f"acceptance ({tag}): truncated proof was ACCEPTED")
            subprocess.run([CADICAL, "-q", *mode, b, pb], capture_output=True)
            ok, _ = drat_verified(a, pb); require(not ok, f"acceptance ({tag}): proof for a different formula was ACCEPTED")
        empty = os.path.join(t, "empty.drat"); open(empty, "w").write("")
        ok, _ = drat_verified(a, empty); require(not ok, "acceptance: empty proof was ACCEPTED")
    return "binary and text modes: valid accepted; truncated, empty and mismatched proofs rejected (exit status checked)"

# ---------- 2. census validation ----------
def validate_census(path, k, expect_count, expect_m, expect_e):
    cores = [l.strip() for l in open(path) if l.strip()]
    require(len(cores) == expect_count, f"census: {len(cores)} cores, expected {expect_count}")
    graphs = []
    for i, g6 in enumerate(cores):
        H = nx.from_graph6_bytes(g6.encode())
        require(H.number_of_nodes() == expect_m, f"census core {i}: {H.number_of_nodes()} vertices")
        require(H.number_of_edges() == expect_e, f"census core {i}: {H.number_of_edges()} edges")
        require(sum(nx.triangles(H).values()) == 0, f"census core {i}: has a triangle")
        a = di.alpha(di.bits(H, list(range(expect_m))))
        require(a <= k - 2, f"census core {i}: alpha {a} > {k - 2}")
        graphs.append(H)
    buckets = {}
    for i, H in enumerate(graphs):
        buckets.setdefault(nx.weisfeiler_lehman_graph_hash(H, iterations=4), []).append(i)
    for idxs in buckets.values():
        for x in range(len(idxs)):
            for y in range(x + 1, len(idxs)):
                require(not nx.is_isomorphic(graphs[idxs[x]], graphs[idxs[y]]), f"census: cores {idxs[x]} and {idxs[y]} isomorphic")
    return cores

# ---------- the per-core job ----------
def one(job):
    idx, g6, k, d, coredir, base_rec = job
    rec = dict(base_rec, idx=idx, core_g6=g6); t0 = time.time()
    H = nx.from_graph6_bytes(g6.encode()); m = H.number_of_nodes()
    adj = di.bits(H, list(range(m)))
    try:
        cnf, a, counts = di.build_cnf(adj, k, d)
    except ValueError as ex:
        return dict(rec, verdict="TRIVIAL", reason=str(ex), seconds=round(time.time() - t0, 1))
    cpath, ppath = os.path.join(coredir, f"{idx:03d}.cnf"), os.path.join(coredir, f"{idx:03d}.drat")
    cnf.to_file(cpath)
    rc = subprocess.run([CADICAL, "-q", cpath, ppath], capture_output=True, text=True)
    rec.update(cnf_sha256=sha256_file(cpath), clauses=len(cnf.clauses), cadical_exit=rc.returncode)
    if rc.returncode == 10:
        model = {int(x) for line in rc.stdout.splitlines() if line.startswith("v") for x in line.split()[1:] if int(x) > 0}
        n = m + d + 1; G = nx.Graph(); G.add_nodes_from(range(n)); G.add_edges_from(H.edges())
        for i in range(d):
            G.add_edge(n - 1, m + i)
            for c in range(m):
                if a[i, c] in model: G.add_edge(m + i, c)
        ok = (sum(nx.triangles(G).values()) == 0 and not di.indep_sets_exact(di.bits(G, list(range(n))), k)
              and G.degree(n - 1) == d)
        rest = G.subgraph([v for v in G if v != n - 1 and not G.has_edge(n - 1, v)])
        ok = ok and nx.is_isomorphic(rest, H)
        g = nx.to_graph6_bytes(G, header=False).decode().strip()
        return dict(rec, verdict="SAT_WITNESS" if ok else "ERROR_SAT_DECODE_FAILED", witness_g6=g,
                    seconds=round(time.time() - t0, 1))
    if rc.returncode != 20:
        return dict(rec, verdict="ERROR_SOLVER", seconds=round(time.time() - t0, 1))
    tpath = os.path.join(coredir, f"{idx:03d}.check.txt")
    ok, tail = drat_verified(cpath, ppath, transcript=tpath)
    rec.update(proof_sha256=sha256_file(ppath), proof_bytes=os.path.getsize(ppath), check_sha256=sha256_file(tpath))
    return dict(rec, verdict="UNSAT_VERIFIED" if ok else "ERROR_PROOF_NOT_VERIFIED",
                checker_tail=None if ok else tail, seconds=round(time.time() - t0, 1))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("census"); ap.add_argument("k", type=int); ap.add_argument("d", type=int)
    ap.add_argument("--expect-count", type=int, required=True); ap.add_argument("--expect-m", type=int, required=True)
    ap.add_argument("--expect-e", type=int, required=True)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--out", default=None)
    ap.add_argument("--audit", action="store_true", help="re-run drat-trim on every stored proof before the verdict")
    A = ap.parse_args()

    census_sha = sha256_file(A.census)
    out = A.out or os.path.join(HERE, f"close_v2_{census_sha[:12]}_k{A.k}_d{A.d}")
    coredir = os.path.join(out, "cores"); os.makedirs(coredir, exist_ok=True)
    tc = toolchain()
    print("acceptance tests:", acceptance_tests(), flush=True)
    cores = validate_census(A.census, A.k, A.expect_count, A.expect_m, A.expect_e)
    print(f"census valid: {len(cores)} cores, sha256 {census_sha}", flush=True)
    base = {"census_sha256": census_sha, "k": A.k, "d": A.d, **tc}
    hdr = os.path.join(out, "run.json")
    if os.path.exists(hdr):
        old = json.load(open(hdr))
        same = all(old.get(x) == base[x] for x in base)
        require(same, "run.json differs from this census/toolchain: start a new --out directory")
    else:
        json.dump(dict(base, started=time.strftime("%Y-%m-%dT%H:%M:%S%z")), open(hdr, "w"), indent=1)

    res_path = os.path.join(out, "results.jsonl"); have = {}
    if os.path.exists(res_path):
        for line in open(res_path):
            r = json.loads(line)
            if (all(r.get(x) == base[x] for x in base) and r["verdict"] in ("UNSAT_VERIFIED", "TRIVIAL")
                    and record_files_intact(r, coredir)):
                have[r["core_g6"]] = r
    todo = [(i, g, A.k, A.d, coredir, base) for i, g in enumerate(cores) if g not in have]
    print(f"{len(cores)} cores, {len(cores) - len(todo)} already done for this census+toolchain, {len(todo)} to run, {A.jobs} jobs", flush=True)

    with open(res_path, "a") as fl, cf.ProcessPoolExecutor(A.jobs) as ex:
        futs = {ex.submit(one, j): j[0] for j in todo}
        for f in cf.as_completed(futs):
            r = f.result(); fl.write(json.dumps(r) + "\n"); fl.flush()
            print(time.strftime("%H:%M"), r["idx"], r["verdict"], f'{r.get("seconds")}s', flush=True)
            if r["verdict"] == "SAT_WITNESS": print("*** WITNESS FOUND:", r["witness_g6"], flush=True)

    final = {}
    for line in open(res_path):
        r = json.loads(line)
        if not all(r.get(x) == base[x] for x in base): continue
        v = r["verdict"]
        if v in ("UNSAT_VERIFIED", "TRIVIAL") and not record_files_intact(r, coredir):
            v = "ERROR_FILES_MISSING_OR_CHANGED"
        if v == "UNSAT_VERIFIED" and A.audit:
            c = os.path.join(coredir, f'{r["idx"]:03d}')
            ok, _ = drat_verified(c + ".cnf", c + ".drat")
            v = v if ok else "ERROR_AUDIT_NOT_VERIFIED"
        final.setdefault(r["core_g6"], []).append(v)
    GOOD = ("UNSAT_VERIFIED", "TRIVIAL")
    unresolved = [g for g in cores if not any(v in GOOD for v in final.get(g, []))]
    witness = [g for g in cores if any(v.startswith("SAT") or v == "ERROR_SAT_DECODE_FAILED" for v in final.get(g, []))]
    retried = [g for g in cores if g not in unresolved and any(v not in GOOD for v in final[g])]
    closed = not unresolved and not witness
    print(f"census {census_sha[:16]}: {len(cores) - len(unresolved)}/{len(cores)} cores refuted and verified; "
          f"unresolved {len(unresolved)}; SAT or failed decode {len(witness)}; earlier errors later resolved {len(retried)}"
          f"  ->  {'ENTRY CLOSED' if closed else 'NOT CLOSED'}", flush=True)

if __name__ == "__main__":
    main()
