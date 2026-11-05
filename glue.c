/*
 * glue.c -- neighbourhood gluing for (3,k)-Ramsey graphs, direct backtracking (replaces the SAT enumerator
 * in glue.py; same mathematics, see glue.py header).
 *
 * Input (stdin): core graphs H in graph6, m <= 63 vertices, each a (3,k-1)-graph.
 * Output (stdout): every glued graph G (graph6, NOT canonical; pipe through `labelg -q | sort -u`).
 * G = H + {x_1..x_d} + v, with N(v) = {x_i}, N(x_i) ∩ H = A_i, and
 *   A_i independent in H, |A_i| <= Dmax-1, deg_H(c) + #{i: c in A_i} <= Dmax  (max degree Dmax, default d = deg v)
 *   for every T ⊆ {1..d}, |T| = t >= 2:  alpha(H - ∪_{i in T} A_i) <= k-1-t   (alpha(G) <= k-1)
 * The A_i are chosen with non-increasing index in a fixed candidate list (x_i are interchangeable).
 *
 * usage: glue k d [maxz | etab=E0,E1,..]  [maxdeg=Dmax] [regular] [mindeg=D] [edges=E | mine=E1 maxe=E2]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef uint64_t set;
#define POP(x) __builtin_popcountll(x)
#define FIRST(x) __builtin_ctzll(x)
#define MAXM 63

static int MAXZ = 0, GAMMA = 0; static int ETAB[64]; /* ETAB[dx] = lower bound e(3,k-1,n-dx-1) used by the driver */
static int K, D, MAXDEG = -1, REG = 0, MINDEG = 0, EDGES = -1, MINE = -1, MAXE = -1;
static int m, eH;
static set adj[MAXM], nadj[MAXM];
static int deg[MAXM], room[MAXM], minhit[MAXM];
static set *cand; static int ncand, capcand;
static int pick[16]; static set uni[1 << 10];   /* union of A over subsets of chosen indices */
static int hits[MAXM];
static long long nout = 0, nodes = 0;
static int sumtarget = -1, sumlo = -1, sumhi = 1 << 30;

/* does U contain an independent set of size s? */
static int has_indep(set U, int s) {
    if (s <= 0) return 1;
    if (POP(U) < s) return 0;
    while (U) {
        if (POP(U) < s) return 0;
        int v = FIRST(U); U &= U - 1;
        if (has_indep(U & nadj[v], s - 1)) return 1;
    }
    return 0;
}

static void add_cand(set A) {
    if (ncand == capcand) { capcand = capcand ? 2 * capcand : 1024; cand = realloc(cand, capcand * sizeof(set)); }
    cand[ncand++] = A;
}
/* enumerate independent sets with size in [lo,hi] using only vertices in avail */
static void gen_cand(set P, set S, int size, int lo, int hi) {
    if (size >= lo) add_cand(S);
    if (size == hi) return;
    while (P) {
        int v = FIRST(P); P &= P - 1;
        gen_cand(P & nadj[v], S | ((set)1 << v), size + 1, lo, hi);
    }
}

static void emit(void) {
    int n = m + D + 1;
    static set g[64];
    for (int i = 0; i < n; i++) g[i] = 0;
    for (int c = 0; c < m; c++) g[c] = adj[c];
    for (int i = 0; i < D; i++) {
        int x = m + i; set A = cand[pick[i]];
        g[x] |= (set)1 << (m + D); g[m + D] |= (set)1 << x;
        for (set B = A; B; B &= B - 1) { int c = FIRST(B); g[x] |= (set)1 << c; g[c] |= (set)1 << x; }
    }
    if (GAMMA) {   /* exact check: v has minimum deficiency (ties allowed) */
        int dg[64], e2 = 0, zv = 0;
        for (int i = 0; i < n; i++) { dg[i] = POP(g[i]); e2 += dg[i]; }
        int e = e2 / 2;
        for (set B = g[m + D]; B; B &= B - 1) zv += dg[FIRST(B)];
        int gv = e - zv - ETAB[D];
        for (int u = 0; u < n; u++) { int z = 0; for (set B = g[u]; B; B &= B - 1) z += dg[FIRST(B)]; if (e - z - ETAB[dg[u]] < gv) return; }
    }
    if (MAXZ) {
        int dg[64], zv = 0;
        for (int i = 0; i < n; i++) dg[i] = POP(g[i]);
        for (set B = g[m + D]; B; B &= B - 1) zv += dg[FIRST(B)];
        for (int u = 0; u < n; u++) { int z = 0; for (set B = g[u]; B; B &= B - 1) z += dg[FIRST(B)]; if (z > zv) return; }
    }
    /* graph6 */
    char buf[2048]; int p = 0;
    buf[p++] = (char)(63 + n);
    int bitc = 0, val = 0;
    for (int j = 1; j < n; j++) for (int i = 0; i < j; i++) {
        val = (val << 1) | (int)((g[i] >> j) & 1); bitc++;
        if (bitc == 6) { buf[p++] = (char)(63 + val); bitc = 0; val = 0; }
    }
    if (bitc) { val <<= (6 - bitc); buf[p++] = (char)(63 + val); }
    buf[p++] = '\n'; fwrite(buf, 1, p, stdout); nout++;
}

