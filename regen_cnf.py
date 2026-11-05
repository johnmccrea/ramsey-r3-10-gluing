#!/usr/bin/env python3
"""Regenerate each certified CNF from its graph and compare SHA-256 with the stored record.

Usage: python3 regen_cnf.py CENSUS.g6 results.jsonl

For every record in results.jsonl this rebuilds the formula with the deposited encoder
(degree_interface.build_cnf, the same call close_entry_v2.py makes), from the graph on line idx
of the census file, and compares its SHA-256 with the record's cnf_sha256. It checks that the
record's graph is the census graph on that line. It prints one line per record and a verdict.

What a match shows: the certified formula is exactly what the deposited encoder produces from that
graph. It does not show that the encoder is correct; that rests on review and controls.
Hashes depend on the PySAT version, which run.json records; use the same version.
"""
import sys, json, hashlib, os, tempfile
import networkx as nx
import degree_interface as di

def main(census, results):
    cores = [l.strip() for l in open(census) if l.strip()]
    ok = bad = 0; seen = set(); seen_list = []
    with tempfile.TemporaryDirectory() as t:
        for line in open(results):
            r = json.loads(line)
            trivial = r.get("verdict") == "TRIVIAL"
            if "cnf_sha256" not in r and not trivial: continue
            i = r["idx"]; seen.add(i); seen_list.append(i)
            if not 0 <= i < len(cores):
                print(f"{i:03d} OUT OF RANGE: census has {len(cores)} lines"); bad += 1; continue
            if cores[i] != r["core_g6"]:
                print(f"{i:03d} MISMATCH: record's graph is not census line {i}"); bad += 1; continue
            H = nx.from_graph6_bytes(cores[i].encode()); m = H.number_of_nodes()
            try:
                cnf, _, _ = di.build_cnf(di.bits(H, list(range(m))), r["k"], r["d"])
            except ValueError as ex:          # the encoder finds the case trivially impossible
                if trivial: print(f"{i:03d} TRIVIAL reproduced ({ex})"); ok += 1
                else: print(f"{i:03d} DIFFERENT encoder now reports trivial, record has a formula"); bad += 1
                continue
            if trivial:
                print(f"{i:03d} DIFFERENT record says trivial, encoder builds a formula"); bad += 1; continue
            p = os.path.join(t, "x.cnf"); cnf.to_file(p)
            h = hashlib.sha256(open(p, "rb").read()).hexdigest()
            if h == r["cnf_sha256"]: print(f"{i:03d} MATCH {h[:16]}"); ok += 1
            else: print(f"{i:03d} DIFFERENT regenerated {h[:16]} stored {r['cnf_sha256'][:16]}"); bad += 1
    missing = sorted(set(range(len(cores))) - seen)
    if missing: print(f"MISSING records for census lines: {missing}"); bad += 1
    dups = len(seen_list) - len(seen)
    if dups: print(f"note: {dups} repeated record(s) (e.g. from a resumed run); each was checked")
    good = bad == 0 and not missing and seen == set(range(len(cores)))
    print(f"{len(seen)} of {len(cores)} census graphs checked, {ok} records match or reproduce, {bad} problems ->",
          "ALL MATCH" if good else "NOT ALL MATCH")
    sys.exit(0 if good else 1)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
