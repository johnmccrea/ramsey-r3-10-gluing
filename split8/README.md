# split8: the degree-8 stage, split across two machines

Order: `make_chunks.py` (835 chunks of 10 cores, seed 20261024; `manifest.txt` records the
coverage hash) -> `worker.sh front 10` on the Mac mini and `worker.sh back 6` on the MacBook Air ->
`run_one.sh` per chunk (with `pipefail`) -> `merge.sh` (dry run, then `--write`).
`calib.sh` and `calib2.sh` are the cross-machine calibration runs (both passed on Oct 25, 2026).

`build.sh` expects a `src/` folder holding `glue.c` (identical to the top-level `glue.c`) and
`pynauty-2.8.8.1.tar.gz` (the PyPI source package, which bundles nauty 2.8.8). Neither is duplicated
here: copy `../glue.c` into `src/` and download the pynauty source package, or run it on a machine
where the top-level `build.sh` has already been run, in which case it links the existing binaries.
