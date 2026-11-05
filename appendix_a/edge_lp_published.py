"""Single-vertex counting for e(3,10,n) using the published exact e(3,9,m) values
(Goedgebeur & Radziszowski, EJC 2013, Tables 3-4) instead of recursive bounds."""
import edge_lp_r3k as m
PUB9 = {25: 46, 26: 52, 27: 61, 28: 68, 29: 77, 30: 86, 31: 95, 32: 104, 33: 118, 34: 129, 35: 140}
orig = m.E.__wrapped__
def E(k, n):
    if k == 9 and n in PUB9: return PUB9[n]
    return orig(k, n)
m.E = m.lru_cache(None)(E)
PUB10 = {35: 107, 36: 117, 37: 128, 38: 139, 39: 151, 40: 161, 41: 172}
print(" n  ours(recursive)  ours(with published e(3,9,.))  published e(3,10,n)  max")
for n in range(35, 42):
    import importlib
    print(f"{n:>2}  {orig(10, n):>15}  {m.E(10, n):>29}  {PUB10[n]:>19}  {n*9//2}")
