import sys, numpy as np
sys.path.insert(0, '/tmp/claude-1000/-home-doom-Public-PROJECT-2026-trader/a013584c-0930-4f6c-921b-e4ea05cde0a4/scratchpad')
import ts3_lib as L

data = L.load()
syms = sorted(data)[:10]
rat = []
for s in syms:
    g = data[s]
    for a, b in L.segments(g):
        d, atr, piv = L.prep(g, a, b)
        n = len(d)
        pools = L.build_pools(d, atr, piv, n)
        voids = L.build_voids(d, atr, n)
        fvgs = L.build_fvgs(d, n)
        onsets, comp, r14 = L.build_coils(d, atr, n)
        ok = ~np.isnan(r14) & (np.arange(n) >= 28)
        rat.append((r14[ok] / atr[ok]))
        sw = sum(1 for p in pools if p['dtyp'] == 'sweep')
        br = sum(1 for p in pools if p['dtyp'] == 'break')
        napp = sum(1 for p in pools if p['t_app'] >= 0)
        print(f"{s:12s} n={n:5d} piv={len(piv):3d} pools={len(pools):3d} (sw={sw} br={br} app={napp}) "
              f"voids={len(voids):4d} fvgs={len(fvgs):4d} coils={len(onsets):3d} comp%={100*comp.mean():.1f}")
r = np.concatenate(rat)
print("r14/ATR pct:", {q: round(float(np.percentile(r, q)), 2) for q in (1, 5, 10, 25, 50)})
