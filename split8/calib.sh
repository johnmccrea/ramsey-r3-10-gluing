#!/bin/bash
# split8/calib.sh -- cross-machine identical-output check + speed calibration.
# Glues the 3 fixed cores in calib_cores.g6 (one per process, in parallel) with the exact d=8 arguments.
# Writes calib_<host>.txt:  idx  seconds  glue_exit  glued  search_nodes  out_lines  out_sha256
# The Mini and Air files must agree on every column except seconds; any difference aborts the split.
set -o pipefail
cd "$(dirname "$0")"
A="etab=x,x,x,x,85,73,65,56,49 maxdeg=8 mindeg=4 mine=104 maxe=104"
H=$(hostname -s); OUT="calib_$H.txt"; : > "$OUT"; mkdir -p calib_tmp
i=0
while read -r g; do
  i=$((i+1))
  (
    s=$(date +%s)
    echo "$g" | bin/glue 9 8 $A 2> calib_tmp/$i.err | bin/labelg -q 2>/dev/null | LC_ALL=C sort -u > calib_tmp/$i.out
    rc=$?
    e=$(date +%s)
    glued=$(sed -n 's/.*cores, \([0-9]*\) glued.*/\1/p' calib_tmp/$i.err)
    nodes=$(sed -n 's/.* \([0-9]*\) search nodes.*/\1/p' calib_tmp/$i.err)
    lines=$(wc -l < calib_tmp/$i.out | tr -d ' ')
    sha=$(shasum -a 256 calib_tmp/$i.out | cut -c1-16)
    echo "$i $((e-s)) $rc ${glued:-?} ${nodes:-?} $lines $sha" >> "$OUT"
  ) &
done < calib_cores.g6
wait
sort -n "$OUT" -o "$OUT"
echo "== $OUT"; cat "$OUT"
