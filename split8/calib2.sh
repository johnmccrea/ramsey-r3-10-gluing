#!/bin/bash
# split8/calib2.sh [P]  -- second calibration: 6 cores cut from the 39 known (3,9;32,104) graphs
# (G minus a min-deficiency degree-6 vertex and its neighbours), glued at d=6, so each MUST output
# graphs: this tests glue + labelg canonical output across machines.  Writes calib2_<host>.txt:
#   idx  seconds  glue_exit  glued  search_nodes  out_lines  out_sha256
set -o pipefail
cd "$(dirname "$0")"
P=${1:-2}
A="etab=x,x,x,x,85,73,65,56,49 maxdeg=8 mindeg=4 mine=104 maxe=104"
H=$(hostname -s); OUT="calib2_$H.txt"; : > "$OUT"; mkdir -p calib2_tmp
nl -ba calib2_cores.g6 | xargs -P "$P" -L 1 bash -c '
  i=$0; g=$1; A="'"$A"'"
  s=$(date +%s)
  echo "$g" | bin/glue 9 6 $A 2> calib2_tmp/$i.err | bin/labelg -q 2>/dev/null | LC_ALL=C sort -u > calib2_tmp/$i.out
  rc=$?; e=$(date +%s)
  glued=$(sed -n "s/.*cores, \([0-9]*\) glued.*/\1/p" calib2_tmp/$i.err)
  nodes=$(sed -n "s/.* \([0-9]*\) search nodes.*/\1/p" calib2_tmp/$i.err)
  lines=$(wc -l < calib2_tmp/$i.out | tr -d " ")
  sha=$(shasum -a 256 calib2_tmp/$i.out | cut -c1-16)
  echo "$i $((e-s)) $rc ${glued:-?} ${nodes:-?} $lines $sha" >> "'"$OUT"'"'
sort -n "$OUT" -o "$OUT"
cat calib2_tmp/*.out | LC_ALL=C sort -u > calib2_all.g6
echo "== $OUT"; cat "$OUT"
echo "all outputs: $(wc -l < calib2_all.g6 | tr -d " ") graphs, sha $(shasum -a 256 calib2_all.g6 | cut -c1-16)"
