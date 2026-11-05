#!/bin/bash
# Build nauty (geng, labelg), the alpha-pruned geng_a, and the gluer.  macOS or Linux.
set -e
cd "$(dirname "$0")"
if [ ! -d nauty ]; then
  # nauty 2.8.8 source: from the pynauty sdist on PyPI (bundles it), else from McKay & Piperno's site
  if python3 -m pip download pynauty==2.8.8.1 --no-binary :all: --no-deps -d _src -q 2>/dev/null; then
    tar xzf _src/pynauty-2.8.8.1.tar.gz -C _src && cp -r _src/pynauty-2.8.8.1/src/nauty2_8_8 nauty
  else
    curl -L -o _src_nauty.tar.gz https://pallini.di.uniroma1.it/nauty2_8_8.tar.gz
    mkdir -p _src && tar xzf _src_nauty.tar.gz -C _src && cp -r _src/nauty2_8_8 nauty
  fi
fi
cd nauty
[ -f makefile ] || ./configure > /dev/null
make labelg gtoolsL.o nautyL1.o nautilL1.o naugraphL1.o schreier.o naurng.o > /dev/null
cp ../prune_alpha.c .
cc -O3 -o geng_a -DMAXN=WORDSIZE -DWORDSIZE=64 -DPRUNE=prune_alpha geng.c prune_alpha.c \
   gtoolsL.o nautyL1.o nautilL1.o naugraphL1.o schreier.o naurng.o
cd ..
cc -O3 -o glue glue.c
# v3: command-line CaDiCaL (streams DRAT proofs to disk) and drat-trim, for closing census entries
[ -x cadical/build/cadical ] || { [ -d cadical ] || git clone -q --depth 1 https://github.com/arminbiere/cadical.git; (cd cadical && ./configure > /dev/null && make -j4 > /dev/null); }
[ -x drat-trim/drat-trim ] || { [ -d drat-trim ] || git clone -q https://github.com/marijnheule/drat-trim.git; (cd drat-trim && make -s drat-trim 2>/dev/null || cc -O2 -o drat-trim drat-trim.c); }
python3 -c "import pysat" 2>/dev/null || python3 -m pip install --user python-sat
python3 -c "import networkx" 2>/dev/null || python3 -m pip install --user networkx
echo "built: nauty/geng_a nauty/labelg glue"
ALPHA_LT=5 nauty/geng_a -tq 13 | wc -l | awk '{print "smoke test (3,5,13) = " $1 " (expect 1)"}'
# closing-tool controls: C35's own core must extend (SAT, rebuilt graph = C35); the degree-4 lemma must replay (UNSAT VERIFIED)
python3 -W ignore -c "
import networkx as nx
G=nx.circulant_graph(35,[1,7,11,16]); open('c35.g6','w').write(nx.to_graph6_bytes(G,header=False).decode())
core=[u for u in G if u!=0 and not G.has_edge(0,u)]; H=nx.convert_node_labels_to_integers(G.subgraph(core))
open('c35core.g6','w').write(nx.to_graph6_bytes(H,header=False).decode())"
python3 -W ignore close_entry.py c35core.g6 9 8 1 | tail -1     # expect SAT 1 -> NOT CLOSED (that is the point)
python3 -W ignore close_entry.py c35.g6 10 4 1 | tail -1        # expect UNSAT VERIFIED 1 -> ENTRY CLOSED
