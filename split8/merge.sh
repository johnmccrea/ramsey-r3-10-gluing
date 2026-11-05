#!/bin/bash
# split8/merge.sh  -- verify and merge the d=8 chunk outputs (run on the Mini, after the Air's out/ and done/
# have been copied into this folder).  Writes ../cache/k9_n32_e104-104_D8_d4.g6 only if every check passes.
#   1 coverage: the sorted union of chunks/*.g6 hashes to manifest's sorted_sha256, with N lines
#   2 completeness: every chunk has done/<id>.ok, and its core count matches the manifest
#   3 integrity: each out/<id>.out still matches the line count and sha recorded in its .ok
#   4 merge: LC_ALL=C sort -m -u of all chunk outputs + the existing 39-graph .raw (as driver.py does),
#     then count lines; reports d=8 glued total (sum of .ok) and how many NEW graphs d=8 added.
set -e -o pipefail
cd "$(dirname "$0")"
RAW=../cache/k9_n32_e104-104_D8_d4.g6.raw; FINAL=../cache/k9_n32_e104-104_D8_d4.g6
N=$(awk '$1=="N"{print $2}' manifest.txt); H=$(awk '$1=="sorted_sha256"{print $2}' manifest.txt)
h=$(cat chunks/*.g6 | LC_ALL=C sort | shasum -a 256 2>/dev/null | cut -d' ' -f1 || true)
[ -n "$h" ] || h=$(cat chunks/*.g6 | LC_ALL=C sort | sha256sum | cut -d' ' -f1)
# python's sorted() == byte order for ASCII graph6, same as LC_ALL=C sort
n=$(cat chunks/*.g6 | wc -l | tr -d ' ')
echo "1 coverage: N=$n (manifest $N)  sha ${h:0:16} (manifest ${H:0:16})"
[ "$n" = "$N" ] && [ "$h" = "$H" ] || { echo "COVERAGE FAIL"; exit 1; }
miss=0; bad=0
while read -r id cnt; do
  case $id in c[0-9]*) ;; *) continue;; esac
  if [ ! -f done/$id.ok ]; then miss=$((miss+1)); echo "  missing $id"; continue; fi
  read -r _ okn glued nodes lines sha secs host < done/$id.ok
  [ "$okn" = "$cnt" ] || { bad=$((bad+1)); echo "  count mismatch $id ($okn vs $cnt)"; }
  l=$(wc -l < out/$id.out | tr -d ' ')
  s=$( (shasum -a 256 out/$id.out 2>/dev/null || sha256sum out/$id.out) | cut -c1-16)
  [ "$l" = "$lines" ] && [ "$s" = "$sha" ] || { bad=$((bad+1)); echo "  integrity fail $id"; }
done < manifest.txt
echo "2/3 completeness+integrity: missing=$miss bad=$bad"
[ $miss -eq 0 ] && [ $bad -eq 0 ] || { echo "NOT MERGING"; exit 1; }
G=$(cat done/*.ok | awk '{s+=$3} END{print s}')
before=$(wc -l < $RAW | tr -d ' ')
LC_ALL=C sort -m -u out/*.out $RAW > merged.tmp
after=$(wc -l < merged.tmp | tr -d ' ')
echo "4 merge: d=8 glued (raw emitted) $G; graphs before $before, after $after, new from d=8 $((after-before))"
LC_ALL=C sort -c -u merged.tmp
cp merged.tmp merged_final.g6
[ "$1" = "--write" ] && { cp merged.tmp "$FINAL"; echo "wrote $FINAL"; } || echo "(dry run; re-run with --write to install)"
