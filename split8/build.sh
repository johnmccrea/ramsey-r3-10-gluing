#!/bin/bash
# split8/build.sh -- put glue + labelg into split8/bin.
#   On the Mini (inside ~/gluing2/split8): links to the binaries ladder9 already uses.
#   On the Air: builds them from the bundled sources (glue.c + nauty 2.8.8 from the pynauty sdist),
#   same compiler flags as ~/gluing2/build.sh.
set -e
cd "$(dirname "$0")"
mkdir -p bin
if [ -x ../glue ] && [ -x ../nauty/labelg ] && [ "$1" != "--fresh" ]; then
  ln -sf ../../glue bin/glue
  ln -sf ../../nauty/labelg bin/labelg
  echo "linked existing ../glue and ../nauty/labelg"
else
  rm -rf _nauty_src && mkdir _nauty_src
  tar xzf src/pynauty-2.8.8.1.tar.gz -C _nauty_src
  ( cd _nauty_src/pynauty-2.8.8.1/src/nauty2_8_8 && ./configure > /dev/null && make labelg > /dev/null )
  cp _nauty_src/pynauty-2.8.8.1/src/nauty2_8_8/labelg bin/labelg
  cc -O3 -o bin/glue src/glue.c
  echo "built bin/glue and bin/labelg from bundled sources"
fi
shasum -a 256 src/glue.c | awk '{print "glue.c sha256 " $1}'
echo "host $(hostname -s)  perf cores $(sysctl -n hw.perflevel0.physicalcpu 2>/dev/null || echo ?)  all cores $(sysctl -n hw.ncpu 2>/dev/null || nproc)"
