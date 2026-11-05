#!/bin/bash
# n=40, alpha<=9, min degree >= 5 (certified degree-4 lemma); automorphism of prime order p with f fixed points
cd /home/claude/sym; T=${T:-240}
for pf in "37 3" "31 9" "29 11" "23 17" "19 2" "19 21" "17 6" "17 23" "13 1" "13 14" "13 27" "11 7" "11 18" "11 29" "7 5" "7 12" "5 0" "5 5" "3 1"; do
  set -- $pf; python3 -W ignore sym_sat.py 40 9 $1 $2 $T mindeg=5 | grep -v "^  \[" | sed -n 2p
done
