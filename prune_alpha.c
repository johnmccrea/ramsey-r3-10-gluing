/* geng PRUNE hook: reject a graph if it has an independent set of size K containing the newest vertex.
   alpha is monotone under vertex deletion, so this yields exactly the graphs with alpha < K. */
#include "gtools.h"
static int K = -1;
graph *G_;

static int indep(setword cand, int need) {
    if (need == 0) return 1;
    if (POPCOUNT(cand) < need) return 0;
    while (cand) {
        int v = FIRSTBITNZ(cand); cand &= ~bit[v];
        /* cand already excludes vertices before v; restrict to non-neighbours */

        if (indep(cand & ~G_[v], need - 1)) return 1;
        if (POPCOUNT(cand) < need) return 0;
    }
    return 0;
}

int prune_alpha(graph *g, int n, int maxn) {
    if (K < 0) { char *s = getenv("ALPHA_LT"); K = s ? atoi(s) : 99; }
    int last = n - 1; G_ = g;
    setword all = (n == WORDSIZE) ? ~(setword)0 : ALLMASK(n);
    setword cand = all & ~g[last] & ~bit[last];
    return indep(cand, K - 1);
}
