#!/bin/bash
# split8/run_one.sh <chunk id>  -- one d=8 chunk (called by worker.sh)
set -o pipefail
cd "$(dirname "$0")"
id=$1
[ -f STOP ] && exit 0
[ -f done/$id.ok ] && exit 0
A="etab=x,x,x,x,85,73,65,56,49 maxdeg=8 mindeg=4 mine=104 maxe=104"
s=$(date +%s)
bin/glue 9 8 $A < chunks/$id.g6 2> out/$id.err | bin/labelg -q 2>/dev/null | LC_ALL=C sort -u > out/$id.tmp
rc=$?
e=$(date +%s)
n=$(wc -l < chunks/$id.g6 | tr -d ' ')
cores=$(sed -n 's/^glue: \([0-9]*\) cores.*/\1/p' out/$id.err)
glued=$(sed -n 's/.*cores, \([0-9]*\) glued.*/\1/p' out/$id.err)
nodes=$(sed -n 's/.* \([0-9]*\) search nodes.*/\1/p' out/$id.err)
if [ $rc -eq 0 ] && [ -n "$glued" ] && [ "$cores" = "$n" ]; then
  mv out/$id.tmp out/$id.out
  lines=$(wc -l < out/$id.out | tr -d ' ')
  sha=$(shasum -a 256 out/$id.out | cut -c1-16)
  echo "$id $n $glued $nodes $lines $sha $((e-s)) $(hostname -s)" > done/$id.ok
else
  echo "$id rc=$rc cores=$cores/$n glued=$glued $((e-s))s $(hostname -s) $(date '+%F %T')" > fail/$id
fi