static int *lists[16]; static set FULL; static int minsz;
static int cmp_size(const void *a, const void *b) {   /* larger sets first, then by value: a fixed total order */
    set x = *(const set *)a, y = *(const set *)b; int px = POP(x), py = POP(y);
    if (px != py) return py - px; return (x < y) ? 1 : (x > y) ? -1 : 0;
}
static void rec(int j, int *list, int len, int sumsz) {
    nodes++;
    int r = D - j;                       /* picks remaining */
    set needset = 0;
    for (int c = 0; c < m; c++) { int nd = minhit[c] - hits[c]; if (nd > r) return; if (nd > 0) needset |= (set)1 << c; }
    if (sumsz > sumhi) return;
    if (sumlo >= 0 && sumsz + r * (MAXDEG - 1) < sumlo) return;
    if (j == D) {
        if (sumsz < sumlo || sumsz > sumhi) return;
        emit(); return;
    }
    set cov = 0; for (int i = 0; i < len; i++) cov |= cand[list[i]];
    if (needset & ~cov) return;          /* some vertex that still needs a neighbour cannot get one */
    int *nl = lists[j + 1];
    for (int idx = 0; idx < len; idx++) {
        int q = list[idx]; set A = cand[q]; int sz = POP(A);
        /* later picks come later in the list, hence are no larger than this one */
        if (sumlo >= 0 && sumsz + r * sz < sumlo) break;
        if (sumsz + sz + (r - 1) * minsz > sumhi) continue;
        int ok = 1;
        for (set B = A; B; B &= B - 1) if (hits[FIRST(B)] >= room[FIRST(B)]) { ok = 0; break; }
        if (!ok) continue;
        int nsub = 1 << j;               /* subsets T of chosen ∪ {j} containing j with |T| >= 3 (pairs pre-filtered) */
        for (int s = 1; s < nsub; s++) {
            set U = uni[s] | A; uni[s | (1 << j)] = U;
            if (ok && POP((set)s) >= 2 && has_indep(~U & FULL, K - POP((set)s) - 1)) ok = 0;
        }
        if (!ok) continue;
        uni[1 << j] = A;
        int nlen = 0;
        if (j + 1 < D)
            for (int i2 = idx; i2 < len; i2++) {
                int q2 = list[i2];
                if (!has_indep(~(A | cand[q2]) & FULL, K - 2)) nl[nlen++] = q2;   /* t = 2: alpha(H - A - A2) <= k-3 */
            }
        pick[j] = q;
        for (set B = A; B; B &= B - 1) hits[FIRST(B)]++;
        rec(j + 1, nl, nlen, sumsz + POP(A));
        for (set B = A; B; B &= B - 1) hits[FIRST(B)]--;
    }
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: glue k d [regular] [mindeg=D] [edges=E]\n"); return 1; }
    K = atoi(argv[1]); D = atoi(argv[2]);
    for (int i = 3; i < argc; i++) {
        if (!strcmp(argv[i], "regular")) REG = 1;
        else if (!strncmp(argv[i], "mindeg=", 7)) MINDEG = atoi(argv[i] + 7);
        else if (!strncmp(argv[i], "edges=", 6)) EDGES = atoi(argv[i] + 6);
        else if (!strncmp(argv[i], "mine=", 5)) MINE = atoi(argv[i] + 5);
        else if (!strncmp(argv[i], "maxdeg=", 7)) MAXDEG = atoi(argv[i] + 7);
        else if (!strcmp(argv[i], "maxz")) MAXZ = 1;
        else if (!strncmp(argv[i], "etab=", 5)) {   /* comma list, index = degree; "x" = impossible */
            GAMMA = 1; char *p = argv[i] + 5; int j = 0;
            while (*p && j < 64) { if (*p == 'x') { ETAB[j++] = 1 << 20; p++; } else ETAB[j++] = (int)strtol(p, &p, 10); if (*p == ',') p++; }
            for (; j < 64; j++) ETAB[j] = 1 << 20;
        }
        else if (!strncmp(argv[i], "maxe=", 5)) MAXE = atoi(argv[i] + 5);
    }
    if (MAXDEG < 0) MAXDEG = D;
    if (MAXDEG < D || (REG && MAXDEG != D)) { fprintf(stderr, "need d <= maxdeg (and = for regular)\n"); return 1; }
    if (D > 10) { fprintf(stderr, "d too large\n"); return 1; }
    char line[4096]; long long ncores = 0;
    while (fgets(line, sizeof line, stdin)) {
        int len = strlen(line); while (len && (line[len-1] == '\n' || line[len-1] == '\r')) line[--len] = 0;
        if (!len) continue;
        m = line[0] - 63; if (m > MAXM) { fprintf(stderr, "core too large\n"); return 1; }
        memset(adj, 0, sizeof adj);
        int k6 = 0, bitpos = 0, idx = 1; int val = 0;
        for (int j = 1; j < m; j++) for (int i = 0; i < j; i++) {
            if (k6 == 0) { val = line[idx++] - 63; k6 = 6; }
            k6--; if ((val >> k6) & 1) { adj[i] |= (set)1 << j; adj[j] |= (set)1 << i; }
            bitpos++;
        }
        set full = (m == 64) ? ~(set)0 : (((set)1 << m) - 1);
        eH = 0; int bad = 0;
        for (int c = 0; c < m; c++) {
            nadj[c] = full & ~adj[c] & ~((set)1 << c);
            deg[c] = POP(adj[c]); eH += deg[c];
            room[c] = MAXDEG - deg[c]; if (room[c] < 0) bad = 1;
            minhit[c] = REG ? room[c] : (MINDEG > deg[c] ? MINDEG - deg[c] : 0);
        }
        eH /= 2; ncores++;
        if (bad) continue;
        /* edges(G) = eH + D + sum|A_i| */
        int lo_e = EDGES >= 0 ? EDGES : MINE, hi_e = EDGES >= 0 ? EDGES : MAXE;
        sumlo = lo_e >= 0 ? lo_e - eH - D : -1;
        sumhi = hi_e >= 0 ? hi_e - eH - D : (1 << 30);
        if (sumhi < 0) continue;
        set avail = 0; for (int c = 0; c < m; c++) if (room[c] > 0) avail |= (set)1 << c;
        ncand = 0;
        int lo = REG ? D - 1 : (MINDEG > 1 ? MINDEG - 1 : 0), hi = MAXDEG - 1;
        gen_cand(avail, 0, 0, lo, hi);
        if (GAMMA) {  /* v minimises deficiency g(u) = e - Z(u) - ETAB[deg u]; need g(x_i) >= g(v) = e(H) - ETAB[D] */
            int ehi = (hi_e >= 0 ? hi_e : 1 << 20), gv = eH - ETAB[D], w = 0;
            for (int i = 0; i < ncand; i++) {
                int dx = POP(cand[i]) + 1, z = D;
                for (set B = cand[i]; B; B &= B - 1) { int c = FIRST(B); int lb = deg[c] + 1; if (lb < MINDEG) lb = MINDEG; z += lb; }
                if (ehi - z - ETAB[dx] >= gv) cand[w++] = cand[i];   /* upper bound on g(x_i) must reach g(v) */
            }
            ncand = w;
        }
        if (MAXZ) {   /* v maximises Z: Z(x_i) = d + sum_{c in A_i} deg_G(c) <= Z(v) = e - e(H) <= maxe - e(H) */
            int zcap = (hi_e >= 0 ? hi_e : 1 << 20) - eH, w = 0;
            for (int i = 0; i < ncand; i++) {
                int z = D; for (set B = cand[i]; B; B &= B - 1) { int c = FIRST(B); int lb = deg[c] + 1; if (lb < MINDEG) lb = MINDEG; z += lb; }
                if (z <= zcap) cand[w++] = cand[i];
            }
            ncand = w;
        }
        qsort(cand, ncand, sizeof(set), cmp_size);
        minsz = ncand ? POP(cand[ncand - 1]) : 0;
        memset(hits, 0, sizeof hits); FULL = full;
        for (int L = 0; L <= D; L++) lists[L] = realloc(lists[L], (ncand + 1) * sizeof(int));
        for (int i = 0; i < ncand; i++) lists[0][i] = i;
        rec(0, lists[0], ncand, 0);
    }
    fprintf(stderr, "glue: %lld cores, %lld glued graphs emitted, %lld search nodes\n", ncores, nout, nodes);
    return 0;
}
