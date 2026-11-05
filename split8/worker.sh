#!/bin/bash
# split8/worker.sh front|back P   -- run the d=8 chunks with P parallel slots.
#   The Mini runs "front" (c0000 upward), the Air runs "back" (last chunk downward); slots pick up the next
#   chunk as they free.  When the two meet, `touch STOP` on both: no new chunk starts, running ones finish.
#   Re-running is safe: chunks with done/<id>.ok are skipped.
# Per chunk (pipefail): bin/glue ... < chunks/<id>.g6 | labelg -q | sort -u  ->  out/<id>.out
#   done/<id>.ok = "id cores glued nodes out_lines out_sha256 seconds host" is written ONLY if glue exited 0,
#   its stderr summary parsed, and its core count equals the chunk's line count.  Failures go to fail/<id>.
cd "$(dirname "$0")"
DIR=${1:?front|back}; P=${2:?slots}
mkdir -p out done fail logs
if [ "$DIR" = front ]; then ls chunks | sort > logs/queue_front.txt; Q=logs/queue_front.txt
else ls chunks | sort -r > logs/queue_back.txt; Q=logs/queue_back.txt; fi
echo "$(date '+%F %T') $(hostname -s) worker $DIR P=$P start" >> logs/worker.log
sed 's/\.g6$//' "$Q" | xargs -P "$P" -n 1 ./run_one.sh
echo "$(date '+%F %T') $(hostname -s) worker $DIR finished queue (or STOP)" >> logs/worker.log
